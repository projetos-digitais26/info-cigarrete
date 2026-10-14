"""Ajuste de rede comum às ferramentas: usa o certificado do proxy do ambiente quando ele existe."""
import os

CA = os.environ.get("CA_BUNDLE", "/root/.ccr/ca-bundle.crt")
if os.path.exists(CA):
    os.environ.setdefault("SSL_CERT_FILE", CA)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", CA)
    try:
        import certifi
        certifi.where = lambda: CA
    except ImportError:
        pass
