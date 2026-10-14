"""Confere cada take de voz contra o texto do roteiro: transcreve sem dica (Whisper) e compara palavra a palavra.

Uso: python3 avaliar_takes.py segmentos.json <pasta_voz> <saida.json> [--modelo medium] [--so ID_00,ID_01]
Saída: para cada take, a nota de semelhança (0–1), as palavras que faltaram/sobraram e a duração.
Take com nota < 0,9, palavra faltando ou fala rápida demais = refazer.
"""
import argparse, difflib, json, os, re, subprocess, sys, unicodedata
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "ferramentas"))
import _rede  # noqa: F401
from faster_whisper import WhisperModel

ap = argparse.ArgumentParser()
ap.add_argument("segmentos"); ap.add_argument("pasta"); ap.add_argument("saida")
ap.add_argument("--modelo", default="medium"); ap.add_argument("--so", default="")
a = ap.parse_args()

NUM = {"0": "zero", "1": "um", "2": "dois", "3": "tres", "4": "quatro", "5": "cinco", "6": "seis", "7": "sete", "8": "oito", "9": "nove",
       "10": "dez", "11": "onze", "12": "doze", "14": "quatorze", "15": "quinze", "19": "dezenove", "20": "vinte", "25": "vinte e cinco",
       "30": "trinta", "37": "trinta e sete", "40": "quarenta", "42": "quarenta e dois", "43": "quarenta e tres", "44": "quarenta e quatro",
       "67": "sessenta e sete", "70": "setenta", "75": "setenta e cinco", "100": "cem", "200": "duzentos", "300": "trezentos", "360": "trezentos e sessenta"}


def norm(t):
    t = unicodedata.normalize("NFD", t.lower()); t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = t.replace("pra ", "para ").replace("pro ", "para o ").replace("ta ", "esta ").replace("to ", "estou ")
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return [w for x in t.split() for w in NUM.get(x, x).split()]


m = WhisperModel(a.modelo, device="cpu", compute_type="int8")
so = set(filter(None, a.so.split(",")))
res = []
for s in json.load(open(a.segmentos)):
    for i, f in enumerate(s["frases"]):
        nome = f"{s['id']}_{i:02d}"
        if so and nome not in so:
            continue
        p = os.path.join(a.pasta, nome + ".mp3")
        audio = np.frombuffer(subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                                             capture_output=True, check=True).stdout, np.float32)
        segs, _ = m.transcribe(audio, language="pt", beam_size=5, vad_filter=False, condition_on_previous_text=False)
        ouvido = " ".join(x.text.strip() for x in segs)
        esp, ouv = norm(f["texto"]), norm(ouvido)
        sm = difflib.SequenceMatcher(None, esp, ouv)
        faltou = [" ".join(esp[i1:i2]) for op, i1, i2, j1, j2 in sm.get_opcodes() if op in ("delete", "replace")]
        trocou = [" ".join(ouv[j1:j2]) for op, i1, i2, j1, j2 in sm.get_opcodes() if op in ("insert", "replace")]
        dur = len(audio) / 16000
        r = {"take": nome, "voz": f["voz"], "nota": round(sm.ratio(), 3), "dur": round(dur, 2), "seg_por_palavra": round(dur / max(1, len(esp)), 3),
             "texto": f["texto"], "ouvido": ouvido, "faltou": faltou, "trocou_por": trocou}
        res.append(r)
        if r["nota"] < .9 or r["seg_por_palavra"] < .25:
            print(f"{nome} nota={r['nota']} | esperado: {f['texto'][:70]} | ouvido: {ouvido[:70]}", flush=True)
json.dump(res, open(a.saida, "w"), ensure_ascii=False, indent=1)
ruins = [r for r in res if r["nota"] < .9 or r["seg_por_palavra"] < .25]
print(f"FIM: {len(res)} takes, {len(ruins)} com problema")
