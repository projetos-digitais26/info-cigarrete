"""Produz os takes de vídeo da VSL no fal.ai: referências de personagem → quadro-chave de cada plano → vídeo 9:16.

Uso (na pasta cinematografia/):
  python3 produzir.py estimar  [--so A01,A02 | --ate C12]           custo previsto, sem gastar nada
  python3 produzir.py checar                                         confere no fal.ai o schema de cada modelo (sem gastar)
  python3 produzir.py refs     [--so MARCIA_44,SOFIA_9]              gera refs/<REF>.png (folha de personagem/objeto)
  python3 produzir.py planos   [--so ...|--ate CENA] --limite-usd 30 gera kf/<id>.png e clips/<id>.mp4; para ao bater o teto
  python3 produzir.py refazer  A04-2 [--prompt "..."]                apaga e regera um plano (1 vez)

- Lê a chave de FAL_KEY (ambiente). Nunca grave a chave em arquivo.
- Já feito = arquivo existe → não gera de novo (retomar é só rodar outra vez).
- Gasto registrado em custos.json (estimado pelo preço da tabela PRECO; conferir no painel do fal.ai).
"""
import argparse, base64, json, os, sys, time, urllib.request
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "..", "..", "..", "ferramentas"))
import fal  # noqa: E402  (req, collect_urls, CTX)

# endpoints (conferir com `checar` antes de gastar; o fal muda nomes e parâmetros com frequência)
MODELO = {
    "ref":      "fal-ai/nano-banana",                          # texto → imagem
    "keyframe": "fal-ai/nano-banana/edit",                     # imagem(s) de referência + texto → imagem
    "hero":     "fal-ai/veo3.1/fast/image-to-video",           # rostos e emoção
    "acao":     "fal-ai/kling-video/v3/pro/image-to-video",    # personagens em movimento, mãos, objetos
    "broll":    "fal-ai/kling-video/v2.5-turbo/pro/image-to-video",
    "fx":       "fal-ai/veo3.1/fast/image-to-video",           # serpente de fumaça, animação 3D
}
# US$ por chamada (imagens) ou por segundo gerado (vídeo) — out/2026, sem áudio
PRECO = {"ref": .04, "keyframe": .04, "hero": .10, "acao": .112, "broll": .07, "fx": .10}
PROMPT_REF = ("character reference sheet, single person, front view and three-quarter view side by side, "
              "neutral grey studio background, soft light, photorealistic, 35mm, no text")
PROMPT_OBJ = "product reference photo, single object, neutral background, soft light, photorealistic, no text, no logos"

ap = argparse.ArgumentParser()
ap.add_argument("acao", choices=["estimar", "checar", "refs", "planos", "refazer"])
ap.add_argument("alvo", nargs="?")
ap.add_argument("--so", default=""); ap.add_argument("--ate", default="")
ap.add_argument("--limite-usd", type=float, default=0); ap.add_argument("--prompt", default="")
a = ap.parse_args()

planos = json.load(open(os.path.join(AQUI, "planos.json")))
cenas = {c["cena"]: c for c in json.load(open(os.path.join(AQUI, "cenas-tempo.json")))}
refs = json.load(open(os.path.join(AQUI, "refs.json")))
ordem = [c for c in cenas]
custos_p = os.path.join(AQUI, "custos.json")
custos = json.load(open(custos_p)) if os.path.exists(custos_p) else {"total": 0, "itens": []}
for d in ("refs", "kf", "clips"):
    os.makedirs(os.path.join(AQUI, d), exist_ok=True)


def selecionar():
    so = set(filter(None, a.so.split(",")))
    lim = ordem.index(a.ate) if a.ate else None
    for p in planos:
        if so and p["id"] not in so and p["cena"] not in so:
            continue
        if lim is not None and ordem.index(p["cena"]) > lim:
            continue
        yield p


def dur_plano(p):
    return p["peso"] * cenas[p["cena"]]["dur"]


def seg_gerados(p):
    """segundos que o modelo vai gerar (e cobrar) para cobrir o plano"""
    d = dur_plano(p)
    if "veo3.1" in MODELO[p["tipo"]]:
        return 4 if d <= 4 else 6 if d <= 6 else 8
    return 5 if d <= 5 else 10


def gera_video(p):
    return p["tipo"] in MODELO and p["tipo"] not in ("ref", "keyframe") and p.get("keyframe_prompt") and "reusa" not in (p.get("nota") or "").lower()


def custo_plano(p):
    c = 0
    if p.get("keyframe_prompt"):
        c += PRECO["keyframe"]
    if gera_video(p):
        c += PRECO[p["tipo"]] * seg_gerados(p)
    return c


def data_uri(caminho):
    mime = "image/png" if caminho.endswith(".png") else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(open(caminho, "rb").read()).decode()


