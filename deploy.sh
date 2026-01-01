#!/usr/bin/env bash
set -euo pipefail

WEBROOT="/Volumes/a0402554/artificiat27/html"
SITE_DIR="$(cd "$(dirname "$0")" && pwd)/site"

if [[ "$WEBROOT" != "/Volumes/a0402554/artificiat27/html" ]]; then
  echo "Refusing to deploy: unexpected webroot path." >&2
  exit 1
fi

if [[ ! -d "$WEBROOT" ]]; then
  echo "Webroot does not exist: $WEBROOT" >&2
  exit 1
fi

if [[ ! -d "$SITE_DIR" ]]; then
  echo "Missing site output. Run python3 tools/build.py first." >&2
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

if command -v rsync >/dev/null 2>&1; then
  rsync -av "$SITE_DIR/" "$WEBROOT/"
else
  cp -a "$SITE_DIR/." "$WEBROOT/"
fi

mkdir -p "$WEBROOT/data"
cat > "$WEBROOT/data/.htaccess" <<'EOF'
Require all denied
<FilesMatch "\.(csv|json)$">
  Require all denied
</FilesMatch>
EOF

if [[ ! -f "$WEBROOT/subscribe.php" ]]; then
  echo "Missing subscribe.php after deploy." >&2
  exit 1
fi

echo "Deploy check (HTTP status):"
curl -s -o /dev/null -w "%{http_code}\n" https://artificial-life-institute.univie.ac.at

echo "First 20 lines of HTML:"
curl -s https://artificial-life-institute.univie.ac.at | sed -n '1,20p'
