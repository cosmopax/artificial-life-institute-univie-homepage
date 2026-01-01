#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SITE="$ROOT/site"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8099}"

if ! command -v php >/dev/null 2>&1; then
  echo "php is required to run the local subscribe.php test." >&2
  exit 1
fi

if [[ ! -f "$SITE/subscribe.php" ]]; then
  echo "subscribe.php not found. Building site output..." >&2
  python3 "$ROOT/tools/build.py"
fi

server_log="$(mktemp)"
response_file="$(mktemp)"
php -S "$HOST:$PORT" -t "$SITE" >"$server_log" 2>&1 &
SERVER_PID=$!

cleanup() {
  kill "$SERVER_PID" >/dev/null 2>&1 || true
  rm -f "$server_log" "$response_file"
}
trap cleanup EXIT

sleep 0.4

email="test+$(date +%s)@example.org"
status=$(curl -s -o "$response_file" -w "%{http_code}" \
  -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "email=$email&company=" \
  "http://$HOST:$PORT/subscribe.php")

cat "$response_file"
echo
echo "HTTP $status"
