"""Confere os trechos do ElevenLabs (eleven/Txxx.mp3) contra o roteiro e guarda o tempo de cada palavra.

Uso: python3 conferir_trechos.py trechos-eleven.json eleven/ conferencia-eleven.json
Só processa trechos ainda não conferidos (ou com o mp3 mais novo que a conferência).
Nota < 0,95 = regravar o trecho.
"""
import difflib, json, os, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "ferramentas"))
import _rede  # noqa: F401
from faster_whisper import WhisperModel
from texto_norm import norm

trechos, pasta, saida = json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3]
res = json.load(open(saida)) if os.path.exists(saida) else {}
modelo = None
for t in trechos:
    p = os.path.join(pasta, t["id"] + ".mp3")
    if not os.path.exists(p) or (t["id"] in res and res[t["id"]]["mtime"] == os.path.getmtime(p)):
        continue
    modelo = modelo or WhisperModel("medium", device="cpu", compute_type="int8")
    x = np.frombuffer(subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                                     capture_output=True, check=True).stdout, np.float32)
    segs, _ = modelo.transcribe(x, language="pt", beam_size=5, condition_on_previous_text=False, word_timestamps=True)
    palavras = [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2)} for s in segs for w in s.words]
    esp = [w for c in t["cenas"] for w in norm(c["texto"])]
    ouv = [w for p_ in palavras for w in norm(p_["w"])]
    sm = difflib.SequenceMatcher(None, esp, ouv, autojunk=False)
    dif = [(" ".join(esp[i1:i2]), " ".join(ouv[j1:j2])) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]
    res[t["id"]] = {"nota": round(sm.ratio(), 3), "dif": dif, "palavras": palavras, "dur": round(len(x) / 16000, 2), "mtime": os.path.getmtime(p)}
    marca = "OK " if sm.ratio() >= .95 else "REVER"
    print(f"{marca} {t['id']} nota={sm.ratio():.3f} {dif[:4]}", flush=True)
    json.dump(res, open(saida, "w"), ensure_ascii=False)
print("FIM conferência:", len(res), "trechos conferidos")
