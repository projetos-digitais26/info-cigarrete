"""Converte o relatório dos takes no formato do montar_audio.py (cada cena = lista de takes, na ordem).

Uso: python3 juntar_takes.py segmentos.json relatorio-takes.json segmentos-takes.json
Para se algum take não passou na conferência (nota < 0,95), a menos que se use --forcar.
"""
import json, sys

segs, rel, saida = json.load(open(sys.argv[1])), json.load(open(sys.argv[2])), sys.argv[3]
ruins = [r for r in rel if (r.get("nota") or 0) < .95]
if ruins and "--forcar" not in sys.argv:
    for r in ruins:
        print("NÃO PASSOU:", r["id"], r.get("nota"), "|", r["texto"], "| ouvido:", r.get("ouvido"))
    sys.exit(1)
por_cena = {}
for r in rel:
    por_cena.setdefault(r["cena"], []).append(r)
for s in segs:
    s["frases"] = [{"texto": r["texto"], "voz": r["voz"]} for r in sorted(por_cena.get(s["id"], []), key=lambda r: r["id"])]
json.dump(segs, open(saida, "w"), ensure_ascii=False, indent=1)
print("ok", sum(len(s["frases"]) for s in segs), "takes em", len(segs), "cenas")
