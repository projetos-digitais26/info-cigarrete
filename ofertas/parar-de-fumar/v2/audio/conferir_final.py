"""Transcreve o áudio final inteiro e alinha com o roteiro: lista trechos de 3+ palavras que sumiram
(efeito ou trilha cobrindo a voz, emenda cortando palavra).

Uso: python3 conferir_final.py segmentos-takes.json vsl-final.mp3 [--modelo small]
"""
import difflib, json, os, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "ferramentas"))
import _rede  # noqa: F401
from faster_whisper import WhisperModel
from texto_norm import norm

segs, mp3 = json.load(open(sys.argv[1])), sys.argv[2]
modelo = sys.argv[sys.argv.index("--modelo") + 1] if "--modelo" in sys.argv else "small"
esp = [w for s in segs for f in s["frases"] for w in norm(f["texto"])]
x = np.frombuffer(subprocess.run(["ffmpeg", "-loglevel", "error", "-i", mp3, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                                 capture_output=True, check=True).stdout, np.float32)
segs_w, _ = WhisperModel(modelo, device="cpu", compute_type="int8").transcribe(
    x, language="pt", beam_size=5, vad_filter=True, condition_on_previous_text=False, word_timestamps=True)
ouv, tempos = [], []
for s in segs_w:
    for w in s.words:
        for t in norm(w.word):
            ouv.append(t); tempos.append(w.start)
sm = difflib.SequenceMatcher(None, esp, ouv, autojunk=False)
print(f"semelhança geral: {sm.ratio():.4f} | palavras no roteiro: {len(esp)} | ouvidas: {len(ouv)}")
n = 0
for op, i1, i2, j1, j2 in sm.get_opcodes():
    if op in ("delete", "replace") and i2 - i1 >= 3:
        t = tempos[min(j1, len(tempos) - 1)]; n += 1
        print(f"{int(t // 60)}:{t % 60:04.1f} FALTOU: {' '.join(esp[i1:i2])} | OUVIDO: {' '.join(ouv[j1:j2])}")
print(f"FIM: {n} trechos para conferir")
