"""Extrai a narração da VSL PT-BR, adapta para narradora (Márcia) e define emoção, trilha e efeitos por cena.

Uso: python3 roteiro_audio.py ../vsl-v2-pt-br.md segmentos.json narracao-feminina.md
"""
import json, re, sys

src, out_json, out_md = sys.argv[1], sys.argv[2], sys.argv[3]
texto = open(src).read()

# ---------- cenas ----------
cenas = []
for bloco in re.split(r"\n(?=\*\*C\d+[a-z]? · )", texto):
    m = re.match(r"\*\*(C\d+[a-z]?) · ", bloco)
    if not m:
        continue
    vo = " ".join(l[2:].strip() for l in bloco.splitlines() if l.startswith("> "))
    vo = re.sub(r"`\[[^\]]*\]`", "", vo)            # marcações de prova/fonte
    vo = re.sub(r"\[Depoimento real \d\]", "", vo)
    vo = vo.replace("(sem narração)", "")
    cenas.append({"id": m.group(1), "vo": re.sub(r"\s+", " ", vo).strip()})

# ---------- narradora ----------
TROCAS = [
    ("Meu nome é Marcos.", "Meu nome é Márcia."),
    ('"Marcos, eu fumo há 30 anos."', '"Márcia, eu fumo há 30 anos."'),
    ("As minhas roupas, as roupas da Luciana, minha esposa.", "As minhas roupas, as roupas do Luciano, meu marido."),
    ("Ela nunca brigou comigo. Ela só abria a janela.", "Ele nunca brigou comigo. Ele só abria a janela."),
    ("uma esposa que me amava", "um marido que me amava"),
    ("a Luciana olhou pra mim e disse", "o Luciano olhou pra mim e disse"),
    ("Ela tinha uma amiga de infância", "Ele tinha um amigo de infância"),
    ("pra amiga da Luciana, a Ama,", "pro amigo do Luciano, o Kofi,"),
    ("No dia seguinte ela me levou", "No dia seguinte ele me levou"),
    ("Ela riu e disse", "Ele riu e disse"),
    ("A Luciana percebeu antes de mim", "O Luciano percebeu antes de mim"),
    ("Eu corri pra contar pra Luciana. Ela me abraçou", "Eu corri pra contar pro Luciano. Ele me abraçou"),
    ('"Pai, você tá com cheiro de pai."', '"Mãe, você tá com cheiro de mãe."'),
    ('"Papai, não fuma.', '"Mamãe, não fuma.'),
    ("uma esposa, você mesmo", "um marido, você mesmo"),
    ("irritado", "irritada"), ("tranquilo.", "tranquila."), ("confuso", "confusa"),
    ("arrepiado", "arrepiada"), ("Eu era o único. Eu, o turista,", "Eu era a única. Eu, a turista,"),
    ("Dez minutos depois de ver o meu pai morrer por causa do cigarro, eu estava fumando.",
     "Dez minutos depois de ver o meu pai morrer por causa do cigarro, eu estava fumando."),
    ("Eu sei o que é isso. E sei o que isso faz com um casamento.",
     "E nas mulheres, o cigarro rouba o colágeno, envelhece a pele, apaga o brilho do rosto. Eu via isso no espelho, todo santo dia."),
]
for c in cenas:
    for a, b in TROCAS:
        c["vo"] = c["vo"].replace(a, b)
    c["vo"] = c["vo"].replace("R$ [PREÇO]", "37 reais").replace("[PREÇO]", "37 reais")
    c["vo"] = c["vo"].replace("em [X] dias", "em três dias")
    c["vo"] = c["vo"].replace("Ou em até 12 parcelas que custam menos que um maço de cigarro.",
                              "Ou em até 12 parcelas, que custam menos que um maço de cigarro.")

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
    "C01": "choque", "C02": "impacto", "C03": "misterio", "C04": "choque", "C05": "impacto", "C05b": "medo",
    "C06": "esperanca", "C07": "esperanca", "C08": "intimo", "C08b": "misterio",
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
FASES = [("tensao", "C01"), ("piano", "C09"), ("hospital", "C13"), ("filho", "C28"), ("tensao", "C34"),
         ("medo", "C37a"), ("tensao", "C38"), ("gana", "C41"), ("fogo", "C51"), ("ciencia", "C61"),
         ("pulso", "C66"), ("diario", "C72"), ("silencio", "C78"), ("vitoria", "C80"), ("manada", "C82"),
         ("gana", "C85"), ("oferta", "C90"), ("leve", "C100"), ("fechamento", "C106"), ("hospital", "C106b"),
         ("fechamento", "C107")]
# ---------- efeitos (antes da fala da cena) ----------
SFX = {
    "C01": ["isqueiro"], "C04": ["impacto"], "C05b": ["impacto", "coracao"], "C08b": ["riser"],
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
    frases = [f.strip() for f in re.split(r"(?<=[.!?…])\s+(?=[A-ZÀ-Ú\"“(])", c["vo"]) if f.strip()]
    out.append({"id": c["id"], "emocao": e, "fase": fase, "rate": rate, "pitch": pitch,
                "pausa_frase": pausa_frase, "pausa_cena": pausa_cena, "sfx": SFX.get(c["id"], []), "frases": frases})

json.dump(out, open(out_json, "w"), ensure_ascii=False, indent=1)
with open(out_md, "w") as f:
    f.write("# Narração feminina — VSL V2 PT-BR (Márcia)\n\nTexto exato usado no áudio de validação, com a emoção de cada cena.\n\n")
    for s in out:
        if s["frases"]:
            f.write(f"**{s['id']}** _({s['emocao']})_ {' '.join(s['frases'])}\n\n")
print(len(out), "cenas,", sum(len(s["frases"]) for s in out), "frases,",
      sum(len(" ".join(s["frases"]).split()) for s in out), "palavras")
