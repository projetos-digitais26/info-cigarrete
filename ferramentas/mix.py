"""Mixagem voz + trilha de fundo, no padrão aprovado pelos clientes.

- A VOZ fica natural (como foi gravada). Filtros de redução de ruído/compressão deixam a fala
  "condensada" e foram reprovados. Só use VOZ=tratada se o usuário pedir limpeza de ruído.
- A trilha fica 20 dB abaixo da voz durante a fala, 16 dB nos respiros e 12 dB no encerramento.
- Volume final com GANHO FIXO (sem loudnorm dinâmico, que comprime a voz): mira -14 LUFS, mas
  para antes se o pico passar de -1 dBTP. É normal sair entre -21 e -15 LUFS em voz gravada no celular.

Uso: python3 ferramentas/mix.py <voz: video_ou_audio> <palavras.json> <trilha> <duracao_total> <inicio_encerramento> <saida.wav>
                                 [sob_fala respiro encerramento]   (dB em relação à voz; padrão -20 -16 -12)
     [VOZ=tratada] para ativar redução de ruído + compressão (só se pedido).
A fala é detectada pelas palavras do Whisper (palavras.json, gerado por transcrever.py).
A trilha precisa ter duração >= total (use emenda_musica.py ou nivelar_trilha.py antes, se preciso).
"""
import json, subprocess, sys, wave, os, tempfile
import numpy as np

if len(sys.argv) < 7:
    sys.exit(__doc__)
fonte, palavras, trilha, TOTAL, END, saida = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), float(sys.argv[5]), sys.argv[6]
SR = 48000
SOB_FALA, RESPIRO, ENCERRAMENTO = -20.0, -16.0, -12.0
if len(sys.argv) > 7: SOB_FALA, RESPIRO, ENCERRAMENTO = map(float, sys.argv[7:10])


def ffmpeg_wav(args, out):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args, "-ar", str(SR), "-ac", "2", "-c:a", "pcm_f32le", out], check=True)


def ler(p):
    raw = open(p, "rb").read(); i = raw.find(b"data")
    n = int.from_bytes(raw[i + 4:i + 8], "little")
    return np.frombuffer(raw[i + 8:i + 8 + n], dtype=np.float32).reshape(-1, 2).copy()


tmp = tempfile.mkdtemp()
FILTRO_VOZ = ("highpass=f=80,afftdn=nf=-25,acompressor=threshold=-18dB:ratio=3:attack=5:release=150"
              if os.environ.get("VOZ") == "tratada" else "anull")
ffmpeg_wav(["-i", fonte, "-vn", "-af", FILTRO_VOZ], f"{tmp}/voz.wav")
ffmpeg_wav(["-i", trilha, "-af", "equalizer=f=2500:t=q:w=1.4:g=-4"], f"{tmp}/mus.wav")   # abre espaço para a voz
voz, mus = ler(f"{tmp}/voz.wav"), ler(f"{tmp}/mus.wav")
N = int(TOTAL * SR)
voz = np.pad(voz, ((0, max(0, N - len(voz))), (0, 0)))[:N]
mus = np.pad(mus, ((0, max(0, N - len(mus))), (0, 0)))[:N]

fala = np.zeros(N, bool)
for w in json.load(open(palavras)):
    a, b = int(max(0, w["s"] - .15) * SR), int(min(TOTAL, w["e"] + .15) * SR)
    fala[a:b] = True
idx = np.flatnonzero(np.diff(fala.astype(int)))
for k in range(1, len(idx) - 1, 2):
    if (idx[k + 1] - idx[k]) < .35 * SR: fala[idx[k]:idx[k + 1] + 1] = True

rms = lambda x: np.sqrt(np.mean(x ** 2) + 1e-12)
voz_db = 20 * np.log10(rms(voz[fala])) if fala.any() else -30.0
mus_db = 20 * np.log10(rms(mus[int(.5 * SR):int(min(TOTAL, END) * SR)]))

alvo = np.where(fala, SOB_FALA, RESPIRO).astype(np.float32)
alvo[int(END * SR):] = ENCERRAMENTO
k = int(.25 * SR); ker = np.ones(k) / k
alvo = np.convolve(np.pad(alvo, (k, k), mode="edge"), ker, mode="same")[k:-k]
ganho = 10 ** ((voz_db + alvo - mus_db) / 20)
fade_in = np.clip(np.arange(N) / (.4 * SR), 0, 1); fade_out = np.clip((N - np.arange(N)) / (1.2 * SR), 0, 1)
mix = voz + mus * (ganho * fade_in * fade_out)[:, None]

pre = f"{tmp}/pre.wav"
with wave.open(pre, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())

r = subprocess.run(["ffmpeg", "-hide_banner", "-i", pre, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                   capture_output=True, text=True).stderr
m = json.loads(r[r.rfind("{"):r.rfind("}") + 1])
g = min(-14 - float(m["input_i"]), -1.0 - float(m["input_tp"]))
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", pre, "-af", f"volume={g:.2f}dB", "-ar", str(SR), "-c:a", "pcm_s16le", saida], check=True)

mg = mus * ganho[:, None]
def rel(mask): return 20 * np.log10(rms(mg[mask])) - voz_db if mask.any() else float("nan")
resp = (~fala); resp[int(END * SR):] = False; resp[:int(.5 * SR)] = False
enc = np.zeros(N, bool); enc[int(END * SR):int(max(END, TOTAL - 1.3) * SR)] = True
print(f"ganho final {g:+.2f} dB -> {float(m['input_i']) + g:.1f} LUFS")
print(f"trilha vs voz: sob a fala {rel(fala):.1f} dB | respiros {rel(resp):.1f} dB | encerramento {rel(enc):.1f} dB -> {saida}")
