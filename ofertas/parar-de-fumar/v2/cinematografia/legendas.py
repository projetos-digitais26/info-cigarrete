"""Gera os dados do overlay (legendas palavra a palavra + textos na tela) no tempo do áudio final.

Uso (na pasta cinematografia/): python3 legendas.py overlay/dados.js [--de 0] [--ate 160]

- Tempo de cada palavra: Whisper sobre o áudio final; a grafia vem do roteiro (segmentos-eleven.json), então
  nomes como Kwame e Kofi saem certos mesmo que o Whisper erre. Palavra sem par no Whisper é interpolada.
- Linhas curtas (até 3–4 palavras / 24 caracteres), quebradas em pontuação ou pausa; fala da Sofia marcada (cor própria).
- Destaque (*...*): palavras-chave da oferta e números.
- Textos na tela (🅣): texto_tela de cada plano, no tempo do plano (mesma linha do tempo do montar_video.py).
"""
import argparse, difflib, json, os, re, subprocess, sys
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "audio"))
sys.path.insert(0, os.path.join(AQUI, "..", "..", "..", "..", "ferramentas"))
import _rede  # noqa: F401
from texto_norm import norm

ap = argparse.ArgumentParser()
ap.add_argument("saida"); ap.add_argument("--de", type=float, default=0); ap.add_argument("--ate", type=float, default=1e9)
a = ap.parse_args()
AUDIO = os.path.join(AQUI, "..", "audio", "vsl-v2-pt-elevenlabs.mp3")
segs = json.load(open(os.path.join(AQUI, "..", "audio", "segmentos-eleven.json")))
cenas = json.load(open(os.path.join(AQUI, "cenas-tempo.json")))
planos = json.load(open(os.path.join(AQUI, "planos.json")))
DESTAQUE = {"cigarro", "cigarros", "primeiro", "uti", "filha", "pai", "serpente", "cabeça", "kwame", "gana", "fraqueza", "morrer",
            "infarto", "câncer", "enfisema", "impotência", "avc", "dinheiro", "promessa", "desenho", "vovô", "sofia", "mamãe",
            "três", "movimentos", "empurrar", "partir", "selar", "frascos", "esqueci", "esquecido", "garantia", "presentes",
            "método", "truque", "café", "isqueiro", "nicotina", "metade", "fico", "vida", "passado", "presente", "botão", "amanhã"}

# palavras do roteiro, com locutor, só das cenas do trecho pedido
inicio = {c["cena"]: c["inicio"] for c in cenas}
alvo = []
for s in segs:
    t = inicio[s["id"]]
    if t < a.de - 30 or t > a.ate + 5:
        continue
    for f in s["frases"]:
        for w in f["texto"].split():
            alvo.append({"w": w, "voz": f["voz"], "cena": s["id"]})

# Whisper com tempo por palavra no trecho
de, ate = max(0, a.de - 30), a.ate + 5
x = np.frombuffer(subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(de), "-t", str(ate - de), "-i", AUDIO, "-ac", "1", "-ar", "16000",
                                  "-f", "f32le", "-"], capture_output=True, check=True).stdout, np.float32)
from faster_whisper import WhisperModel
m = WhisperModel("medium", device="cpu", compute_type="int8")
ws, _ = m.transcribe(x, language="pt", beam_size=5, condition_on_previous_text=False, word_timestamps=True,
                     initial_prompt="Márcia, Sofia, Luciano, Kwame, Kofi, Gana, UTI, cigarro.")
ouv = [{"w": w.word.strip(), "s": w.start + de, "e": w.end + de} for seg in ws for w in seg.words]

# alinhamento token a token (norm pode virar 1 palavra em várias)
E, eo_ = [], []
for i, w in enumerate(alvo):
    for t in norm(w["w"]):
        E.append(t); eo_.append(i)
O, oo = [], []
for j, w in enumerate(ouv):
    for t in norm(w["w"]):
        O.append(t); oo.append(j)
for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, E, O, autojunk=False).get_opcodes():
    if op in ("equal", "replace"):
        for k in range(min(i2 - i1, j2 - j1)):
            w, o = alvo[eo_[i1 + k]], ouv[oo[j1 + k]]
            w.setdefault("s", o["s"]); w["e"] = o["e"]
