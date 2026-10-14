"""Grava a locução em takes curtos, confere cada take (Whisper) e regrava até sair certo.

Uso: python3 gravar_takes.py segmentos.json <pasta_takes> <relatorio.json> [--voz pt-BR-FranciscaNeural] [--so A01,C34]

- Take = 1 a 3 frases da mesma cena e do mesmo locutor, de 8 a 30 palavras (frase solta de 1–2
  palavras sai com pronúncia errada: a voz não tem contexto).
- Pronúncia: DICIONARIO troca nomes/siglas pela grafia que a voz lê certo (só no áudio).
- Cada take é transcrito sem dica e comparado ao texto; abaixo de NOTA_OK, regrava com variação
  de velocidade (até 6 tentativas) e guarda a melhor. O relatório lista o que não passou.
"""
import argparse, asyncio, difflib, json, os, re, subprocess, sys
import numpy as np
import edge_tts
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "ferramentas"))
import _rede  # noqa: F401
from faster_whisper import WhisperModel

ap = argparse.ArgumentParser()
ap.add_argument("segmentos"); ap.add_argument("pasta"); ap.add_argument("relatorio")
ap.add_argument("--voz", default="pt-BR-FranciscaNeural"); ap.add_argument("--so", default="")
ap.add_argument("--modelo", default="medium"); ap.add_argument("--previa", action="store_true")
a = ap.parse_args()
PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
NOTA_OK = .95

# grafia para a voz ler certo -> (só no áudio; a comparação usa o texto original)
DICIONARIO = {"Kwame": "Kuâmi", "Kofi": "Kôfi", "AVC": "á vê cê", "UTI": "u tê í", "Gana": "Gana", "OMS": "ó ême ésse"}
# prosódia por emoção: mais contida que a v1 (extremos deixam a voz artificial)
PROSODIA = {"impacto": ("-8%", "-2Hz"), "intimo": ("-6%", "-1Hz"), "dor": ("-11%", "-3Hz"), "choque": ("-13%", "-4Hz"),
            "medo": ("-8%", "-2Hz"), "revelacao": ("-5%", "+0Hz"), "misterio": ("-10%", "-3Hz"), "esperanca": ("-4%", "+1Hz"),
            "alegria": ("-2%", "+2Hz"), "venda": ("+0%", "+0Hz"), "urgencia": ("+2%", "+0Hz")}
CRIANCA = {"rate": "-6%", "pitch": "+28Hz", "filtro": "asetrate=24000*1.09,aresample=24000,atempo=0.917"}

from texto_norm import norm  # noqa: E402


def montar_takes(segs):
    takes = []
    for s in segs:
        grupo = []
        def fecha():
            if grupo:
                takes.append({"id": f"{s['id']}_{len([t for t in takes if t['cena'] == s['id']]):02d}", "cena": s["id"],
                              "voz": grupo[0]["voz"], "emocao": s["emocao"], "texto": " ".join(g["texto"] for g in grupo)})
        for f in s["frases"]:
            if grupo and (f["voz"] != grupo[0]["voz"] or
                          (len(" ".join(g["texto"] for g in grupo).split()) >= 8 and len(" ".join(g["texto"] for g in grupo + [f]).split()) > 30)):
                fecha(); grupo = []
            grupo.append(f)
        fecha()
    return takes


def falar(texto):
    for k, v in DICIONARIO.items():
        texto = re.sub(rf"\b{k}\b", v, texto)
    return texto


async def tts(texto, voz, rate, pitch, dst):
    await edge_tts.Communicate(texto, voz, rate=rate, pitch=pitch, proxy=PROXY).save(dst)


def carregar16(p):
    return np.frombuffer(subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                                        capture_output=True, check=True).stdout, np.float32)


def avaliar(p, texto):
    x = carregar16(p)
    segs, _ = modelo.transcribe(x, language="pt", beam_size=5, vad_filter=False, condition_on_previous_text=False)
    ouvido = " ".join(s.text.strip() for s in segs)
    esp, ouv = norm(texto), norm(ouvido)
    nota = difflib.SequenceMatcher(None, esp, ouv).ratio()
    rapido = len(x) / 16000 / max(1, len(esp)) < .25
    return (0 if rapido else nota), ouvido, len(x) / 16000


segs = json.load(open(a.segmentos))
takes = montar_takes(segs)
if a.previa:
    curtos = [t for t in takes if len(t["texto"].split()) < 5]
    print(len(takes), "takes; menor", min(len(t["texto"].split()) for t in takes), "palavras; maior", max(len(t["texto"].split()) for t in takes))
    for t in curtos:
        print("  curto:", t["id"], t["voz"], "|", t["texto"])
    print(norm("por apenas R$ 37,00."), norm("Kuami e Cofi porque"))
    sys.exit()
modelo = WhisperModel(a.modelo, device="cpu", compute_type="int8")
so = set(filter(None, a.so.split(",")))
os.makedirs(a.pasta, exist_ok=True)
rel_antigo = {r["id"]: r for r in json.load(open(a.relatorio))} if os.path.exists(a.relatorio) else {}
relatorio = []
VARIACOES = [0, -3, 3, -6, 2, -9]   # pontos percentuais somados à velocidade
for t in takes:
    dst = os.path.join(a.pasta, t["id"] + ".mp3")
    if (so and t["cena"] not in so) or (not so and t["id"] in rel_antigo and rel_antigo[t["id"]]["nota"] >= NOTA_OK and os.path.exists(dst)):
        relatorio.append(rel_antigo.get(t["id"], {**t, "nota": None})); continue
    crianca = t["voz"] == "crianca"
    rate0, pitch = (CRIANCA["rate"], CRIANCA["pitch"]) if crianca else PROSODIA[t["emocao"]]
    melhor = None
    for n, dv in enumerate(VARIACOES):
        rate = f"{int(rate0.rstrip('%')) + dv:+d}%"
        bruto = dst + f".t{n}.mp3"
        try:
            asyncio.run(tts(falar(t["texto"]), a.voz, rate, pitch, bruto))
        except Exception as e:
            print("erro tts", t["id"], e, flush=True); continue
        cand = bruto
        if crianca:
            cand = dst + f".c{n}.mp3"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", bruto, "-af", CRIANCA["filtro"], cand], check=True)
        nota, ouvido, dur = avaliar(cand, t["texto"])
        if melhor is None or nota > melhor[0]:
            melhor = (nota, ouvido, dur, cand, rate)
        if nota >= NOTA_OK:
            break
    os.replace(melhor[3], dst)
    for f in os.listdir(a.pasta):
        if f.startswith(t["id"] + ".mp3."):
            os.remove(os.path.join(a.pasta, f))
    r = {**t, "nota": round(melhor[0], 3), "ouvido": melhor[1], "dur": round(melhor[2], 2), "rate": melhor[4], "tentativas": n + 1}
    relatorio.append(r)
    marca = "OK " if r["nota"] >= NOTA_OK else "REVER"
    print(f"{marca} {t['id']} nota={r['nota']} tent={n + 1} | {t['texto'][:60]} | ouvido: {melhor[1][:60]}", flush=True)
    json.dump(relatorio, open(a.relatorio, "w"), ensure_ascii=False, indent=1)
json.dump(relatorio, open(a.relatorio, "w"), ensure_ascii=False, indent=1)
ruins = [r for r in relatorio if r.get("nota") is not None and r["nota"] < NOTA_OK]
print(f"FIM: {len(takes)} takes, {len(ruins)} para rever")
