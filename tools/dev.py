#!/usr/bin/env python3
from __future__ import annotations

import argparse
import functools
import http.server
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SITE_DIR = BASE_DIR / "site"
PORT = 8787


def run_build() -> None:
    subprocess.run([sys.executable, str(BASE_DIR / "tools" / "build.py")], check=True)


def serve() -> None:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE_DIR))
    httpd = http.server.ThreadingHTTPServer(("localhost", PORT), handler)
    url = f"http://localhost:{PORT}/"
    print(f"[ALI] Serving {url} (site dir: {SITE_DIR})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("[ALI] Shutting down server.")
    finally:
        httpd.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and serve the ALI site locally.")
    parser.add_argument("--once", action="store_true", help="Build once and exit without serving.")
    args = parser.parse_args()

    run_build()
    url = f"http://localhost:{PORT}/"
    print(f"[ALI] Build complete. Preview at {url}")
    if args.once:
        return 0
    if not SITE_DIR.exists():
        print("[ALI] site/ directory missing after build.")
        return 1
    serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
