"""Normalização de texto para comparar roteiro × transcrição (números por extenso, acentos, apelidos)."""
import re, unicodedata

NUM = {"0": "zero", "1": "um", "2": "dois", "3": "tres", "4": "quatro", "5": "cinco", "6": "seis", "7": "sete", "8": "oito", "9": "nove",
       "10": "dez", "11": "onze", "12": "doze", "14": "quatorze", "15": "quinze", "19": "dezenove", "20": "vinte", "25": "vinte e cinco",
       "30": "trinta", "37": "trinta e sete", "40": "quarenta", "42": "quarenta e dois", "43": "quarenta e tres", "44": "quarenta e quatro",
       "67": "sessenta e sete", "70": "setenta", "75": "setenta e cinco", "100": "cem", "200": "duzentos", "300": "trezentos", "360": "trezentos e sessenta"}


ALIAS = {"kuami": "kwame", "kwami": "kwame", "kuame": "kwame", "cuame": "kwame", "cuami": "kwame", "kwamy": "kwame",
         "cofi": "kofi", "kofe": "kofi", "kofy": "kofi", "porque": "por que"}


def norm(t):
    t = re.sub(r"R\$ ?(\d+)(,00)?", r"\1 reais", t)
    t = re.sub(r"\b15º", "décimo quinto", t)
    t = unicodedata.normalize("NFD", t.lower()); t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"\bpra\b", "para", t); t = re.sub(r"\bpro\b", "para o", t); t = re.sub(r"\bta\b", "esta", t)
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return [w for x in t.split() for w in NUM.get(ALIAS.get(x, x), ALIAS.get(x, x)).split()]
