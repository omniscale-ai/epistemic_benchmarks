#!/usr/bin/env bash
# Build slides.pdf from slides_en.md with the Constructor brand theme (constructor.css).
# marp-cli renders HTML; headless Chrome (bundled with Quarto) prints it to PDF.
set -euo pipefail
cd "$(dirname "$0")"
SRC=${1:-slides_en.md}
OUT=${2:-slides.pdf}
CH=${CHROME:-$HOME/.local/share/quarto/chrome-headless-shell/chrome-headless-shell-linux64/chrome-headless-shell}
TMP=$(mktemp -d)
# mark the first slide as the title slide (no change to the source file)
awk 'BEGIN{n=0} {print} /^---$/ {n++; if(n==2){print "\n<!-- _class: title -->"}}' "$SRC" > "$TMP/deck.md"
cp ./*.png "$TMP"/ 2>/dev/null || true
npx -y @marp-team/marp-cli@4.5.1 "$TMP/deck.md" --theme constructor.css --html -o "$TMP/deck.html"
"$CH" --no-sandbox --disable-gpu --no-pdf-header-footer --print-to-pdf="$OUT" "file://$TMP/deck.html" 2>/dev/null
rm -rf "$TMP"
echo "wrote $OUT"
