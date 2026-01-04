#!/usr/bin/env bash
set -euo pipefail

# 1. Load Configuration
SITE_DIR="$(cd "$(dirname "$0")" && pwd)/site"

if [[ -f "deploy.env" ]]; then
  source deploy.env
else
  echo "Error: deploy.env file not found." >&2
  echo "Please create deploy.env with WEBROOT='/path/to/html' and SITE_URL='https://example.com'" >&2
  exit 1
fi

# 2. Safety Checks
if [[ -z "${WEBROOT:-}" ]]; then
  echo "Error: WEBROOT is not set in deploy.env." >&2
  exit 1
fi

if [[ ! -d "$WEBROOT" ]]; then
  echo "Error: Webroot directory does not exist: $WEBROOT" >&2
  echo "Is the remote volume mounted?" >&2
  exit 1
fi

if [[ ! -d "$SITE_DIR" ]]; then
  echo "Error: Build output missing. Run 'python3 tools/build.py' first." >&2
  exit 1
fi

# 3. Execution
echo "Deploying to: $WEBROOT"
timestamp=$(date +%Y%m%d-%H%M%S)
quarantine="$WEBROOT/__quarantine__/$timestamp"

echo "  - Quarantining old files..."
mkdir -p "$quarantine"

# Move everything except __quarantine__ to the new quarantine folder
shopt -s dotglob nullglob
for item in "$WEBROOT"/*; do
  base=$(basename "$item")
  if [[ "$base" == "__quarantine__" ]]; then
    continue
  fi
  mv "$item" "$quarantine/"
done
shopt -u dotglob nullglob

echo "  - Copying new site..."
if command -v rsync >/dev/null 2>&1; then
  rsync -av "$SITE_DIR/" "$WEBROOT/"
else
  cp -a "$SITE_DIR/." "$WEBROOT/"
fi

# 4. Post-Deploy Configuration
echo "  - Securing data directory..."
mkdir -p "$WEBROOT/data"
cat > "$WEBROOT/data/.htaccess" <<'EOF'
Require all denied
<FilesMatch "\.(csv|json)$">
  Require all denied
</FilesMatch>
EOF

# 5. Verification
if [[ -n "${SITE_URL:-}" ]]; then
    echo "  - Verifying deployment..."
    status=$(curl -s -o /dev/null -w "%{http_code}" "$SITE_URL" || echo "FAIL")
    echo "    HTTP Status: $status"
    if [[ "$status" == "200" ]]; then
        echo "    SUCCESS."
    else
        echo "    WARNING: Site might be down."
    fi
fi

echo "Deployment Complete."