def chamar(modelo, entrada, destino, tipo_custo, qtd=1):
    """envia, espera e baixa o 1º arquivo para `destino`; registra o custo"""
    gasto = PRECO[tipo_custo] * qtd
    if a.limite_usd and custos["total"] + gasto > a.limite_usd:
        sys.exit(f"Teto de US$ {a.limite_usd:.2f} atingido (gasto até agora US$ {custos['total']:.2f}). Nada mais foi enviado.")
    code, sub = fal.req("POST", f"{fal.BASE}/{modelo}", entrada)
    if code >= 300:
        print(f"  erro ao enviar {destino}: {code} {str(sub)[:300]}"); return False
    while True:
        code, st = fal.req("GET", sub["status_url"] + "?logs=0")
        if st.get("status") == "COMPLETED":
            break
        if code >= 400 or st.get("status") in ("FAILED", "ERROR"):
            print(f"  falhou {destino}: {str(st)[:300]}"); return False
        time.sleep(4)
    code, res = fal.req("GET", sub["response_url"])
    urls = fal.collect_urls(res, []) if code < 300 else []
    if not urls:
        print(f"  sem arquivo em {destino}: {str(res)[:300]}"); return False
    with urllib.request.urlopen(urls[0], context=fal.CTX, timeout=300) as r, open(destino, "wb") as f:
        f.write(r.read())
    custos["total"] = round(custos["total"] + gasto, 3)
    custos["itens"].append({"arquivo": os.path.relpath(destino, AQUI), "modelo": modelo, "usd": round(gasto, 3), "quando": time.strftime("%Y-%m-%d %H:%M")})
    json.dump(custos, open(custos_p, "w"), indent=1, ensure_ascii=False)
    print(f"  ok {os.path.relpath(destino, AQUI)}  (+US$ {gasto:.2f} · total US$ {custos['total']:.2f})", flush=True)
    return True


def fazer_ref(nome):
    dst = os.path.join(AQUI, "refs", nome + ".png")
    if os.path.exists(dst):
        return
    r = refs[nome]
    base = PROMPT_OBJ if r["tipo"] == "objeto" else PROMPT_REF if r["tipo"] == "pessoa" else "establishing shot, photorealistic, 35mm, no text"
    chamar(MODELO["ref"], {"prompt": f"{r['descricao']}. {base}", "aspect_ratio": "9:16", "num_images": 1}, dst, "ref")


def fazer_plano(p, prompt_extra=""):
    kf = os.path.join(AQUI, "kf", p["id"] + ".png")
    clip = os.path.join(AQUI, "clips", p["id"] + ".mp4")
    if not p.get("keyframe_prompt"):
        return
    if not os.path.exists(kf):
        imgs = [data_uri(os.path.join(AQUI, "refs", r + ".png")) for r in p.get("refs", [])
                if os.path.exists(os.path.join(AQUI, "refs", r + ".png"))][:4]
        prompt = (p["keyframe_prompt"] + " " + prompt_extra).strip() + " Vertical 9:16 frame."
        if imgs:
            ok = chamar(MODELO["keyframe"], {"prompt": prompt, "image_urls": imgs, "aspect_ratio": "9:16", "num_images": 1}, kf, "keyframe")
        else:
            ok = chamar(MODELO["ref"], {"prompt": prompt, "aspect_ratio": "9:16", "num_images": 1}, kf, "keyframe")
        if not ok:
            return
    if gera_video(p) and not os.path.exists(clip):
        entrada = {"prompt": p.get("motion_prompt") or "subtle natural motion, slow push-in", "image_url": data_uri(kf),
                   "duration": str(seg_gerados(p)),
                   "aspect_ratio": "9:16", "generate_audio": False, "negative_prompt": "text, subtitles, logo, watermark, blur, distortion, extra fingers"}
        if "veo3.1" in MODELO[p["tipo"]]:
            entrada["duration"] = f"{seg_gerados(p)}s"
            entrada["resolution"] = "1080p"
        chamar(MODELO[p["tipo"]], entrada, clip, p["tipo"], seg_gerados(p))


if a.acao == "estimar":
    sel = list(selecionar())
    por_tipo = {}
    for p in sel:
        por_tipo.setdefault(p["tipo"], [0, 0.0]); por_tipo[p["tipo"]][0] += 1; por_tipo[p["tipo"]][1] += custo_plano(p)
    n_refs = len(refs) if not a.so and not a.ate else len({r for p in sel for r in p.get("refs", [])})
    print(f"{len(sel)} planos · {sum(1 for p in sel if gera_video(p))} vídeos a gerar")
    for t, (n, c) in sorted(por_tipo.items()):
        print(f"  {t:8s} {n:4d} planos  US$ {c:7.2f}")
    total = sum(custo_plano(p) for p in sel) + n_refs * PRECO["ref"]
    print(f"  refs     {n_refs:4d}         US$ {n_refs * PRECO['ref']:7.2f}")
    print(f"TOTAL previsto (1 tentativa por plano): US$ {total:.2f} · com 25% de refações: US$ {total * 1.25:.2f}")
elif a.acao == "checar":
    for k, m in MODELO.items():
        code, body = fal.req("GET", f"https://fal.ai/api/openapi/queue/openapi.json?endpoint_id={m}")
        print(k, m, "OK" if code < 300 else f"ERRO {code}")
        if code < 300:
            sch = body.get("components", {}).get("schemas", {})
            ent = next((v for n, v in sch.items() if n.endswith("Input")), {})
            print("   entradas:", ", ".join(f"{n}{'*' if n in ent.get('required', []) else ''}" for n in ent.get("properties", {})))
elif a.acao == "refs":
    fal.key()
    nomes = [n for n in refs if not a.so or n in a.so.split(",")]
    for n in nomes:
        print("ref", n); fazer_ref(n)
elif a.acao == "planos":
    fal.key()
    sel = list(selecionar())
    falta = sorted({r for p in sel for r in p.get("refs", []) if r in refs and not os.path.exists(os.path.join(AQUI, "refs", r + ".png"))})
    if falta:
        sys.exit("Gere antes as referências: python3 produzir.py refs --so " + ",".join(falta))
    for p in sel:
        print(p["id"], p["tipo"]); fazer_plano(p)
elif a.acao == "refazer":
    fal.key()
    p = next(p for p in planos if p["id"] == a.alvo)
    for d, ext in (("kf", ".png"), ("clips", ".mp4")):
        f = os.path.join(AQUI, d, p["id"] + ext)
        if os.path.exists(f):
            os.replace(f, f + ".anterior")
    fazer_plano(p, a.prompt)
