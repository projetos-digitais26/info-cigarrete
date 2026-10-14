"""Separa a música de fundo da voz de um vídeo (Demucs via fal.ai) — para reaproveitar a trilha
que o cliente já usa em outro vídeo.

Uso: python3 ferramentas/separar_musica.py <video_ou_audio> <pasta_saida>
Saída: <pasta_saida>/musica.wav (bateria + baixo + outros) e <pasta_saida>/voz.wav
Precisa da variável FAL_KEY. Custo baixo (centavos por minuto de áudio).
Depois, se a música estava abaixada sob a fala no original, rode nivelar_trilha.py.
"""
import base64, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
import _rede  # noqa: F401

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
mp3 = os.path.join(out, "_entrada.mp3")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-vn", "-ac", "2", "-ar", "44100", "-b:a", "192k", mp3], check=True)
inp = os.path.join(out, "demucs.json")
json.dump({"audio_url": "data:audio/mpeg;base64," + base64.b64encode(open(mp3, "rb").read()).decode(),
           "model": "htdemucs_ft", "stems": ["vocals", "drums", "bass", "other"], "output_format": "wav"}, open(inp, "w"))
subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "fal.py"), "run", "fal-ai/demucs", inp, out], check=True)
res = json.load(open(os.path.join(out, "demucs.result.json")))
ordem = [k for k, v in res.items() if isinstance(v, dict) and v.get("url")]
arq = {k: os.path.join(out, f"demucs_{i}.wav") for i, k in enumerate(ordem)}
inst = [arq[k] for k in ("drums", "bass", "other") if k in arq]
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *sum([["-i", f] for f in inst], []),
                "-filter_complex", f"amix=inputs={len(inst)}:normalize=0", "-c:a", "pcm_s16le", os.path.join(out, "musica.wav")], check=True)
if "vocals" in arq:
    os.replace(arq["vocals"], os.path.join(out, "voz.wav"))
os.remove(inp); os.remove(mp3)
print("ok:", os.path.join(out, "musica.wav"))
