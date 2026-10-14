"""Extrai a narração da VSL PT-BR (narradora Márcia + voz de criança da Sofia) e define emoção, trilha e efeitos por cena.

Uso: python3 roteiro_audio.py ../vsl-v2-pt-br.md segmentos.json narracao-feminina.md
"""
import json, re, sys

src, out_json, out_md = sys.argv[1], sys.argv[2], sys.argv[3]
texto = open(src).read()
texto = texto.split("\n## Rodapé")[0]   # o rodapé da página não é narrado

# ---------- cenas ----------
cenas = []
for bloco in re.split(r"\n(?=\*\*[ACU]\d+[a-z]? · )", texto):
    m = re.match(r"\*\*([ACU]\d+[a-z]?) · ", bloco)
    if not m:
        continue
    falas = []
    for l in bloco.splitlines():
        if not l.startswith("> "):
            continue
        l = l[2:].strip(); quem = "crianca" if l.startswith("🧒") else "narradora"
        l = l.lstrip("🧒").strip()
        l = re.sub(r"`\[[^\]]*\]`", "", l); l = re.sub(r"\[Depoimento real \d\]", "", l).replace("(sem narração)", "")
        l = re.sub(r"\s+", " ", l).strip()
        if l:
            falas.append((quem, l))
    cenas.append({"id": m.group(1), "falas": falas})

def preco(t):
    t = t.replace("R$ [PREÇO]", "37 reais").replace("[PREÇO]", "37 reais").replace("em [X] dias", "em três dias")
    return t.replace("Ou em até 12 parcelas que custam", "Ou em até 12 parcelas, que custam")


for c in cenas:
    c["falas"] = [(q, preco(t)) for q, t in c["falas"]]

# ---------- emoção (velocidade, tom, pausa entre frases, pausa depois da cena) ----------
EST = {
    "impacto":   ("-12%", "-4Hz", .55, 1.0),
    "intimo":    ("-8%",  "-2Hz", .45, .7),
    "dor":       ("-16%", "-6Hz", .7,  1.0),
    "choque":    ("-22%", "-8Hz", .9,  1.6),
    "medo":      ("-10%", "-4Hz", .5,  .8),
    "revelacao": ("-7%",  "-1Hz", .5,  .8),
    "misterio":  ("-14%", "-5Hz", .6,  1.0),
    "esperanca": ("-5%",  "+2Hz", .45, .7),
    "alegria":   ("-2%",  "+4Hz", .4,  .7),
    "venda":     ("+0%",  "+1Hz", .35, .6),
    "urgencia":  ("+3%",  "+1Hz", .3,  .6),
}
EMOCAO = {
    "A01": "dor", "A02": "dor", "A03": "dor", "A04": "choque", "A05": "dor", "A06": "choque", "A07": "misterio",
    "A08": "dor", "A09": "intimo", "A10": "intimo", "A11": "misterio", "A12": "esperanca", "A13": "intimo", "A14": "misterio",
    "U01": "medo", "U02": "dor", "U03": "choque", "U04": "dor", "U05": "impacto", "C109b": "intimo",
    "C09": "intimo", "C10": "dor", "C11": "revelacao", "C12": "misterio",
    "C13": "dor", "C14": "intimo", "C15": "dor", "C16": "dor", "C17": "choque", "C18": "choque",
    "C19": "choque", "C20": "dor", "C21": "choque", "C22": "dor", "C23": "intimo", "C24": "dor",
    "C25": "impacto", "C26": "dor", "C27": "misterio",
    "C28": "dor", "C29": "choque", "C30": "choque", "C31": "dor", "C32": "impacto", "C33": "choque",
    "C34": "impacto", "C35": "dor", "C35b": "revelacao", "C36": "dor", "C37": "dor",
    "C37a": "medo", "C37b": "medo", "C37c": "medo", "C37d": "dor", "C37e": "choque", "C37f": "dor",
    "C37g": "impacto", "C37h": "misterio", "C38": "revelacao", "C39": "revelacao", "C40": "misterio",
    "C41": "intimo", "C42": "intimo", "C43": "esperanca", "C44": "intimo", "C45": "revelacao",
    "C46": "esperanca", "C47": "misterio", "C48": "misterio", "C49": "misterio", "C50": "misterio",
    "C51": "intimo", "C52": "misterio", "C53": "intimo", "C54": "misterio", "C55": "choque",
    "C56": "revelacao", "C57": "misterio", "C58": "impacto", "C59": "revelacao", "C60": "misterio",
    "C61": "revelacao", "C62": "impacto", "C63": "choque", "C64": "revelacao", "C65": "impacto",
    "C66": "impacto", "C67": "revelacao", "C68": "revelacao", "C69": "revelacao", "C70": "esperanca",
    "C71": "misterio",
    "C72": "intimo", "C73": "esperanca", "C74": "esperanca", "C75": "alegria", "C76": "dor",
    "C77": "esperanca", "C78": "misterio", "C79": "choque", "C80": "alegria", "C81": "alegria",
    "C82": "alegria", "C83": "alegria", "C83b": "esperanca", "C83c": "intimo", "C84": "misterio",
    "C85": "intimo", "C86": "impacto", "C87": "revelacao", "C88": "dor", "C89": "esperanca",
    "C90": "venda", "C91": "venda", "C92": "venda", "C93": "impacto", "C94": "venda",
    "C95": "alegria", "C96": "venda", "C97": "venda", "C98": "venda", "C98b": "venda", "C99": "impacto",
    "C100": "urgencia", "C101": "intimo", "C102": "intimo", "C103": "intimo", "C104": "intimo",
    "C105": "intimo", "C106": "dor", "C106b": "choque", "C107": "esperanca", "C108": "intimo",
    "C109": "intimo", "C110": "impacto", "C111": "choque",
}
# ---------- trilha por fase ----------
FASES = [("uti", "A01"), ("silencio", "A06"), ("memoria", "A07"), ("uti", "A08"), ("piano", "A09"), ("tensao", "A11"), ("piano", "C09"), ("hospital", "C13"), ("filho", "C28"), ("tensao", "C34"),
         ("medo", "C37a"), ("uti", "U01"), ("tensao", "C37g"), ("gana", "C41"), ("fogo", "C51"), ("ciencia", "C61"),
         ("pulso", "C66"), ("diario", "C72"), ("silencio", "C78"), ("vitoria", "C80"), ("manada", "C82"),
         ("gana", "C85"), ("oferta", "C90"), ("leve", "C100"), ("fechamento", "C106"), ("hospital", "C106b"),
         ("fechamento", "C107"), ("ninar", "C109b"), ("fechamento", "C110")]
