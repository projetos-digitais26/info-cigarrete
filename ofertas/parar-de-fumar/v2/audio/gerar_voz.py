"""Gera a voz de cada frase (edge-tts, Thalita) com a velocidade/tom da emoção da cena.

Uso: python3 gerar_voz.py segmentos.json <pasta_voz>
"""
import asyncio, json, os, sys
import edge_tts

VOZ = "pt-BR-ThalitaMultilingualNeural"
PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
segs, pasta = json.load(open(sys.argv[1])), sys.argv[2]
os.makedirs(pasta, exist_ok=True)
tarefas = [(f"{s['id']}_{i:02d}", f, s["rate"], s["pitch"]) for s in segs for i, f in enumerate(s["frases"])]
sem = asyncio.Semaphore(4)


async def um(nome, texto, rate, pitch):
    dst = os.path.join(pasta, nome + ".mp3")
    if os.path.exists(dst) and os.path.getsize(dst) > 1000:
        return
    async with sem:
        for tentativa in range(4):
            try:
                await edge_tts.Communicate(texto, VOZ, rate=rate, pitch=pitch, proxy=PROXY).save(dst)
                return
            except Exception as e:
                await asyncio.sleep(2 ** tentativa)
        print("FALHOU", nome, e, flush=True)


async def main():
    await asyncio.gather(*(um(*t) for t in tarefas))
    print("ok", len(tarefas), "frases")

asyncio.run(main())
