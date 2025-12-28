#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SITE_DIR = BASE_DIR / "site"

FORBIDDEN_TARGETS = [
    "zid.univie.ac.at/helpdesk",
]

HREF_PATTERN = re.compile(r'(?:href|src)=["\']([^"\']+)["\']', re.IGNORECASE)


def _matches_forbidden(url: str) -> str | None:
    lowered = url.lower()
    for forbidden in FORBIDDEN_TARGETS:
        if forbidden.lower() in lowered:
            return forbidden
    return None


def main() -> int:
    if not SITE_DIR.exists():
        print("[ALI] site/ directory not found. Run python3 tools/build.py first.")
        return 1

    hits: list[tuple[Path, str, str]] = []
    for path in SITE_DIR.rglob("*.html"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for url in HREF_PATTERN.findall(text):
            match = _matches_forbidden(url.strip())
            if match:
                hits.append((path, url.strip(), match))

    if hits:
        print("[ALI] Forbidden external targets found:")
        for path, url, match in hits:
            rel = path.relative_to(BASE_DIR)
            print(f"[ALI] {rel}: {url} (matches {match})")
        return 1

    print("[ALI] Link verification passed. No forbidden external targets found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
