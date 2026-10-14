"""Monta o áudio de validação da VSL: voz + trilha sintetizada por fase + efeitos de impacto.

Uso: python3 montar_audio.py segmentos.json <pasta_voz> <saida.mp3> <marcacoes.md>
Trilha e efeitos são gerados aqui (sem samples externos). Música ~20 dB abaixo da voz na fala,
~14 dB nos respiros, ganho final fixo (sem loudnorm dinâmico).
"""
import json, os, subprocess, sys
import numpy as np

SR = 32000
rng = np.random.default_rng(7)
segs, pasta_voz, saida, marc = json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3], sys.argv[4]


# ---------------- utilidades ----------------
def tt(d): return np.arange(int(d * SR)) / SR
def db(x): return 10 ** (x / 20)
def rms(x): return float(np.sqrt(np.mean(x ** 2) + 1e-12))


def fftconv(x, h):
    n = len(x) + len(h) - 1; N = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(h, N), N)[:n]


def reverb(x, dur=2.8, decay=2.2, mix=.35):
    ir = rng.standard_normal(int(dur * SR)) * np.exp(-tt(dur) * decay)
    ir = np.convolve(ir, np.ones(6) / 6, "same"); ir /= np.sqrt(np.sum(ir ** 2))
    w = fftconv(x, ir)[:len(x)]
    return (1 - mix) * x + mix * w * (rms(x) / (rms(w) + 1e-9))


def lowpass(x, k):  # média móvel simples
    return np.convolve(x, np.ones(k) / k, "same")


def nota(n):  # nome -> Hz (A4=440)
    nomes = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}
    base = nomes[n[0]] + (1 if "#" in n else -1 if "b" in n[1:2] else 0)
    oit = int(n[-1]); return 440 * 2 ** ((base + 12 * (oit - 4)) / 12)


ACORDES = {"Am": ["A2", "E3", "A3", "C4", "E4"], "F": ["F2", "C3", "F3", "A3", "C4"],
           "C": ["C3", "G3", "C4", "E4", "G4"], "G": ["G2", "D3", "G3", "B3", "D4"],
           "Dm": ["D3", "A3", "D4", "F4", "A4"], "E": ["E2", "B2", "E3", "G#3", "B3"],
           "D": ["D3", "A3", "D4", "F#4", "A4"], "Bb": ["Bb2", "F3", "Bb3", "D4", "F4"]}


# ---------------- instrumentos ----------------
_cache_piano = {}


def piano(f, d=3.0):
    chave = (round(f, 2), d)
    if chave not in _cache_piano:
        x = tt(d); s_ = sum((1 / k ** 1.4) * np.sin(2 * np.pi * f * k * (1 + .0004 * k * k) * x) * np.exp(-x * (1.2 + .9 * k)) for k in range(1, 7))
        _cache_piano[chave] = s_ * np.minimum(1, x / .005)
    return _cache_piano[chave]


_tabelas = {}


def tabela(harm):
    if harm not in _tabelas:
        th = np.linspace(0, 2 * np.pi, 4096, endpoint=False)
        _tabelas[harm] = sum(np.sin(k * th) / k for k in range(1, harm + 1)).astype(np.float32)
    return _tabelas[harm]


def tom_sustentado(f, d, harm=8, vib=0.0, ataque=1.5, soltura=1.5):
    x = tt(d); out = np.zeros_like(x); tab = tabela(harm)
    for det in (-.003, 0, .003):
        fase = f * (1 + det) * x + (vib * f / (2 * np.pi * 5) * np.sin(2 * np.pi * 5 * x) if vib else 0)
        out += tab[((fase % 1.0) * 4096).astype(np.int32)]
    env = np.minimum(1, x / ataque) * np.minimum(1, (d - x) / soltura)
    return out * np.clip(env, 0, 1) / 3


def pad(acordes, dur_acorde, d, harm=5, vib=0.0, ataque=1.5):
    out = np.zeros(int(d * SR)); t0 = 0.0; i = 0
    while t0 < d:
        ac = ACORDES[acordes[i % len(acordes)]]; dd = min(dur_acorde + 1.5, d - t0)
        if dd <= .2: break
        s = sum(tom_sustentado(nota(n), dd, harm, vib, min(ataque, dd / 3), min(1.5, dd / 3)) for n in ac[1:]) / 4
        a = int(t0 * SR); out[a:a + len(s)] += s[:len(out) - a]; t0 += dur_acorde; i += 1
    return out


