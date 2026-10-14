"""Monta o vídeo 9:16 da VSL plano a plano, no tempo exato do áudio do ElevenLabs.

Uso (na pasta cinematografia/):
  python3 montar_video.py animatic.mp4 [--ate C12] [--de A01]     cartões/quadros-chave no lugar do que ainda não tem vídeo
  python3 montar_video.py vsl-video.mp4                            versão com todos os takes (mesmo comando)

Para cada plano usa, nesta ordem: clips/<id>.mp4 → kf/<id>.png (com zoom lento) → cartão com a descrição do plano.
Duração do plano = peso × duração da cena (cenas-tempo.json). Aplica o grade da fase e a quebra de padrão do plano.
Texto na tela e legendas entram depois, pelo overlay HTML (ferramentas/render_overlay.js).
"""
import argparse, json, os, subprocess, textwrap
AQUI = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(AQUI, "..", "audio", "vsl-v2-pt-elevenlabs.mp3")
FONTE = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FPS, W, H = 30, 1080, 1920

ap = argparse.ArgumentParser()
ap.add_argument("saida"); ap.add_argument("--de", default=""); ap.add_argument("--ate", default="")
a = ap.parse_args()

cenas = json.load(open(os.path.join(AQUI, "cenas-tempo.json")))
planos = json.load(open(os.path.join(AQUI, "planos.json")))
ids = [c["cena"] for c in cenas]
i0 = ids.index(a.de) if a.de else 0
i1 = ids.index(a.ate) if a.ate else len(ids) - 1

GRADE = {
    "uti": "eq=saturation=.55:contrast=1.08,colorbalance=bs=.12:ms=.05", "hospital": "eq=saturation=.55:contrast=1.08,colorbalance=bs=.12:ms=.05",
    "memoria": "eq=saturation=.9,colorbalance=rs=.08:ms=.04", "piano": "eq=saturation=.9,colorbalance=rs=.08:ms=.04", "ninar": "eq=saturation=.9,colorbalance=rs=.08:ms=.04",
    "tensao": "eq=contrast=1.18:saturation=.8", "medo": "eq=contrast=1.18:saturation=.8", "pulso": "eq=contrast=1.18:saturation=.8",
    "fogo": "eq=contrast=1.15,colorbalance=rh=.1:bs=-.05", "gana": "eq=saturation=1.15,colorbalance=rh=.06:mh=.04",
    "ciencia": "eq=saturation=.85,colorbalance=bs=.06", "diario": "eq=saturation=1.05:gamma=1.03", "leve": "eq=saturation=1.05:gamma=1.03",
    "vitoria": "eq=saturation=1.05:gamma=1.03", "filho": "eq=saturation=.95,colorbalance=rs=.05",
}
COR_CARTAO = {"uti": "0x0d1b2a", "hospital": "0x0d1b2a", "silencio": "black", "gana": "0x3d2a10", "fogo": "0x2a1205", "ciencia": "0x0b2530",
              "oferta": "0x14110a", "fechamento": "0x14110a"}
QUEBRA = {   # efeito aplicado no começo do plano
    "flash_branco": "fade=t=in:st=0:d=0.13:color=white",
    "preto": "fade=t=in:st=0:d=0.35:color=black",
    "corte_seco": "",
    "zoom_punch": "scale=w='trunc(1080*(1+0.15*max(0\\,1-t/0.16))/2)*2':h=-2:eval=frame,crop=1080:1920",
    "glitch": "rgbashift=rh=14:bh=-14:rv=4:enable='lt(t,0.17)'",
    "whip": "gblur=sigma=40:steps=1:enable='lt(t,0.12)'",
    "freeze": "",          # o congelamento entra no começo via tpad (abaixo)
}
NORMAL = f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},setsar=1"


def dur_media(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                                capture_output=True, text=True).stdout or 0)


def esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%").replace(",", "\\,")