# interpola as que ficaram sem tempo
idx = [i for i, w in enumerate(alvo) if "s" in w]
for i, w in enumerate(alvo):
    if "s" in w:
        continue
    ant = max([k for k in idx if k < i], default=None); pos = min([k for k in idx if k > i], default=None)
    if ant is None or pos is None:
        w["s"] = w["e"] = alvo[ant if ant is not None else pos]["s"]; continue
    f = (i - ant) / (pos - ant); w["s"] = alvo[ant]["e"] + f * (alvo[pos]["s"] - alvo[ant]["e"]); w["e"] = w["s"] + .25
alvo = [w for w in alvo if a.de <= w["s"] < a.ate]

# linhas de legenda
cap, cur = [], []
def fecha():
    if cur:
        txt = " ".join(("*" + w["w"] + "*") if (re.sub(r"[^\wÀ-ú]", "", w["w"]).lower() in DESTAQUE or re.search(r"\d", w["w"])) else w["w"] for w in cur)
        txt = re.sub(r"\*\s\*", " ", txt)   # destaques vizinhos num só bloco
        cap.append([round(cur[0]["s"] - a.de, 2), round(cur[-1]["e"] - a.de + .25, 2), txt, cur[0]["voz"]])
for i, w in enumerate(alvo):
    if cur and (w["voz"] != cur[-1]["voz"] or len(cur) >= 4 or len(" ".join(c["w"] for c in cur + [w])) > 24 or w["s"] - cur[-1]["e"] > .35):
        fecha(); cur = []
    cur.append(w)
    if re.search(r"[.!?…:]$", w["w"]):
        fecha(); cur = []
fecha()
for k in range(len(cap) - 1):            # não sobrepõe a próxima
    cap[k][1] = min(cap[k][1], cap[k + 1][0] - .02)

# textos na tela, com a mesma linha do tempo do montar_video.py
tt = []
for k, c in enumerate(cenas):
    ps = sorted([p for p in planos if p["cena"] == c["cena"]], key=lambda p: p["ordem"])
    t = c["inicio"] if k > 0 else 0.0
    fim = cenas[k + 1]["inicio"] if k + 1 < len(cenas) else c["inicio"] + c["dur"]
    total = fim - t
    for p in ps:
        d = total * p["peso"] / sum(q["peso"] for q in ps)
        if isinstance(p.get("texto_tela"), dict) and p["texto_tela"].get("texto") and a.de <= t < a.ate:
            tt.append([round(t - a.de, 2), round(t + d - a.de, 2), p["texto_tela"]["texto"], p["texto_tela"].get("posicao", "topo")])
        t += d
# junta textos iguais em planos seguidos (o mesmo 🅣 atravessando cortes)
jun = []
for x in tt:
    if jun and jun[-1][2] == x[2] and abs(jun[-1][1] - x[0]) < .05:
        jun[-1][1] = x[1]
    else:
        jun.append(x)
# selo "Cenas dramatizadas" nas fases de hospital/UTI (e nos 6 s iniciais)
selo = [[0, 6]]
for k, c in enumerate(cenas):
    if c["fase"] in ("uti", "hospital"):
        t0 = c["inicio"] if k else 0.0; t1 = t0 + c["dur"]
        if t1 > a.de and t0 < a.ate:
            r = [round(max(t0, a.de) - a.de, 2), round(min(t1, a.ate) - a.de, 2)]
            if selo and r[0] - selo[-1][1] < 1:
                selo[-1][1] = r[1]
            else:
                selo.append(r)
os.makedirs(os.path.dirname(os.path.abspath(a.saida)), exist_ok=True)
open(a.saida, "w").write("window.CAP = " + json.dumps(cap, ensure_ascii=False) + ";\nwindow.TT = " + json.dumps(jun, ensure_ascii=False) + ";\n"
                         + "window.SELO = " + json.dumps(selo) + ";\n" + f"window.TOTAL = {min(a.ate, cenas[-1]['inicio'] + cenas[-1]['dur']) - a.de:.2f};\n")
print(f"ok {a.saida}: {len(cap)} legendas, {len(jun)} textos na tela; {sum(1 for w in alvo if 'e' not in w)} palavras interpoladas")
