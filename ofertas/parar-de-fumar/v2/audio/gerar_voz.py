"""Gera a voz de cada frase (edge-tts, Thalita) com a velocidade/tom da emoção da cena.

Uso: python3 gerar_voz.py segmentos.json <pasta_voz>
"""
import asyncio, json, os, subprocess, sys
import edge_tts

VOZ = "pt-BR-ThalitaMultilingualNeural"
PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
segs, pasta = json.load(open(sys.argv[1])), sys.argv[2]
os.makedirs(pasta, exist_ok=True)
# voz de criança: Thalita mais aguda + deslocamento de timbre (formantes) com asetrate, mantendo o andamento
CRIANCA = ("-10%", "+45Hz", "asetrate=24000*1.17,aresample=24000,atempo=0.855,highpass=f=170")
tarefas = [(f"{s['id']}_{i:02d}", f["texto"], *((CRIANCA[0], CRIANCA[1]) if f["voz"] == "crianca" else (s["rate"], s["pitch"])), f["voz"] == "crianca")
           for s in segs for i, f in enumerate(s["frases"])]
sem = asyncio.Semaphore(4)


async def um(nome, texto, rate, pitch, crianca=False):
    dst = os.path.join(pasta, nome + ".mp3")
    if os.path.exists(dst) and os.path.getsize(dst) > 1000:
        return
    async with sem:
        for tentativa in range(4):
            try:
                bruto = dst + ".tmp.mp3" if crianca else dst
                await edge_tts.Communicate(texto, VOZ, rate=rate, pitch=pitch, proxy=PROXY).save(bruto)
                dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", bruto],
                                           capture_output=True, text=True).stdout or 0)
                if dur / max(1, len(texto.split())) < .22:   # a voz às vezes corta a frase no meio
                    raise RuntimeError(f"frase cortada ({dur:.2f}s)")
                if crianca:
                    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", bruto, "-af", CRIANCA[2], dst], check=True)
                    os.remove(bruto)
                return
            except Exception as e:
                await asyncio.sleep(2 ** tentativa)
        print("FALHOU", nome, e, flush=True)


async def main():
    await asyncio.gather(*(um(*t) for t in tarefas))
    print("ok", len(tarefas), "frases")

asyncio.run(main())
