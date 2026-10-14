"""Cliente mínimo do fal.ai (fila assíncrona) para gerar imagens e vídeos.

Lê a chave de FAL_KEY (variável de ambiente; nunca escreva a chave em arquivo).

Uso:
  python3 ferramentas/fal.py check
      Valida a chave sem gastar créditos.
  python3 ferramentas/fal.py run <modelo> <entrada.json> <saida_dir>
      Envia o pedido, acompanha a fila e baixa os arquivos gerados.
      Ex.: python3 ferramentas/fal.py run fal-ai/kling-video/v2.1/master/text-to-video prompt.json out/
"""
import json, os, sys, time, urllib.request, urllib.error

CA = os.environ.get("CA_BUNDLE", "/root/.ccr/ca-bundle.crt")
if os.path.exists(CA):
    os.environ.setdefault("SSL_CERT_FILE", CA)
import ssl
CTX = ssl.create_default_context(cafile=CA if os.path.exists(CA) else None)
BASE = "https://queue.fal.run"


def key():
    k = os.environ.get("FAL_KEY")
    if not k:
        sys.exit("FAL_KEY não está definida nesta sessão. Cadastre no ambiente e abra uma sessão nova.")
    return k


def req(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method,
                               headers={"Authorization": f"Key {key()}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, context=CTX, timeout=120) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        txt = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(txt)
        except Exception:
            return e.code, {"raw": txt[:500]}


def check():
    # Consulta o status de um pedido inexistente: 401/403 = chave inválida; 404/422 = chave aceita.
    code, body = req("GET", f"{BASE}/fal-ai/flux/requests/00000000-0000-0000-0000-000000000000/status")
    if code in (401, 403):
        sys.exit(f"Chave recusada ({code}): {body}")
    print(f"Chave aceita pelo fal.ai (resposta {code} para pedido de teste inexistente).")


def collect_urls(obj, found):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "url" and isinstance(v, str) and v.startswith("http"):
                found.append(v)
            else:
                collect_urls(v, found)
    elif isinstance(obj, list):
        for v in obj:
            collect_urls(v, found)
    return found


def run(model, inp_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    payload = json.load(open(inp_path))
    code, sub = req("POST", f"{BASE}/{model}", payload)
    if code >= 300:
        sys.exit(f"Erro ao enviar ({code}): {sub}")
    status_url, response_url = sub["status_url"], sub["response_url"]
    print("pedido:", sub.get("request_id"))
    t0 = time.time()
    while True:
        code, st = req("GET", status_url + "?logs=0")
        s = st.get("status")
        print(f"  {int(time.time()-t0):4d}s  {s}  fila={st.get('queue_position','-')}", flush=True)
        if s == "COMPLETED":
            break
        if code >= 400 or s in ("FAILED", "ERROR"):
            sys.exit(f"Falhou: {st}")
        time.sleep(5)
    code, res = req("GET", response_url)
    if code >= 300:
        sys.exit(f"Erro no resultado ({code}): {res}")
    base = os.path.splitext(os.path.basename(inp_path))[0]
    json.dump(res, open(os.path.join(out_dir, base + ".result.json"), "w"), indent=2, ensure_ascii=False)
    for i, u in enumerate(collect_urls(res, [])):
        ext = os.path.splitext(u.split("?")[0])[1] or ".bin"
        dst = os.path.join(out_dir, f"{base}_{i}{ext}")
        with urllib.request.urlopen(u, context=CTX, timeout=300) as r, open(dst, "wb") as f:
            f.write(r.read())
        print("baixado:", dst)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "check":
        check()
    elif len(sys.argv) == 5 and sys.argv[1] == "run":
        run(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print(__doc__)