def arpejo(acordes, dur_acorde, passo, d, oit=1.0, vol=.5):
    out = np.zeros(int(d * SR)); t0 = 0.0; i = 0
    while t0 < d:
        ac = ACORDES[acordes[int(t0 // dur_acorde) % len(acordes)]]
        f = nota(ac[1 + i % (len(ac) - 1)]) * oit; s = piano(f, 2.5) * vol
        a = int(t0 * SR); n = min(len(s), len(out) - a); out[a:a + n] += s[:n]; t0 += passo; i += 1
    return out


def djembe(grave=True):
    x = tt(.4); f = (95 if grave else 220) * (1 + .6 * np.exp(-x * 30))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * (9 if grave else 16))
    return s + .25 * rng.standard_normal(len(x)) * np.exp(-x * 60)


def shaker():
    x = tt(.08); n = np.diff(rng.standard_normal(len(x) + 1)); return n * np.exp(-x * 60) * .15


def percussao(bpm, d, vol=.6, leve=False):
    out = np.zeros(int(d * SR)); b = 60 / bpm; padrao = [1, 0, 2, 1, 0, 2, 2, 0]  # 1 grave, 2 agudo
    k = 0; t0 = 0.0
    while t0 < d:
        p = padrao[k % 8]; a = int(t0 * SR)
        if p and not (leve and p == 2 and k % 4):
            s = djembe(p == 1) * vol; n = min(len(s), len(out) - a); out[a:a + n] += s[:n]
        s = shaker() * vol; n = min(len(s), len(out) - a); out[a:a + n] += s[:n]
        t0 += b / 2; k += 1
    return out


def drone(f, d):
    x = tt(d); lfo = .6 + .4 * np.sin(2 * np.pi * .07 * x)
    n = lowpass(rng.standard_normal(len(x)), 80) * 3
    return (np.sin(2 * np.pi * f * x) + .5 * np.sin(2 * np.pi * f * 1.5 * x) + .3 * np.sin(2 * np.pi * f * 2.01 * x) + .3 * n) * lfo


def batida_coracao(d, bpm=62, vol=1.0):
    out = np.zeros(int(d * SR)); b = 60 / bpm; t0 = 0.0
    while t0 < d:
        for off, a_ in ((0, 1), (.24, .7)):
            x = tt(.25); s = np.sin(2 * np.pi * 52 * x * (1 + .5 * np.exp(-x * 25))) * np.exp(-x * 18) * a_ * vol
            a = int((t0 + off) * SR); n = max(0, min(len(s), len(out) - a)); out[a:a + n] += s[:n]
        t0 += b
    return out


def bips(d, vol=.25):
    out = np.zeros(int(d * SR)); t0 = .3
    while t0 < d:
        x = tt(.12); s = np.sin(2 * np.pi * 980 * x) * np.minimum(1, (0.12 - x) / .02) * vol
        a = int(t0 * SR); n = max(0, min(len(s), len(out) - a)); out[a:a + n] += s[:n]; t0 += 1.05
    return out


def respirador(d):
    out = np.zeros(int(d * SR)); t0 = 0.0
    while t0 < d:
        x = tt(1.6); n = lowpass(rng.standard_normal(len(x)), 18)
        insp = n * np.sin(np.pi * x / 1.6) ** 2 * .9
        x2 = tt(2.0); n2 = lowpass(rng.standard_normal(len(x2)), 40)
        exp_ = n2 * np.sin(np.pi * x2 / 2.0) ** 2 * .6
        clique = rng.standard_normal(int(.01 * SR)) * .4
        for seg, off in ((clique, 0), (insp, .02), (exp_, 1.8)):
            a = int((t0 + off) * SR); k = max(0, min(len(seg), len(out) - a)); out[a:a + k] += seg[:k]
        t0 += 4.2
    return out


def fogo(d):
    x = tt(d); base = lowpass(rng.standard_normal(len(x)), 40) * 2
    estalos = np.zeros(len(x)); idx = rng.choice(len(x), int(d * 9), replace=False)
    for i in idx:
        s = rng.standard_normal(80) * np.exp(-np.arange(80) / 12) * rng.uniform(.3, 1.2); estalos[i:i + 80] += s[:len(x) - i]
    return base * .3 + estalos * .5


def cresc(d, de=.4, ate=1.0):
    return np.linspace(de, ate, int(d * SR))


def trilha(fase, d):
    d = max(d, 1.0); n = int(d * SR)
    if fase == "uti": s = respirador(d) * .8 + bips(d) * 1.2 + drone(41.2, d) * .35 + pad(["Am"], 10, d, 2) * .2
    elif fase == "memoria": s = pad(["F", "C"], 5, d, 3) * .5 + arpejo(["F", "C"], 5, 1.0, d, 2, .25)
    elif fase == "ninar": s = arpejo(["C", "Am", "F", "G"], 4, .75, d, 2, .4) + pad(["C", "Am", "F", "G"], 4, d, 3) * .4
    elif fase == "tensao": s = drone(55, d) * .5 + pad(["Am"], 8, d, 3) * .4 + batida_coracao(d, 50, .25)
    elif fase == "piano": s = arpejo(["Am", "F", "C", "G"], 4, .5, d) + pad(["Am", "F", "C", "G"], 4, d, 3) * .5
    elif fase == "hospital": s = arpejo(["Am", "Dm", "Am", "E"], 6, 1.5, d, vol=.7) + drone(55, d) * .3 + bips(d) * 1.4
    elif fase == "filho": s = pad(["Am", "F", "C", "E"], 6, d, 9, vib=.004, ataque=2.5) + arpejo(["Am", "F", "C", "E"], 6, 1.5, d, 2, .35)
    elif fase == "medo": s = drone(49, d) * .7 + batida_coracao(d, 72, .9) + pad(["Bb", "Am"], 3, d, 4) * .35
    elif fase == "gana": s = pad(["D", "G", "D", "Am"], 4, d, 4) * .7 + percussao(96, d, .55)
    elif fase == "fogo": s = fogo(d) + drone(73.4, d) * .35 + percussao(66, d, .35, leve=True)
    elif fase == "ciencia": s = arpejo(["Am", "F", "C", "G"], 4.36, 60 / 110 / 2, d, 2, .3) + pad(["Am", "F", "C", "G"], 4.36, d, 3) * .45
    elif fase == "pulso": s = batida_coracao(d, 60, .5) + pad(["Dm"], 6, d, 4) * .6 + drone(36.7, d) * .4
    elif fase == "diario": s = (pad(["C", "G", "Am", "F"], 5, d, 9, vib=.004, ataque=2) + arpejo(["C", "G", "Am", "F"], 5, 1.25, d, 2, .3)) * cresc(d)
    elif fase == "silencio": s = pad(["C"], 10, d, 2) * .08
    elif fase == "vitoria": s = pad(["C", "G", "Am", "F"], 4, d, 10, vib=.004, ataque=1) + arpejo(["C", "G", "Am", "F"], 4, .5, d, 2, .45)
    elif fase == "manada": s = (pad(["C", "G", "Am", "F"], 4, d, 9, vib=.004) + percussao(100, d, .4) + arpejo(["C", "G", "Am", "F"], 4, .5, d, 2, .35)) * cresc(d, .5, 1)
    elif fase == "oferta": s = pad(["C", "G", "Am", "F"], 4.8, d, 5) * .7 + arpejo(["C", "G", "Am", "F"], 4.8, .3, d, 2, .3) + percussao(100, d, .25, leve=True)
    elif fase == "leve": s = pad(["F", "C", "G", "Am"], 6, d, 3) * .6 + arpejo(["F", "C", "G", "Am"], 6, 1.5, d, 1, .4)
    elif fase == "fechamento": s = (pad(["Am", "F", "C", "G"], 5, d, 10, vib=.004, ataque=2) + arpejo(["Am", "F", "C", "G"], 5, .625, d, 2, .35)) * cresc(d, .5, 1)
    else: s = np.zeros(n)
    s = reverb(s[:n]); return s / (rms(s) + 1e-9)


# ---------------- efeitos ----------------
def sfx(nome):
    if nome in ("isqueiro", "isqueiro_falha"):
        x = tt(.06); clique = rng.standard_normal(len(x)) * np.exp(-x * 400)
        anel = sum(np.sin(2 * np.pi * f * x) for f in (3200, 4700, 6100)) * np.exp(-x * 70) * .4
        s = np.concatenate([clique + anel, np.zeros(int(.05 * SR))])
        if nome == "isqueiro":
            y = tt(.9); chama = lowpass(rng.standard_normal(len(y)), 25) * np.sin(np.pi * y / .9) * 1.5
            s = np.concatenate([s, chama])
        else:
            s = np.concatenate([s, np.zeros(int(.35 * SR)), s * .8, np.zeros(int(.6 * SR))])
        return s * 1.4
    if nome == "impacto":
        x = tt(2.2); f = 35 + 60 * np.exp(-x * 6)
        boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 2.2)
        ruido = lowpass(rng.standard_normal(len(x)), 12) * np.exp(-x * 14) * 2
        return reverb(boom + ruido, 2.5, 1.6, .3) * 1.6
    if nome == "tum":
        x = tt(.7); return (np.sin(2 * np.pi * 60 * x * (1 + .4 * np.exp(-x * 20))) * np.exp(-x * 6) + rng.standard_normal(len(x)) * np.exp(-x * 120) * .3) * 1.3
    if nome == "whoosh":
        x = tt(1.0); n = rng.standard_normal(len(x)); env = np.sin(np.pi * x) ** 2
        return (lowpass(n, 6) * (1 - x) + lowpass(n, 30) * 3 * x) * env * .9
    if nome == "riser":
        x = tt(2.6); f = 180 * (1 + 5 * (x / 2.6) ** 2)
        tom = np.sin(2 * np.pi * np.cumsum(f) / SR) * .4
        return (tom + lowpass(rng.standard_normal(len(x)), 4) * .6) * (x / 2.6) ** 2 * 1.2
    if nome == "sibilo":
        x = tt(1.6); n = np.diff(rng.standard_normal(len(x) + 1)); return n * np.sin(np.pi * x / 1.6) * .35
    if nome == "brilho":
        x = tt(2.0); return sum(np.sin(2 * np.pi * f * x) * np.exp(-x * (2 + i)) * np.minimum(1, x / (.005 + .08 * i)) for i, f in enumerate((1568, 2093, 2637, 3136))) * .35
    if nome == "monitor": return bips(3.2, 1.0)
    if nome == "linha_reta":
        x = tt(2.6); return np.sin(2 * np.pi * 980 * x) * np.minimum(1, (2.6 - x) / .3) * .35
    if nome == "coracao": return batida_coracao(4.2, 66, 1.4)
    if nome == "respirador": return respirador(6.0) * 1.2
    if nome == "alarme":
        x = tt(.18); bip = np.sin(2 * np.pi * 1250 * x) * np.minimum(1, (.18 - x) / .02)
        out = np.zeros(int(3.2 * SR))
        for i in range(6):
            a = int(i * .32 * SR); out[a:a + len(bip)] += bip * (1 if i % 2 == 0 else .7)
        return out * .5
    if nome == "sirene":
        x = tt(4.5); f = 750 + 250 * np.sin(2 * np.pi * .9 * x)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.minimum(1, x / .8) * np.minimum(1, (4.5 - x) / 1.2) * .35
    return np.zeros(1)


# avanço da timeline depois de cada efeito (s) e deslocamento do início (negativo = começa antes da fala)
AVANCO = {"respirador": 2.2, "alarme": .4, "sirene": 1.0, "isqueiro": .9, "isqueiro_falha": 1.8, "impacto": .35, "tum": .3, "whoosh": .25, "riser": 0, "sibilo": .5,
          "brilho": .3, "monitor": .9, "linha_reta": 2.8, "coracao": .4, "silencio": 1.2}
INICIO = {"riser": -2.6, "whoosh": -.45}


# ---------------- linha do tempo ----------------
def carregar(mp3):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", mp3, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, np.float32).copy(); v = np.flatnonzero(np.abs(x) > .01)
    return x[max(0, v[0] - int(.03 * SR)):v[-1] + int(.08 * SR)] if len(v) else x


eventos_voz, eventos_sfx, fases, cenas_t = [], [], [], []
t = 1.0
for s in segs:
    if not fases or fases[-1][0] != s["fase"]:
        fases.append([s["fase"], t])
    for nome in s["sfx"]:
        if nome != "silencio":
            eventos_sfx.append((max(0, t + INICIO.get(nome, 0)), nome))
        t += AVANCO.get(nome, 0)
    cenas_t.append((s["id"], t, s["emocao"], s["fase"]))
    for i, _ in enumerate(s["frases"]):
        x = carregar(os.path.join(pasta_voz, f"{s['id']}_{i:02d}.mp3"))
        eventos_voz.append((t, x)); t += len(x) / SR + s["pausa_frase"]
    t += s["pausa_cena"] - s["pausa_frase"] if s["frases"] else .4
TOTAL = t + 3.0
N = int(TOTAL * SR)

voz = np.zeros(N); fala = np.zeros(N, bool)
for t0, x in eventos_voz:
    a = int(t0 * SR); voz[a:a + len(x)] += x; fala[a:a + len(x)] = True

# trilha por fase, com cruzamento de 2 s
mus = np.zeros(N); XF = 2.0
for i, (fase, t0) in enumerate(fases):
    t1 = fases[i + 1][1] if i + 1 < len(fases) else TOTAL
    s = trilha(fase, t1 - t0 + XF); a = int(t0 * SR); n = min(len(s), N - a)
    env = np.ones(n); k = int(XF * SR)
    env[:min(k, n)] = np.linspace(0, 1, min(k, n)) if i else 1
    if i + 1 < len(fases): env[-min(k, n):] = np.linspace(1, 0, min(k, n))
    mus[a:a + n] += s[:n] * env

# ducking: -20 dB sob a fala, -14 nos respiros (suavizado)
v_db = 20 * np.log10(rms(voz[fala]))
alvo = np.where(fala, -20.0, -14.0)
k = int(.3 * SR); alvo = np.convolve(np.pad(alvo, (k, k), mode="edge"), np.ones(k) / k, "same")[k:-k]
mix = voz + mus * db(v_db + alvo)

for t0, nome in eventos_sfx:
    s = sfx(nome); s = s / (rms(s) + 1e-9) * db(v_db - {"impacto": 7, "coracao": 6, "isqueiro": 6, "isqueiro_falha": 6, "monitor": 12, "linha_reta": 12, "respirador": 10, "alarme": 17, "sirene": 14}.get(nome, 10))
    a = int(t0 * SR); n = min(len(s), N - a); mix[a:a + n] += s[:n]

# fade final; ganho fixo para a fala ficar em ~-19 dBFS RMS (~-16 LUFS) e limitador suave só nos picos dos efeitos
mix[-int(2.5 * SR):] *= np.linspace(1, 0, int(2.5 * SR))
mix *= db(-15.5 - v_db)
lim = db(-5); acima = np.abs(mix) > lim
mix[acima] = np.sign(mix[acima]) * (lim + (db(-3) - lim) * np.tanh((np.abs(mix[acima]) - lim) / (db(-3) - lim)))
tmp = saida + ".wav"
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-ac", "2", "-ar", "44100", tmp],
               input=mix.astype(np.float32).tobytes(), check=True)
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", tmp, "-c:a", "libmp3lame", "-b:a", "128k", saida], check=True)
os.remove(tmp)

with open(marc, "w") as f:
    f.write("# Marcações do áudio de validação (tempo de cada cena)\n\n| Cena | Tempo | Emoção | Trilha |\n|---|---|---|---|\n")
    for cid, t0, e, fase in cenas_t:
        f.write(f"| {cid} | {int(t0 // 60)}:{t0 % 60:04.1f} | {e} | {fase} |\n")
print(f"ok {saida}: {TOTAL / 60:.1f} min, {len(eventos_voz)} frases, {len(eventos_sfx)} efeitos, {len(fases)} trechos de trilha")
