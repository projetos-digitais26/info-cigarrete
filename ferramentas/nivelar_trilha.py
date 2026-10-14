"""Desfaz o "abaixa sob a fala" (ducking) de uma trilha extraída com separar_musica.py:
aplica ganho inverso suavizado para a música ficar com nível constante e servir de fundo em outro vídeo.

Uso: python3 ferramentas/nivelar_trilha.py <musica.wav> <saida.wav>
Imprime o volume por segundo antes de gravar (deve ficar estável, variação de poucos dB).
"""
import subprocess, sys, wave
import numpy as np
SR = 44100
raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", sys.argv[1], "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
x = np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
p = np.mean(x ** 2, axis=1)
k = int(.6 * SR); env = np.sqrt(np.convolve(p, np.ones(k) / k, mode="same") + 1e-10)
alvo = np.percentile(env, 90)                      # nível dos trechos sem fala
g = np.clip(alvo / env, 1, 12)                     # até +21,6 dB
k2 = int(.4 * SR); g = np.convolve(np.pad(g, (k2, k2), mode="edge"), np.ones(k2) / k2, mode="same")[k2:-k2]
y = x * g[:, None]; y *= .5 / max(1e-6, np.abs(y).max())
with wave.open(sys.argv[2], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((y * 32767).astype("<i2").tobytes())
r = np.sqrt(np.mean(y[:len(y)//SR*SR, 0].reshape(-1, SR) ** 2, axis=1))
print("volume por segundo:", " ".join(f"{i}:{20*np.log10(v+1e-9):.0f}" for i, v in enumerate(r)))
