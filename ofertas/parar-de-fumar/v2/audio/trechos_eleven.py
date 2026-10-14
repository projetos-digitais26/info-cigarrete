"""Monta os trechos para o ElevenLabs (1 a 3 cenas seguidas do mesmo locutor, até ~550 caracteres),
com marcação de emoção por cena e pronúncia guiada. Sem [whispers] (pedido do produtor).

Uso: python3 trechos_eleven.py segmentos.json trechos-eleven.json
Cada trecho guarda: id, voz (narradora|crianca), cenas [{id, texto}], prompt (texto com marcações).
"""
import json, re, sys

segs, saida = json.load(open(sys.argv[1])), sys.argv[2]
NARRADORA, CRIANCA = "AKXBn24T1f9tvTDnWzWT", "cabLxBh81HurPAAJfEHo"   # Bruna da Costa · Bea
TAG = {"impacto": "[serious]", "intimo": "[warmly]", "dor": "[sad]", "choque": "[sad] [trembling voice] [slowly]",
       "medo": "[nervous]", "revelacao": "[curious]", "misterio": "[serious] [slowly]", "esperanca": "[warmly]",
       "alegria": "[happy]", "venda": "[excited]", "urgencia": "[excited]"}
TAG_CRIANCA = {"dor": "[childlike voice] [crying] [softly]", "choque": "[childlike voice] [crying] [shouting]",
               "intimo": "[childlike voice] [softly]"}
IPA = {"Kwame": "/ˈkwami/", "Kofi": "/ˈkofi/"}
MAX = 550


def fala(t):
    for k, v in IPA.items():
        t = re.sub(rf"\b{k}\b", v, t)
    return t


# unidades = cena × locutor (uma cena com fala da Sofia no meio vira 2–3 unidades)
unid = []
for s in segs:
    for f in s["frases"]:
        if unid and unid[-1]["cena"] == s["id"] and unid[-1]["voz"] == f["voz"]:
            unid[-1]["texto"] += " " + f["texto"]
        else:
            unid.append({"cena": s["id"], "voz": f["voz"], "emocao": s["emocao"], "texto": f["texto"]})

trechos, cur = [], None
for u in unid:
    tag = (TAG_CRIANCA.get(u["emocao"], TAG_CRIANCA["dor"]) if u["voz"] == "crianca" else TAG.get(u["emocao"], ""))
    parte = f"{tag} {fala(u['texto'])}".strip()
    if cur and cur["voz"] == u["voz"] and len(cur["prompt"]) + len(parte) + 1 <= MAX:
        cur["prompt"] += " " + parte; cur["cenas"].append({"id": u["cena"], "texto": u["texto"]})
    else:
        cur = {"id": f"T{len(trechos) + 1:03d}", "voz": u["voz"], "voice_id": CRIANCA if u["voz"] == "crianca" else NARRADORA,
               "prompt": parte, "cenas": [{"id": u["cena"], "texto": u["texto"]}]}
        trechos.append(cur)
json.dump(trechos, open(saida, "w"), ensure_ascii=False, indent=1)
print(len(trechos), "trechos;", sum(len(t["prompt"]) for t in trechos), "caracteres;",
      sum(1 for t in trechos if t["voz"] == "crianca"), "da Sofia")
