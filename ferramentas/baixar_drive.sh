#!/usr/bin/env bash
# Baixa um arquivo do Google Drive compartilhado como "qualquer pessoa com o link".
# Uso: ferramentas/baixar_drive.sh <link_ou_id> <arquivo_saida>
set -euo pipefail
ID=$(echo "$1" | sed -E 's#.*/d/([^/?]+).*#\1#; s#.*[?&]id=([^&]+).*#\1#')
OUT="$2"; mkdir -p "$(dirname "$OUT")"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
curl -sL -c "$TMP/ck" "https://drive.google.com/uc?export=download&id=$ID" -o "$TMP/t1"
if grep -qa 'name="uuid"' "$TMP/t1"; then
  # arquivo grande: o Drive pede confirmação
  U=$(grep -aoE 'name="uuid" value="[^"]+"' "$TMP/t1" | sed 's/.*value="//;s/"//')
  curl -sL -b "$TMP/ck" "https://drive.usercontent.google.com/download?id=$ID&export=download&confirm=t&uuid=$U" -o "$OUT"
else
  mv "$TMP/t1" "$OUT"
fi
if head -c 200 "$OUT" | grep -qi '<html'; then
  echo "ERRO: o Drive devolveu uma página, não o arquivo. Confira se o link está como 'qualquer pessoa com o link'." >&2; exit 1
fi
ls -la "$OUT"
ffprobe -v error -show_entries stream=codec_type,codec_name,width,height,r_frame_rate,color_transfer:format=duration -of compact "$OUT" || true
