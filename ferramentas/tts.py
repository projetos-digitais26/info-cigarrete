"""Narração em português com voz neural gratuita (edge-tts).

Uso: python3 ferramentas/tts.py "<texto>" <saida.mp3> [voz=pt-BR-ThalitaMultilingualNeural] [rate=-5%] [pitch=+0Hz]
     python3 ferramentas/tts.py --lote narracao.json <pasta_saida>     (JSON: [[id, texto, rate, pitch], ...])
Sempre confira a pronúncia transcrevendo o resultado (transcrever.py). Aprendizados:
- escreva "Pix" (em "PIX" maiúsculo a voz soletra);
- palavra estrangeira no início da frase sai quebrada: reescreva ("O gateway caiu?").
"""
import asyncio, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import _rede  # noqa: F401
import edge_tts

VOZ = "pt-BR-ThalitaMultilingualNeural"


async def um(texto, out, voz=VOZ, rate="-5%", pitch="+0Hz"):
    await edge_tts.Communicate(texto, voz, rate=rate, pitch=pitch).save(out)


async def lote(spec, pasta):
    os.makedirs(pasta, exist_ok=True)
    for i, txt, rate, pitch in json.load(open(spec)):
        await um(txt, os.path.join(pasta, i + ".mp3"), VOZ, rate, pitch); print(i, flush=True)

if len(sys.argv) >= 4 and sys.argv[1] == "--lote":
    asyncio.run(lote(sys.argv[2], sys.argv[3]))
elif len(sys.argv) >= 3:
    asyncio.run(um(sys.argv[1], sys.argv[2], *sys.argv[3:6]))
else:
    print(__doc__)
