"""Baixa uma fonte do Google Fonts (subconjunto latin, .woff2) para usar nos overlays.

Uso: python3 ferramentas/baixar_fonte.py "<Família>" <pasta_saida> [pesos=400,700] [--italico]
Ex.: python3 ferramentas/baixar_fonte.py "Montserrat" modelos/fonts 600,700,800
     python3 ferramentas/baixar_fonte.py "Playfair Display" modelos/fonts 600,700 --italico
Arquivos: <slug>-<peso>-<normal|italic>.woff2 (ex.: playfair-display-600-italic.woff2)
"""
import os, re, sys, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
import _rede  # noqa: F401
import ssl
CTX = ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE") or None)

fam, out = sys.argv[1], sys.argv[2]
pesos = (sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else "400,700").split(",")
ital = "--italico" in sys.argv
axis = "ital,wght@" + ";".join([f"0,{p}" for p in pesos] + ([f"1,{p}" for p in pesos] if ital else []))
url = f"https://fonts.googleapis.com/css2?family={fam.replace(' ', '+')}:{axis}&display=swap"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"})
css = urllib.request.urlopen(req, context=CTX).read().decode()
os.makedirs(out, exist_ok=True)
slug = re.sub(r"[^a-z0-9]+", "-", fam.lower()).strip("-")
for sub, bloco in re.findall(r"/\* (\S+) \*/\s*@font-face \{(.*?)\}", css, re.S):
    if sub != "latin": continue
    st = re.search(r"font-style: (\w+)", bloco).group(1); w = re.search(r"font-weight: (\d+)", bloco).group(1)
    u = re.search(r"url\((.*?)\)", bloco).group(1)
    dst = os.path.join(out, f"{slug}-{w}-{st}.woff2")
    open(dst, "wb").write(urllib.request.urlopen(u, context=CTX).read()); print(dst)