# linha do tempo: início de cada plano
linha = []
for k in range(i0, i1 + 1):
    c = cenas[k]
    ps = sorted([p for p in planos if p["cena"] == c["cena"]], key=lambda p: p["ordem"])
    t = c["inicio"] if k > 0 else 0.0
    fim = cenas[k + 1]["inicio"] if k + 1 < len(cenas) else c["inicio"] + c["dur"]
    if not ps:
        ps = [{"id": c["cena"] + "-0", "cena": c["cena"], "peso": 1, "tipo": "preto", "enquadramento": "(sem plano)", "quebra": None}]
    total = fim - t
    for p in ps:
        d = total * p["peso"] / sum(q["peso"] for q in ps)
        linha.append((p, c, t, d)); t += d
inicio_trecho = linha[0][2]

seg_dir = os.path.join(AQUI, "render", "seg"); os.makedirs(seg_dir, exist_ok=True)
lista = []
for p, c, t0, d in linha:
    n = max(1, round((t0 + d - inicio_trecho) * FPS) - round((t0 - inicio_trecho) * FPS))   # quadros inteiros sem acumular erro
    d = n / FPS
    clip, kf = os.path.join(AQUI, "clips", p["id"] + ".mp4"), os.path.join(AQUI, "kf", p["id"] + ".png")
    alvo = os.path.join(seg_dir, p["id"] + ".mp4")
    grade = GRADE.get(c["fase"], "eq=saturation=1")
    fx = [QUEBRA.get(p.get("quebra") or "", "")]
    if p.get("quebra") == "freeze":
        fx.insert(0, "tpad=start_duration=0.6:start_mode=clone")
    if os.path.exists(clip):
        dc = dur_media(clip)
        lento = f"setpts={min(1.6, d / dc):.3f}*PTS," if dc < d else ""   # estica até 1,6× (câmera lenta) e congela o resto
        src = ["-i", clip]
        vf = f"{lento}{NORMAL},tpad=stop_mode=clone:stop_duration={d:.2f}"
    elif os.path.exists(kf):
        src = ["-loop", "1", "-i", kf]
        vf = f"scale=1296:2304:flags=lanczos,zoompan=z='1+0.0009*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={FPS},setsar=1"
    else:
        cor = COR_CARTAO.get(c["fase"], "0x222222")
        txt = "\n".join(textwrap.wrap(p.get("enquadramento") or p["tipo"], 30))[:400]
        tt = (p.get("texto_tela") or {}).get("texto", "") if isinstance(p.get("texto_tela"), dict) else ""
        src = ["-f", "lavfi", "-i", f"color=c={cor}:s={W}x{H}:r={FPS}"]
        vf = (f"drawtext=fontfile={FONTE}:text='{esc(p['id'] + '  ' + p['tipo'].upper())}':x=60:y=120:fontsize=46:fontcolor=white@0.6,"
              f"drawtext=fontfile={FONTE}:text='{esc(txt)}':x=60:y=560:fontsize=44:fontcolor=white:line_spacing=14")
        if tt:
            vf += f",drawtext=fontfile={FONTE}:text='{esc(tt[:60])}':x=(w-tw)/2:y=260:fontsize=56:fontcolor=0xffd36b:box=1:boxcolor=black@0.5:boxborderw=18"
        if p["tipo"] == "preto":
            vf = "drawbox=c=black:t=fill"
    vf = ",".join(filter(None, [vf, grade, *fx, "noise=alls=8:allf=t", "vignette=PI/5", "format=yuv420p"]))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *src, "-vf", vf, "-frames:v", str(n), "-r", str(FPS),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-an", alvo], check=True)
    lista.append(alvo)

lista_txt = os.path.join(seg_dir, "lista.txt")
open(lista_txt, "w").write("".join(f"file '{f}'\n" for f in lista))
fim_trecho = linha[-1][2] + linha[-1][3]
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lista_txt,
                "-ss", f"{inicio_trecho:.3f}", "-t", f"{fim_trecho - inicio_trecho:.3f}", "-i", AUDIO,
                "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", a.saida], check=True)
sem = sum(1 for p, *_ in linha if not os.path.exists(os.path.join(AQUI, "clips", p["id"] + ".mp4")))
print(f"ok {a.saida}: {len(linha)} planos, {fim_trecho - inicio_trecho:.1f} s; {sem} planos ainda sem vídeo (cartão ou quadro-chave)")