# ---------- efeitos (antes da fala da cena) ----------
SFX = {
    "A01": ["respirador"], "A04": ["alarme", "impacto"], "A05": ["impacto"], "A06": ["silencio"], "A07": ["isqueiro"],
    "A09": ["whoosh"], "A10": ["impacto"], "A11": ["sibilo"], "A14": ["riser"],
    "U01": ["impacto", "monitor"], "U02": ["sirene"], "U03": ["impacto"], "U04": ["isqueiro"], "U05": ["sibilo"],
    "C11": ["impacto"], "C13": ["monitor"], "C17": ["silencio"], "C19": ["linha_reta"], "C21": ["isqueiro", "impacto"],
    "C27": ["whoosh"], "C29": ["impacto"], "C33": ["impacto"], "C35b": ["whoosh"], "C37": ["isqueiro"],
    "C37a": ["impacto", "coracao"], "C37b": ["impacto"], "C37c": ["impacto"], "C37d": ["impacto"],
    "C37e": ["impacto"], "C37g": ["whoosh"], "C37h": ["impacto"], "C38": ["riser"], "C41": ["whoosh"],
    "C45": ["tum"], "C50": ["riser"], "C55": ["sibilo", "impacto"], "C58": ["impacto"], "C61": ["whoosh"],
    "C62": ["tum"], "C63": ["impacto"], "C66": ["tum"], "C67": ["tum"], "C68": ["tum"], "C69": ["tum"],
    "C70": ["impacto"], "C79": ["impacto"], "C83b": ["riser"], "C86": ["impacto"], "C93": ["impacto"],
    "C95": ["brilho"], "C99": ["impacto"], "C106b": ["monitor", "impacto"], "C108": ["whoosh"],
    "C110": ["riser"], "C111": ["isqueiro_falha"],
}

fase, out = None, []
fase_por_inicio = dict((c, f) for f, c in FASES)
for c in cenas:
    fase = fase_por_inicio.get(c["id"], fase)
    e = EMOCAO.get(c["id"], "intimo")
    rate, pitch, pausa_frase, pausa_cena = EST[e]
    frases = []
    for quem, t in c["falas"]:
        for f in re.split(r"(?<=[.!?…])\s+(?=[A-ZÀ-Ú\"“(])", t):
            if f.strip():
                frases.append({"texto": f.strip(), "voz": quem})
    out.append({"id": c["id"], "emocao": e, "fase": fase, "rate": rate, "pitch": pitch,
                "pausa_frase": pausa_frase, "pausa_cena": pausa_cena, "sfx": SFX.get(c["id"], []), "frases": frases})

json.dump(out, open(out_json, "w"), ensure_ascii=False, indent=1)
with open(out_md, "w") as f:
    f.write("# Narração — VSL V2 PT-BR (Márcia + Sofia)\n\nTexto exato do áudio de validação, com a emoção de cada cena. 🧒 = voz da Sofia.\n\n")
    for s_ in out:
        if s_["frases"]:
            f.write(f"**{s_['id']}** _({s_['emocao']})_ " + " ".join(("🧒 " if x["voz"] == "crianca" else "") + x["texto"] for x in s_["frases"]) + "\n\n")
print(len(out), "cenas,", sum(len(s_["frases"]) for s_ in out), "frases,",
      sum(len(x["texto"].split()) for s_ in out for x in s_["frases"]), "palavras")
