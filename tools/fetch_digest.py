#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

BASE_DIR = Path(__file__).resolve().parents[1]
CONTENT_DIR = BASE_DIR / "content"
FEEDS_FILE = CONTENT_DIR / "feeds" / "feeds.txt"
DIGESTS_DIR = CONTENT_DIR / "digests"
INDEX_PATH = DIGESTS_DIR / "index.json"

MAX_BYTES = 1_000_000
TIMEOUT = 10
ITEMS_PER_FEED = 3


def _read_feeds() -> list[str]:
    if not FEEDS_FILE.exists():
        return []
    feeds = []
    for line in FEEDS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        feeds.append(line)
    return feeds


def _validate_data(data: bytes) -> bytes:
    if len(data) > MAX_BYTES:
        raise ValueError("Feed too large")
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        raise ValueError("Unsafe XML detected")
    return data


def _fetch(url: str) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme in {"", "file"}:
        if parsed.scheme == "file":
            path = Path(unquote(parsed.path))
        else:
            path = Path(url)
            if not path.is_absolute():
                path = (BASE_DIR / path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Feed not found: {path}")
        return _validate_data(path.read_bytes())
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ALI Digest Bot/1.0"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        data = resp.read(MAX_BYTES + 1)
    return _validate_data(data)


def _text(elem: ET.Element | None) -> str:
    if elem is None or elem.text is None:
        return ""
    return elem.text.strip()


def _find_first(elem: ET.Element, tags: list[str]) -> str:
    for tag in tags:
        child = elem.find(tag)
        if child is not None and child.text:
            return child.text.strip()
    return ""


def _parse_link(elem: ET.Element) -> str:
    link = elem.find("link")
    if link is not None:
        href = link.attrib.get("href")
        if href:
            return href.strip()
        if link.text:
            return link.text.strip()
    for link in elem.findall("{*}link"):
        rel = link.attrib.get("rel", "alternate")
        if rel == "alternate" and link.attrib.get("href"):
            return link.attrib["href"].strip()
    return ""


def _parse_feed(data: bytes) -> list[dict[str, str]]:
    root = ET.fromstring(data)
    tag = root.tag.lower()
    items: list[dict[str, str]] = []
    if tag.endswith("rss") or "rss" in tag:
        channel = root.find("channel")
        if channel is None:
            channel = root.find("{*}channel")
        if channel is None:
            return []
        for item in channel.findall("item")[:ITEMS_PER_FEED]:
            title = _find_first(item, ["title", "{*}title"])
            link = _find_first(item, ["link", "{*}link"]) or _parse_link(item)
            date = _find_first(item, ["pubDate", "{*}pubDate", "date", "{*}date"])
            items.append({"title": title, "link": link, "date": date})
    elif tag.endswith("feed") or "feed" in tag:
        for entry in root.findall("{*}entry")[:ITEMS_PER_FEED]:
            title = _find_first(entry, ["{*}title"])
            link = _parse_link(entry)
            date = _find_first(entry, ["{*}updated", "{*}published"])
            items.append({"title": title, "link": link, "date": date})
    return items


def _slug_date(raw: str) -> str:
    match = re.search(r"\d{4}-\d{2}-\d{2}", raw)
    if match:
        return match.group(0)
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _build_digest(
    items: list[dict[str, str]],
    issue_number: int,
    date_override: str | None = None,
) -> tuple[str, str, str]:
    today = date_override or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    title = f"ALI Digest Issue #{issue_number}"
    lines = [f"# {title}", "", f"*{today}*", "", "## Highlights", ""]
    for item in items:
        label = item.get("title") or "Untitled"
        link = item.get("link") or ""
        if link:
            host = urlparse(link).netloc
            source = f" — {host}" if host else ""
            lines.append(f"- [{label}]({link}){source}")
        else:
            lines.append(f"- {label}")
    return today, title, "\n".join(lines) + "\n"


def _load_index() -> dict[str, list[dict[str, str]]]:
    if INDEX_PATH.exists():
        raw = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and isinstance(raw.get("digests"), list):
            return raw
    return {"digests": []}


def main() -> None:
    feeds = _read_feeds()
    if not feeds:
        raise SystemExit("No feeds found in content/feeds/feeds.txt")
    collected: list[dict[str, str]] = []
    for url in feeds:
        data = _fetch(url)
        collected.extend(_parse_feed(data))
    index = _load_index()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if any(entry.get("date") == today for entry in index.get("digests", [])):
        print(f"Digest already exists for {today}. Skipping.")
        return
    issue_number = len(index["digests"]) + 1
    date, title, markdown = _build_digest(collected, issue_number, today)
    DIGESTS_DIR.mkdir(parents=True, exist_ok=True)
    digest_path = DIGESTS_DIR / f"{date}.md"
    digest_path.write_text(markdown, encoding="utf-8")

    index_entries = [entry for entry in index["digests"] if entry.get("date") != date]
    index_entries.insert(
        0,
        {
            "date": date,
            "title": title,
            "slug": date,
            "source_md": f"digests/{date}.md",
        },
    )
    index["digests"] = index_entries
    INDEX_PATH.write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"Wrote digest {digest_path}")


if __name__ == "__main__":
    main()
