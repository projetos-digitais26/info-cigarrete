#!/usr/bin/env bash
# Instala tudo o que o kit de edição de vídeo usa e confere o ambiente. Pode rodar quantas vezes quiser.
# Uso: bash ferramentas/setup.sh            (dentro do repositório)
# O mesmo conteúdo das etapas 1–3 serve como "Setup script" do ambiente na nuvem do Claude Code.
set -uo pipefail
RAIZ=$(cd "$(dirname "$0")/.." && pwd)
CA=${CA_BUNDLE:-/root/.ccr/ca-bundle.crt}
[ -f "$CA" ] && export PIP_CERT="$CA" NODE_EXTRA_CA_CERTS="$CA" SSL_CERT_FILE="$CA" REQUESTS_CA_BUNDLE="$CA"
SUDO=""; [ "$(id -u)" != 0 ] && command -v sudo >/dev/null && SUDO="sudo"

echo "== 1/5 ffmpeg"
command -v ffmpeg >/dev/null || { $SUDO apt-get update -qq && $SUDO apt-get install -y -qq ffmpeg fonts-dejavu-core; }

echo "== 2/5 Python: faster-whisper, numpy, edge-tts"
python3 -c "import faster_whisper, numpy, edge_tts" 2>/dev/null || \
  pip install -q faster-whisper numpy edge-tts 2>/dev/null || pip install -q --break-system-packages faster-whisper numpy edge-tts

echo "== 3/5 Node: Playwright (Chromium)"
if ! node -e "require('playwright')" 2>/dev/null && ! node -e "require(require('child_process').execSync('npm root -g').toString().trim()+'/playwright')" 2>/dev/null; then
  npm install -g -s playwright@1.56.1
fi
if ! ls -d "${PLAYWRIGHT_BROWSERS_PATH:-/opt/pw-browsers}"/chromium-* >/dev/null 2>&1; then
  npx -y playwright@1.56.1 install --with-deps chromium || echo "AVISO: não consegui baixar o Chromium (rede?)"
fi

echo "== 4/5 fontes dos modelos (Google Fonts)"
if [ ! -f "$RAIZ/modelos/fonts/montserrat-800-normal.woff2" ]; then
  python3 "$RAIZ/ferramentas/baixar_fonte.py" "Montserrat" "$RAIZ/modelos/fonts" 600,700,800 >/dev/null && \
  python3 "$RAIZ/ferramentas/baixar_fonte.py" "Playfair Display" "$RAIZ/modelos/fonts" 600,700 --italico >/dev/null || \
  echo "AVISO: fontes não baixadas (libere fonts.googleapis.com e fonts.gstatic.com)"
fi

echo "== 5/5 modelo de transcrição (Whisper medium, ~1,5 GB, só na primeira vez)"
python3 - <<'EOF' || echo "AVISO: modelo do Whisper não baixado (libere huggingface.co); será baixado no primeiro uso"
import os, sys
sys.path.insert(0, os.path.join(os.environ.get("RAIZ", "."), "ferramentas"))
from faster_whisper import WhisperModel
WhisperModel("medium", device="cpu", compute_type="int8"); print("whisper medium ok")
EOF

echo; echo "== conferência"
ok(){ printf "  %-28s %s\n" "$1" "$2"; }
command -v ffmpeg >/dev/null && ok ffmpeg "ok" || ok ffmpeg "FALTANDO"
python3 -c "import faster_whisper" 2>/dev/null && ok faster-whisper ok || ok faster-whisper FALTANDO
python3 -c "import edge_tts" 2>/dev/null && ok edge-tts ok || ok edge-tts FALTANDO
(node -e "require('playwright')" 2>/dev/null || node -e "require(require('child_process').execSync('npm root -g').toString().trim()+'/playwright')" 2>/dev/null) && ok playwright ok || ok playwright FALTANDO
ls "$RAIZ/modelos/fonts/"*.woff2 >/dev/null 2>&1 && ok "fontes dos modelos" ok || ok "fontes dos modelos" FALTANDO
if [ -n "${FAL_KEY:-}" ]; then python3 "$RAIZ/ferramentas/fal.py" check >/dev/null 2>&1 && ok "FAL_KEY (fal.ai)" "ok" || ok "FAL_KEY (fal.ai)" "recusada ou sem rede"; else ok "FAL_KEY (fal.ai)" "não definida (só precisa para IA/Demucs)"; fi
curl -s -o /dev/null -w "%{http_code}" https://drive.google.com >/dev/null 2>&1 && ok "rede: Google Drive" ok || ok "rede: Google Drive" "BLOQUEADO"
