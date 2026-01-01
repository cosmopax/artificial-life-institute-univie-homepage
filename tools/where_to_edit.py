#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
CONTENT_DIR = BASE_DIR / "content"
BLOCKS_DIR = CONTENT_DIR / "blocks"
CONTROL_CSV = CONTENT_DIR / "control.csv"
PREFIX = "[ALI]"


def _normalize_slug(raw_slug: str) -> str:
    slug = (raw_slug or "").strip()
    if slug in {"", "/", "index", "home"}:
        return ""
    return slug.strip("/")


def _display_slug(slug: str) -> str:
    if slug == "":
        return "/"
    return f"/{slug}/"


def _resolve_source_path(source_md: str) -> str:
    if not source_md:
        return "(none)"
    source = Path(source_md)
    if source.is_absolute():
        resolved = source
    elif "/" in source_md or "\\" in source_md:
        resolved = CONTENT_DIR / source
    else:
        resolved = BLOCKS_DIR / source
    try:
        return resolved.relative_to(BASE_DIR).as_posix()
    except ValueError:
        return resolved.as_posix()


def load_control() -> list[dict[str, object]]:
    pages: dict[str, dict[str, object]] = {}
    with CONTROL_CSV.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            data = {key: (value or "").strip() for key, value in row.items()}
            status = (data.get("status") or "").lower()
            if status in {"draft", "hidden", "archived", "inactive"}:
                continue
            slug = _normalize_slug(data.get("page_slug", ""))
            order = int(data.get("order") or 0)
            page = pages.setdefault(
                slug,
                {"title": slug.title() or "Home", "sections": [], "order": 0},
            )
            kind = (data.get("kind") or "section").lower()
            if kind in {"page", "meta"}:
                if data.get("title"):
                    page["title"] = data["title"]
                page["order"] = order
                continue
            page["sections"].append(
                {
                    "order": order,
                    "section_id": data.get("section") or data.get("id") or "",
                    "title": data.get("title") or "",
                    "source_md": data.get("source_md") or "",
                }
            )
    ordered_pages = sorted(pages.items(), key=lambda item: item[1].get("order", 0))
    results: list[dict[str, object]] = []
    for slug, page in ordered_pages:
        sections = sorted(page["sections"], key=lambda item: item["order"])
        results.append({"slug": slug, "title": page["title"], "sections": sections})
    return results


def format_dashboard(pages: list[dict[str, object]]) -> str:
    lines: list[str] = [f"{PREFIX} Dashboard"]
    for page in pages:
        slug = _display_slug(page["slug"])  # type: ignore[index]
        title = page["title"]  # type: ignore[index]
        lines.append(f"{PREFIX} {slug} ({title})")
        for index, section in enumerate(page["sections"], start=1):  # type: ignore[index]
            label = section.get("section_id") or section.get("title") or "section"
            source = _resolve_source_path(section.get("source_md", ""))
            lines.append(f"{PREFIX} {index}. {label} -> {source}")
    return "\n".join(lines)


def main() -> int:
    pages = load_control()
    print(format_dashboard(pages))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
