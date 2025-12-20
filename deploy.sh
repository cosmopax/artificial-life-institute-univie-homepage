#!/usr/bin/env bash
set -euo pipefail

WEBROOT="/Users/cosmopax/WebspaceMount/artificiat27/html"
SITE_DIR="$(cd "$(dirname "$0")" && pwd)/site"

if [[ "$WEBROOT" != "/Users/cosmopax/WebspaceMount/artificiat27/html" ]]; then
  echo "Refusing to deploy: unexpected webroot path." >&2
  exit 1
fi

if [[ ! -d "$WEBROOT" ]]; then
  echo "Webroot does not exist: $WEBROOT" >&2
  exit 1
fi

if [[ ! -d "$SITE_DIR" ]]; then
  echo "Missing site output. Run ./build.py first." >&2
  exit 1
fi

timestamp=$(date +%Y%m%d-%H%M%S)
quarantine="$WEBROOT/__quarantine__/$timestamp"

mkdir -p "$quarantine"

shopt -s dotglob nullglob
for item in "$WEBROOT"/*; do
  base=$(basename "$item")
  if [[ "$base" == "__quarantine__" ]]; then
    continue
  fi
  mv "$item" "$quarantine/"
done
shopt -u dotglob nullglob

rsync -av "$SITE_DIR/" "$WEBROOT/"

echo "Deploy check (HTTP status):"
curl -s -o /dev/null -w "%{http_code}\n" https://artificial-life-institute.univie.ac.at

echo "First 20 lines of HTML:"
curl -s https://artificial-life-institute.univie.ac.at | sed -n '1,20p'
