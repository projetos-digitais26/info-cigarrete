"""Corta os trechos do ElevenLabs (1 a 3 cenas cada) em um arquivo por cena e locutor, pelos tempos das palavras.

Uso: python3 separar_cenas.py segmentos.json trechos-eleven.json conferencia-eleven.json eleven/ <pasta_cenas> segmentos-eleven.json

- A abertura da Sofia (T001, T003, T005) sai de eleven/SOFIA_ABERTURA.mp3 (take aprovado pelo produtor).
- Corte no ponto de menor energia entre a última palavra de uma cena e a primeira da seguinte
  (a pausa natural da narradora fica dentro da cena anterior; o montar_audio recorta o silêncio das pontas).
- Gera segmentos-eleven.json: cada cena com uma "frase" por bloco de locutor ({cena}_{i:02d}.mp3), para o montar_audio.py.
"""
import difflib, json, os, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from texto_norm import norm

segs, trechos, conf = (json.load(open(p)) for p in sys.argv[1:4])
pasta, saida_dir, saida_segs = sys.argv[4], sys.argv[5], sys.argv[6]
os.makedirs(saida_dir, exist_ok=True)
SR = 44100


def carregar(p):
    return np.frombuffer(subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                                        capture_output=True, check=True).stdout, np.float32)


def salvar(x, p):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-c:a", "libmp3lame", "-b:a", "192k", p],
                   input=x.astype(np.float32).tobytes(), check=True)


def palavras_de(p):
    from faster_whisper import WhisperModel
    m = WhisperModel("medium", device="cpu", compute_type="int8")
    x = np.frombuffer(subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                                     capture_output=True, check=True).stdout, np.float32)
    s, _ = m.transcribe(x, language="pt", beam_size=5, condition_on_previous_text=False, word_timestamps=True)
    return [{"w": w.word.strip(), "s": w.start, "e": w.end} for seg in s for w in seg.words]


def ponto_de_corte(x, a, b):
    """menor energia (janela de 20 ms) entre a e b segundos"""
    a, b = int(max(0, a) * SR), int(min(len(x) / SR, b) * SR)
    if b - a < int(.04 * SR):
        return (a + b) / 2 / SR
    j = int(.02 * SR); e = np.convolve(x[a:b] ** 2, np.ones(j), "same")
    return (a + int(np.argmin(e[j:-j])) + j) / SR if len(e) > 2 * j else (a + b) / 2 / SR


def cortar(audio, cenas, palavras):
    """devolve uma lista de arrays, uma por cena"""
    x = carregar(audio)
    esp, dono = [], []
    for k, c in enumerate(cenas):
        w = norm(c["texto"]); esp += w; dono += [k] * len(w)
    ouv, idx = [], []
    for i, p in enumerate(palavras):
        w = norm(p["w"]); ouv += w; idx += [i] * len(w)
    # para cada token esperado, a palavra ouvida correspondente (quando bate)
    par = {}
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, esp, ouv, autojunk=False).get_opcodes():
        if op in ("equal", "replace"):
            for d in range(min(i2 - i1, j2 - j1)):
                par[i1 + d] = idx[j1 + d]
    cortes = [0.0]
    for k in range(1, len(cenas)):
        primeiro = dono.index(k)
        ult = max((par[i] for i in range(primeiro) if i in par), default=None)
        prox = min((par[i] for i in range(primeiro, len(esp)) if i in par and dono[i] >= k), default=None)
        if ult is None or prox is None:
            raise SystemExit(f"sem alinhamento para cortar {audio} antes de {cenas[k]['id']}")
        e, s = palavras[ult]["e"], palavras[prox]["s"]
        cortes.append(ponto_de_corte(x, min(e, s) - .05, max(e, s) + .05))
    cortes.append(len(x) / SR)
    return [x[int(cortes[k] * SR):int(cortes[k + 1] * SR)] for k in range(len(cenas))], cortes


# arquivo de cada bloco (cena, locutor) na ordem do roteiro
blocos = {}
sofia = [t for t in trechos if t["id"] in ("T001", "T003", "T005")]
cenas_sofia = [c for t in sofia for c in t["cenas"]]
partes, cortes = cortar(os.path.join(pasta, "SOFIA_ABERTURA.mp3"), cenas_sofia, palavras_de(os.path.join(pasta, "SOFIA_ABERTURA.mp3")))
print("SOFIA_ABERTURA cortes:", [round(c, 2) for c in cortes])
for c, x in zip(cenas_sofia, partes):
    blocos.setdefault(c["id"], []).append(x)
for t in trechos:
    if t["id"] in ("T001", "T003", "T005"):
        continue
    audio = os.path.join(pasta, t["id"] + ".mp3")
    if len(t["cenas"]) == 1:
        partes = [carregar(audio)]
    else:
        partes, cortes = cortar(audio, t["cenas"], conf[t["id"]]["palavras"])
        print(t["id"], "cortes:", [round(c, 2) for c in cortes[1:-1]], [c["id"] for c in t["cenas"]])
    for c, x in zip(t["cenas"], partes):
        blocos.setdefault(c["id"], []).append(x)

novos = []
for s in segs:
    # blocos de locutor desta cena, na ordem (mesma regra do trechos_eleven.py)
    grupos = []
    for f in s["frases"]:
        if grupos and grupos[-1]["voz"] == f["voz"]:
            grupos[-1]["texto"] += " " + f["texto"]
        else:
            grupos.append(dict(f))
    if len(grupos) != len(blocos.get(s["id"], [])):
        raise SystemExit(f"{s['id']}: {len(grupos)} blocos no roteiro, {len(blocos.get(s['id'], []))} no áudio")
    for i, x in enumerate(blocos.get(s["id"], [])):
        salvar(x, os.path.join(saida_dir, f"{s['id']}_{i:02d}.mp3"))
    novos.append({**s, "frases": grupos})
json.dump(novos, open(saida_segs, "w"), ensure_ascii=False, indent=1)
print("ok:", len(novos), "cenas,", sum(len(s["frases"]) for s in novos), "arquivos em", saida_dir)
