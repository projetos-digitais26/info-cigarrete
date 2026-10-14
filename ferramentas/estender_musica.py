"""Estende a música de um vídeo (quando o vídeo editado fica mais longo que a trilha original),
repetindo uma frase musical da própria trilha, sem salto de volume nem de andamento.

Procura um ponto t1 (perto do fim) cujo som combina com um ponto anterior t0 (mesmo timbre e mesmo
volume), refina no nível da forma de onda e monta: [0, t1] + [t0, t1] + [t0, t1] + ... até a duração pedida,
com cruzamento de 40 ms em cada emenda e fade-out no final.

Uso: python3 ferramentas/estender_musica.py <video_ou_audio> <duracao_total> <saida.wav> [fade_out_s=1.5]
Imprime a emenda escolhida e, em cada emenda, o volume logo depois dela comparado ao que a música
original tocaria naquele ponto (diferença ideal < 1 dB).
"""
import subprocess, sys
import numpy as np

src, TOTAL, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
FADE = float(sys.argv[4]) if len(sys.argv) > 4 else 1.5
SR = 22050
x = np.frombuffer(subprocess.run(["ffmpeg", "-loglevel", "error", "-i", src, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                                 capture_output=True).stdout, np.float32)
D = len(x) / SR
hop = 256; fr = np.lib.stride_tricks.sliding_window_view(x, 2048)[::hop]
S = np.log1p(np.abs(np.fft.rfft(fr * np.hanning(2048), axis=1))[:, :300]); fps = SR / hop
lv = lambda a, b: 20 * np.log10(np.sqrt(np.mean(x[int(a * SR):int(b * SR)] ** 2)) + 1e-9)
L = int(1.5 * fps); res = []
for t1 in np.arange(max(3.0, D * .6), D - .3, .05):
    a = S[int(t1 * fps) - L:int(t1 * fps)]
    for t0 in np.arange(1.6, t1 - 3.0, .05):
        b = S[int(t0 * fps) - L:int(t0 * fps)]
        c = np.corrcoef(a.ravel(), b.ravel())[0, 1]; dl = abs(lv(t1, t1 + .8) - lv(t0, t0 + .8))
        res.append((c - .08 * dl, c, dl, t1, t0))
res.sort(reverse=True)
_, c, dl, t1, t0 = res[0]
# refino fino do t0 pela forma de onda
ref = x[int((t1 - .4) * SR):int(t1 * SR)]; best = (-2, t0)
for d in np.arange(-.04, .04, 4 / SR):
    seg = x[int((t0 + d - .4) * SR):int((t0 + d - .4) * SR) + len(ref)]
    cc = np.dot(ref, seg) / np.sqrt(np.dot(ref, ref) * np.dot(seg, seg) + 1e-12)
    if cc > best[0]: best = (cc, t0 + d)
t0 = best[1]
print(f"emenda: {t1:.2f}s volta para {t0:.3f}s (frase de {t1 - t0:.2f}s, timbre {c:.2f}, dif. volume {dl:.1f} dB)")

partes = [(0.0, t1)]; dur = t1
while dur < TOTAL + .5:
    partes.append((t0, t1)); dur += t1 - t0
ins, f = [], []
for i, (a, b) in enumerate(partes):
    ins += ["-i", src]; f.append(f"[{i}:a]atrim={a:.4f}:{b + .02:.4f},asetpts=PTS-STARTPTS[p{i}]")
cur = "p0"
for i in range(1, len(partes)):
    f.append(f"[{cur}][p{i}]acrossfade=d=0.04:c1=tri:c2=tri[q{i}]"); cur = f"q{i}"
f.append(f"[{cur}]atrim=0:{TOTAL},afade=t=out:st={TOTAL - FADE}:d={FADE}[m]")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *ins, "-filter_complex", ";".join(f), "-map", "[m]", "-ar", "48000",
                "-c:a", "pcm_s16le", out], check=True)
y = np.frombuffer(subprocess.run(["ffmpeg", "-loglevel", "error", "-i", out, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                                 capture_output=True).stdout, np.float32)
ly = lambda a, b: 20 * np.log10(np.sqrt(np.mean(y[int(a * SR):int(b * SR)] ** 2)) + 1e-9)
pos = t1
for i in range(1, len(partes)):
    if pos < TOTAL - FADE:
        print(f"  emenda em {pos:.2f}s: depois da emenda {ly(pos, pos + .4):.1f} dB | a música original tocaria {lv(t1, t1 + .4):.1f} dB")
    pos += t1 - t0
print("ok:", out)
