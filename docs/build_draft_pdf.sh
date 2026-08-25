#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT_DIR/docs/draft.md"
TMP_MD="${TMPDIR:-/tmp}/draft_formatted.md"

if [[ ! -f "$ROOT_DIR/docs/figures/fragility_deciles.png" ]]; then
  echo "Missing generated paper figure. Run: python scripts/08_paper_artifacts.py" >&2
  exit 1
fi

{
  printf '%s\n' '---'
  printf 'title: "%s"\n' "$(sed -n '1s/^# //p' "$SRC")"
  printf '%s\n' 'author:'
  printf '  - "%s | %s"\n' "$(sed -n '3s/^\*\*\(.*\)\*\*  *$/\1/p' "$SRC")" "$(sed -n '4p' "$SRC")"
  printf 'date: "%s"\n' "$(sed -n '5p' "$SRC")"
  printf '%s\n' 'abstract: |'
  awk '
    /^## Abstract$/ {in_abs=1; next}
    in_abs && /^---$/ {in_abs=0; next}
    in_abs {
      gsub(/\*\*\*/, "\\*\\*\\*")
      print "  " $0
    }
  ' "$SRC"
  printf '%s\n\n' '---'
  awk 'found {print} /^## 1\. Introduction$/ {found=1; print}' "$SRC" | sed 's/\*\*\*/\\*\\*\\*/g'
} > "$TMP_MD"

pandoc "$TMP_MD" \
  -o "$ROOT_DIR/docs/draft.pdf" \
  --template "$ROOT_DIR/docs/arxiv_like.latex" \
  --pdf-engine=xelatex \
  --resource-path "$ROOT_DIR" \
  --shift-heading-level-by=-1

echo "OK -> $ROOT_DIR/docs/draft.pdf"
