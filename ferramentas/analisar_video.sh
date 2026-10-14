#!/usr/bin/env bash
# "Assiste" um vídeo: gera o que o Claude precisa para entender visual, cortes, áudio e fala.
# Uso: ferramentas/analisar_video.sh <video> <pasta_saida> ["dica de vocabulário para a transcrição"]
#   <pasta_saida>/folha.jpg      1 quadro por segundo, numerado, com linhas a cada 10% da altura
#                                (abra com a ferramenta de leitura de imagem para ver as cenas e onde ficam os rostos)
#   <pasta_saida>/cortes.txt     instantes de corte de cena
#   <pasta_saida>/nivel.txt      volume do áudio por segundo
#   <pasta_saida>/audio16k.wav   áudio para transcrição
#   <pasta_saida>/palavras.json  fala palavra a palavra (Whisper), se houver fala
set -euo pipefail
V="$1"; O="$2"; DICA="${3:-}"
DIR=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$O"
echo "== arquivo"; ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,r_frame_rate,color_transfer:format=duration -of compact "$V"
FONT=$(fc-match -f '%{file}' DejaVuSans 2>/dev/null || echo /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf)
G=$(for p in 1 2 3 4 5 6 7 8 9; do printf "drawbox=y=ih*0.$p:w=iw:h=1:color=yellow@0.6,"; done)
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$V"); N=$(python3 -c "import math;print(max(1,math.ceil($DUR)))")
COLS=$(( N < 11 ? N : 11 )); ROWS=$(( (N + COLS - 1) / COLS ))
ffmpeg -loglevel error -y -i "$V" -vf "fps=1,scale=180:-2,${G}drawtext=fontfile=$FONT:text='%{n}':x=5:y=5:fontsize=28:fontcolor=yellow:box=1:boxcolor=black,tile=${COLS}x${ROWS}" -frames:v 1 "$O/folha.jpg"
echo "== folha de contato: $O/folha.jpg (números = segundo; linhas amarelas a cada 10% da altura)"
ffmpeg -i "$V" -vf "select='gt(scene,0.3)',showinfo" -an -f null - 2>&1 | grep -oE "pts_time:[0-9.]+" | sed 's/pts_time://' > "$O/cortes.txt" || true
echo "== cortes de cena (s): $(tr '\n' ' ' < "$O/cortes.txt")"
if ffprobe -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 "$V" | grep -q audio; then
  ffmpeg -loglevel error -y -i "$V" -vn -ac 1 -ar 16000 "$O/audio16k.wav"
  python3 - "$O/audio16k.wav" > "$O/nivel.txt" <<'EOF'
import subprocess, sys, numpy as np
x = np.frombuffer(subprocess.run(["ffmpeg","-loglevel","error","-i",sys.argv[1],"-f","f32le","-"],capture_output=True).stdout, np.float32)
print(" ".join(f"{i}:{20*np.log10(np.sqrt(np.mean(x[i*16000:(i+1)*16000]**2))+1e-9):.0f}" for i in range(len(x)//16000)))
EOF
  echo "== volume por segundo (dBFS): $(cat "$O/nivel.txt")"
  ffmpeg -hide_banner -i "$V" -af ebur128=peak=true -f null - 2>&1 | grep -E " I:|Peak:" | tail -2
  echo "== transcrição"
  python3 "$DIR/transcrever.py" "$O/audio16k.wav" "$O/palavras.json" --prompt "$DICA"
else
  echo "== sem trilha de áudio"
fi
