"""Transcreve a fala com tempo de cada palavra (faster-whisper) e grava palavras.json + palavras.js.

Uso: python3 ferramentas/transcrever.py <audio_ou_video> <palavras.json> [--modelo medium] [--prompt "nomes e termos"]
- Use o modelo "medium" para legendas (o "small" erra mais nomes e marcas).
- --prompt ajuda com nomes próprios: ex. "Oi, lojista! Ste Fashion, Brunna, pedido mínimo de 12 peças."
- Se não houver fala, o arquivo sai com lista vazia.
Conferir sempre: palavras com probabilidade baixa (p < 0,6) costumam estar erradas; corrija pelo
contexto na legenda e avise o usuário do que foi corrigido.
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import _rede  # noqa: F401
from faster_whisper import WhisperModel

ap = argparse.ArgumentParser()
ap.add_argument("entrada"); ap.add_argument("saida")
ap.add_argument("--modelo", default="medium"); ap.add_argument("--prompt", default="")
a = ap.parse_args()
m = WhisperModel(a.modelo, device="cpu", compute_type="int8")
segs, _ = m.transcribe(a.entrada, language="pt", word_timestamps=True, beam_size=5, vad_filter=True,
                       condition_on_previous_text=False, initial_prompt=a.prompt or None)
W = []
for s in segs:
    if s.no_speech_prob > .8 and s.avg_logprob < -1:   # alucinação comum em trecho só de música
        continue
    print(f"[{s.start:6.2f}-{s.end:6.2f}] {s.text.strip()}")
    W += [{"w": w.word.strip(), "s": round(w.start, 2), "e": round(w.end, 2), "p": round(w.probability, 2)} for w in s.words]
json.dump(W, open(a.saida, "w"), ensure_ascii=False)
open(os.path.splitext(a.saida)[0] + ".js", "w").write("window.PALAVRAS = " + json.dumps(W, ensure_ascii=False) + ";")
duvidas = [f"{w['w']}@{w['s']}s(p={w['p']})" for w in W if w["p"] < .6]
print(f"{len(W)} palavras -> {a.saida}" + (f"\nconferir (baixa confiança): {', '.join(duvidas)}" if duvidas else ""))
