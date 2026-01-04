#!/usr/bin/env python3
from __future__ import annotations

import csv
import html
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Iterable, Any

BASE_DIR = Path(__file__).resolve().parents[1]
CONTENT_DIR = BASE_DIR / "content"
SITE_DIR = BASE_DIR / "site"
ASSETS_DIR = SITE_DIR / "assets"
CSS_DIR = ASSETS_DIR / "css"
JS_DIR = ASSETS_DIR / "js"
IMG_DIR = ASSETS_DIR / "img"
BLOG_DIR = CONTENT_DIR / "blog"
MEDIA_DIR = CONTENT_DIR / "media"
BLOCKS_DIR = CONTENT_DIR / "blocks"
DIGESTS_DIR = CONTENT_DIR / "digests"

SITE_JSON = CONTENT_DIR / "site.json"
CONTROL_CSV = CONTENT_DIR / "control.csv"
LINKS_CSV = CONTENT_DIR / "links.csv"
POSTS_CSV = BLOG_DIR / "posts.csv"

PLACEHOLDER_IMAGES = {
    "placeholder-hero.svg": "Warm abstract hero placeholder",
    "placeholder-studio.svg": "Studio placeholder",
    "placeholder-lab.svg": "Lab placeholder",
    "placeholder-portrait.svg": "Portrait placeholder",
    "placeholder-grid.svg": "Project grid placeholder",
}

NAV_SLUGS = ["", "about", "research", "projects", "digest", "blog", "contact"]


def _escape(text: str) -> str:
    return html.escape(text or "", quote=True)


def _slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\s-]", "", text or "")
    cleaned = re.sub(r"\s+", "-", cleaned.strip())
    return cleaned.lower() or "post"


def _split_paragraphs(text: str) -> list[str]:
    normalized = (text or "").replace("\n", "\n").strip()
    if not normalized:
        return []
    chunks = re.split(r"\n\s*\n", normalized)
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _render_paragraphs(text: str) -> str:
    return "\n".join(f"<p>{_escape(p)}</p>" for p in _split_paragraphs(text))


def _render_emphasis(text: str) -> str:
    escaped = _escape(text or "")
    if not escaped:
        return ""
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    return escaped


def _render_inline_markdown(text: str) -> str:
    pattern = re.compile(r"[[^]]+]\]\(([^)]+)\)")
    parts: list[str] = []
    last = 0
    raw = text or ""
    for match in pattern.finditer(raw):
        parts.append(_render_emphasis(raw[last:match.start()]))
        label = _render_emphasis(match.group(1))
        href = _escape(match.group(2))
        parts.append(f"<a href=\"{href}\">{label}</a>")
        last = match.end()
    parts.append(_render_emphasis(raw[last:]))
    return "".join(parts)


def _render_markdown(text: str) -> str:
    cleaned = (text or "").replace("\r\n", "\n").strip()
    if not cleaned:
        return ""
    blocks = re.split(r"\n\s*\n", cleaned)
    rendered: list[str] = []
    for block in blocks:
        lines = [line.rstrip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if all(line.lstrip().startswith(("-", "*")) for line in lines):
            items = [
                f"<li>{_render_inline_markdown(line.lstrip()[1:].strip())}</li>"
                for line in lines
            ]
            rendered.append("<ul>" + "".join(items) + "</ul>")
            continue
        heading_match = re.match(r"^(#{1,3})\s+(.*)$", lines[0])
        if heading_match:
            level = len(heading_match.group(1))
            heading = _render_inline_markdown(heading_match.group(2))
            tag = "h2" if level == 1 else "h3" if level == 2 else "h4"
            rendered.append(f"<{tag}>{heading}</{tag}>")
            rest = [line for line in lines[1:] if line.strip()]
            if rest:
                rendered.append(f"<p>{_render_inline_markdown(' '.join(rest))}</p>")
            continue
        rendered.append(f"<p>{_render_inline_markdown(' '.join(lines))}</p>")
    return "\n".join(rendered)


def _resolve_block_path(source_md: str) -> Path | None:
    if not source_md:
        return None
    source = Path(source_md)
    if source.is_absolute():
        candidate = source
    elif "/" in source_md or "\\" in source_md:
        candidate = CONTENT_DIR / source
    else:
        candidate = BLOCKS_DIR / source
    resolved = candidate.resolve()
    if not resolved.is_relative_to(CONTENT_DIR):
        raise SystemExit(f"Block path outside content directory: {source_md}")
    return resolved


def _read_block(source_md: str) -> str:
    path = _resolve_block_path(source_md)
    if not path:
        return ""
    if not path.exists():
        raise SystemExit(f"Missing block file: {path}")
    return path.read_text(encoding="utf-8")


def _read_site_config() -> dict[str, Any]:
    if SITE_JSON.exists():
        return json.loads(SITE_JSON.read_text(encoding="utf-8"))
    return {
        "site_name": "Artificial Life Institute",
        "site_tagline": "",
        "meta_description": "Artificial Life Institute at the University of Vienna",
        "contact_blurb": "",
        "domain": "",
        "newsletter_mode": "local",
        "newsletter_provider_url": "",
        "layout_variant": "standard",
        "footer_note": "",
        "address": "",
        "show_digest_home": "false",
    }


def _normalize_slug(raw_slug: str) -> str:
    slug = (raw_slug or "").strip()
    if slug in {"", "/", "index", "home"}:
        return ""
    return slug.strip("/")


def _page_output_path(slug: str) -> Path:
    if slug == "":
        return Path("index.html")
    return Path(slug) / "index.html"


def _page_link_path(slug: str) -> Path:
    if slug == "":
        return Path(".")
    return Path(slug)


def _rel_link(current_path: Path, target_path: Path) -> str:
    current_dir = current_path.parent.as_posix()
    target = target_path.as_posix()
    rel = os.path.relpath(target, start=current_dir)
    return rel


def _rel_dir_link(current_path: Path, target_dir: Path) -> str:
    current_dir = current_path.parent.as_posix() or "."
    target_dir_str = target_dir.as_posix() or "."
    rel = os.path.relpath(target_dir_str, start=current_dir)
    if rel == ".":
        return "./"
    return rel.rstrip("/") + "/"


def _rel_page_link(current_path: Path, slug: str) -> str:
    return _rel_dir_link(current_path, _page_link_path(slug))


def _resolve_image_src(raw_image: str, current_path: Path) -> str:
    image = (raw_image or "").strip()
    if not image:
        image = "placeholder-hero.svg"
    if image.startswith("assets/"):
        return _rel_link(current_path, Path(image))
    return _rel_link(current_path, Path("assets/img") / image)


def _read_control() -> dict[str, dict[str, object]]:
    if not CONTROL_CSV.exists():
        raise SystemExit(f"Missing control file: {CONTROL_CSV}")
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
            entry = pages.setdefault(
                slug,
                {
                    "title": slug.title() or "Home",
                    "sections": [],
                    "order": 0,
                },
            )
            kind = (data.get("kind") or "section").lower()
            if kind in {"page", "meta"}:
                if data.get("title"):
                    entry["title"] = data["title"]
                entry["order"] = order
                continue
            section_id = data.get("section") or data.get("id") or ""
            entry["sections"].append(
                {
                    **data,
                    "order": order,
                    "page_slug": slug,
                    "section_id": section_id,
                    "kind": kind,
                }
            )
    for page in pages.values():
        page["sections"] = sorted(page["sections"], key=lambda item: item["order"])
    return pages


def _read_links() -> list[dict[str, str]]:
    if not LINKS_CSV.exists():
        return []
    items: list[dict[str, str]] = []
    with LINKS_CSV.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            data = {key: (value or "").strip() for key, value in row.items()}
            if not data.get("label"):
                continue
            items.append(data)
    items.sort(key=lambda item: int(item.get("order") or 0))
    return items


def _read_digests() -> list[dict[str, str]]:
    if not DIGESTS_DIR.exists():
        return []
    index_path = DIGESTS_DIR / "index.json"
    if not index_path.exists():
        return []
    raw = json.loads(index_path.read_text(encoding="utf-8"))
    items = []
    for entry in raw.get("digests", []):
        if not isinstance(entry, dict):
            continue
        date = str(entry.get("date", "")).strip()
        title = str(entry.get("title", "")).strip()
        slug = str(entry.get("slug", "")).strip()
        source_md = str(entry.get("source_md", "")).strip()
        if not (date and slug and source_md):
            continue
        items.append(
            {
                "date": date,
                "title": title or f"Digest {date}",
                "slug": slug,
                "source_md": source_md,
            }
        )
    return items


def _parse_blog_post(path: Path) -> dict[str, str]:
    raw = path.read_text(encoding="utf-8")
    title = ""
    date = ""
    body = ""
    slug = _slugify(path.stem)

    # Check for YAML frontmatter
    if raw.startswith("---"):
        parts = re.split(r"^---\s*$", raw, maxsplit=2, flags=re.MULTILINE)
        if len(parts) >= 3:
            frontmatter = parts[1]
            body = parts[2].strip()
            for line in frontmatter.splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    k, v = key.strip().lower(), value.strip()
                    if k == "title":
                        title = v.strip('"')
                    elif k == "date":
                        date = v.strip('"')
                    elif k == "slug":
                        slug = v.strip('"')
            if not date:
                date = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
            return {"title": title or path.stem, "date": date, "body": body, "slug": slug}

    # Legacy format
    body_lines: list[str] = []
    in_body = False
    for line in raw.splitlines():
        if not in_body and line.strip() == "":
            in_body = True
            continue
        if not in_body:
            if line.startswith("Title:"):
                title = line.split(":", 1)[1].strip()
            elif line.startswith("Date:"):
                date = line.split(":", 1)[1].strip()
            elif line.startswith("Body:"):
                in_body = True
        else:
            body_lines.append(line)
    if not title:
        title = path.stem
    if not date:
        date = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
    body = "\n".join(body_lines).strip()
    return {"title": title, "date": date, "body": body, "slug": slug}


def _read_blog_posts() -> list[dict[str, str]]:
    if not BLOG_DIR.exists():
        return []
    
    posts = []
    seen_slugs = set()

    # 1. Read from posts.csv
    if POSTS_CSV.exists():
        with POSTS_CSV.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                data = {key: (value or "").strip() for key, value in row.items()}
                if not data.get("source_md"):
                    continue
                
                source_path = BLOG_DIR / data["source_md"]
                if not source_path.exists():
                    print(f"Warning: Blog post file not found: {source_path}")
                    continue
                
                # Parse the file content to get the body, but prefer CSV metadata if available
                file_data = _parse_blog_post(source_path)
                
                title = data.get("title") or file_data["title"]
                date = data.get("date") or file_data["date"]
                slug = data.get("slug") or file_data["slug"]
                
                posts.append({
                    "title": title,
                    "date": date,
                    "slug": slug,
                    "body": file_data["body"]
                })
                seen_slugs.add(slug)

    # 2. Scan for legacy .txt files
    for path in sorted(BLOG_DIR.glob("*.txt")):
        file_data = _parse_blog_post(path)
        if file_data["slug"] not in seen_slugs:
            posts.append(file_data)
            seen_slugs.add(file_data["slug"])

    posts.sort(key=lambda item: item.get("date", ""), reverse=True)
    return posts


def _resolve_cta_url(raw_url: str, pages: dict[str, dict[str, object]], current_path: Path) -> str:
    if not raw_url:
        return ""
    if raw_url.startswith("http") or raw_url.startswith("mailto:") or raw_url.startswith("#"):
        return raw_url
    slug = _normalize_slug(raw_url)
    if slug in pages:
        return _rel_page_link(current_path, slug)
    return raw_url


def _render_newsletter_form(site: dict[str, str], current_path: Path) -> str:
    mode = (site.get("newsletter_mode") or "local").strip()
    provider_url = (site.get("newsletter_provider_url") or "").strip()
    if mode == "local" or not provider_url:
        endpoint = _rel_link(current_path, Path("subscribe.php"))
    else:
        endpoint = provider_url
    return f"""
<div class="newsletter" id="newsletter">
  <div>
    <h3>Newsletter</h3>
    <p>Subscribe for institute updates, events, and research highlights.</p>
  </div>
  <form class="newsletter-form" data-newsletter-form action="{_escape(endpoint)}" method="post">
    <label class="sr-only" for="newsletter-email">Email</label>
    <input id="newsletter-email" name="email" type="email" placeholder="you@example.org" required />
    <div class="sr-only" aria-hidden="true">
      <label for="newsletter-company">Company</label>
      <input id="newsletter-company" name="company" type="text" tabindex="-1" autocomplete="off" />
    </div>
    <button class="button" type="submit">Subscribe</button>
    <p class="form-status" aria-live="polite"></p>
  </form>
</div>
"""


def _render_links(links: list[dict[str, str]]) -> str:
    if not links:
        return ""
    items = []
    for link in links:
        label = _escape(link.get("label", ""))
        url = _escape(link.get("url", ""))
        kind = (link.get("kind") or "").strip()
        class_name = "tag" if kind == "placeholder" else "tag primary"
        items.append(f"<a class=\"{class_name}\" href=\"{url}\" rel=\"noopener\">{label}</a>")
    return "<div class=\"tag-list\">" + "".join(items) + "</div>"


def _render_head(title: str, css_href: str, description: str, extra_css: str = "") -> str:
    extra_css = extra_css.strip()
    if extra_css:
        extra_css = "\n  " + extra_css
    return f"""
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_escape(title)}</title>
  <meta name="description" content="{_escape(description)}" />
  <link rel="stylesheet" href="{_escape(css_href)}" />{extra_css}
</head>
"""


def _render_header(current_slug: str, pages: dict[str, dict[str, object]], current_path: Path) -> str:
    nav_links = []
    for slug in NAV_SLUGS:
        if slug not in pages:
            continue
        title = pages[slug]["title"]
        href = _rel_page_link(current_path, slug)
        active = "active" if slug == current_slug else ""
        nav_links.append(f"<a class=\"{active}\" href=\"{_escape(href)}\">{_escape(title)}</a>")
    cta_href = _rel_page_link(current_path, "contact") if "contact" in pages else "#"
    return f"""
<header class="site-header">
  <a class="logo" href="{_escape(_rel_page_link(current_path, ""))}">ALI</a>
  <nav class="nav">{''.join(nav_links)}</nav>
  <a class="cta" href="{_escape(cta_href)}">Get in touch</a>
</header>
"""


def _render_footer(site: dict[str, str], pages: dict[str, dict[str, object]], current_path: Path, links: list[dict[str, str]]) -> str:
    footer_links = []
    for slug in ("privacy", "imprint"):
        if slug in pages:
            href = _rel_page_link(current_path, slug)
            footer_links.append(f"<a href=\"{_escape(href)}\">{_escape(pages[slug]['title'])}</a>")
    links_html = "".join(footer_links)
    digital_html = _render_links(links)
    address = _escape(site.get("address", ""))
    note = _escape(site.get("footer_note", ""))
    domain = _escape(site.get("domain", ""))
    return f"""
<footer class="site-footer">
  <div class="footer-grid">
    <div>
      <p class="footer-title">Artificial Life Institute</p>
      <p>{address}</p>
      <p>{note}</p>
      <p><a href="{domain}">{domain}</a></p>
    </div>
    <div>
      <p class="footer-title">Digital presence</p>
      {digital_html}
    </div>
    <div>
      <p class="footer-title">Legal</p>
      <div class="footer-links">{links_html}</div>
    </div>
  </div>
</footer>
"""


def _render_section(
    section: dict[str, str],
    current_path: Path,
    pages: dict[str, dict[str, object]],
    digests: list[dict[str, str]],
) -> str:
    kind = (section.get("kind") or "section").lower()
    if kind == "contact_form":
        return _render_contact_form(section, current_path)
    if kind == "digest_list":
        return _render_digest_list(section, current_path, digests)
    heading = _escape(section.get("title", ""))
    body = _render_markdown(_read_block(section.get("source_md", "")))
    cta_text = _escape(section.get("cta_text", ""))
    raw_cta_url = section.get("cta_url", "")
    cta_url = _resolve_cta_url(raw_cta_url, pages, current_path)
    cta = ""
    if cta_text and cta_url:
        cta = f"<a class=\"button ghost\" href=\"{_escape(cta_url)}\">{cta_text}</a>"
    image_src = _resolve_image_src(section.get("hero_image", ""), current_path)
    image = f"<figure class=\"image-frame\"><img src=\"{_escape(image_src)}\" alt=\"{heading} image\" /></figure>"
    section_id = _escape(section.get("section_id", ""))
    return f"""
<section class="content-section" id="{section_id}">
  <div class="content-grid">
    <div>
      <h2>{heading}</h2>
      {body}
      {cta}
    </div>
    {image}
  </div>
</section>
"""


def _render_linkhub_links(links: list[dict[str, str]]) -> str:
    if not links:
        return ""
    items = []
    for link in links:
        label = _escape(link.get("label", ""))
        url = _escape(link.get("url", ""))
        kind = (link.get("kind") or "").strip()
        class_name = "linkhub-link placeholder" if kind == "placeholder" else "linkhub-link"
        items.append(f"<a class=\"{class_name}\" href=\"{url}\" rel=\"noopener\">{label}</a>")
    return "<div class=\"linkhub-links\">" + "".join(items) + "</div>"


def _render_contact_form(section: dict[str, str], current_path: Path) -> str:
    section_id = _escape(section.get("section_id", "contact-form"))
    heading = _escape(section.get("title", "Contact"))
    body = _render_markdown(_read_block(section.get("source_md", "")))
    endpoint = _rel_link(current_path, Path("contact.php"))
    return f"""
<section class="content-section contact-section" id="{section_id}">
  <div class="content-grid">
    <div>
      <h2>{heading}</h2>
      {body}
    </div>
    <div class="contact-card">
      <form class="contact-form" data-contact-form action="{_escape(endpoint)}" method="post">
        <div class="contact-field">
          <label for="contact-name">Name</label>
          <input id="contact-name" name="name" type="text" required />
        </div>
        <div class="contact-field">
          <label for="contact-email">Email</label>
          <input id="contact-email" name="email" type="email" required />
        </div>
        <div class="contact-field">
          <label for="contact-message">Message</label>
          <textarea id="contact-message" name="message" rows="5" required></textarea>
        </div>
        <div class="contact-field sr-only" aria-hidden="true">
          <label for="contact-company">Company</label>
          <input id="contact-company" name="company" type="text" tabindex="-1" autocomplete="off" />
        </div>
        <button class="button" type="submit">Send message</button>
        <p class="form-status" aria-live="polite"></p>
      </form>
    </div>
  </div>
</section>
"""


def _render_digest_list(section: dict[str, str], current_path: Path, digests: list[dict[str, str]]) -> str:
    section_id = _escape(section.get("section_id", "digest"))
    heading = _escape(section.get("title", "Digest"))
    intro = _render_markdown(_read_block(section.get("source_md", "")))
    items = digests[:5]
    if not items:
        listing = "<p>No digests yet. Run tools/fetch_digest.py to create the first issue.</p>"
    else:
        cards = []
        for digest in items:
            target = _rel_dir_link(current_path, Path("digest") / digest["slug"])
            cards.append(
                f"""<article class=\"digest-card\">
  <p class=\"post-date\">{_escape(digest['date'])}</p>
  <h3><a href=\"{_escape(target)}\">{_escape(digest['title'])}</a></h3>
</article>"""
            )
        listing = "<div class=\"digest-grid\">" + "".join(cards) + "</div>"
    return f"""
<section class="content-section digest-section" id="{section_id}">
  <div class="content-grid">
    <div>
      <h2>{heading}</h2>
      {intro}
    </div>
    <div>
      {listing}
    </div>
  </div>
</section>
"""


def _render_home_overview(pages: dict[str, dict[str, object]], current_path: Path) -> str:
    cards = []
    for slug in NAV_SLUGS:
        if slug in ("", "blog", "contact"):
            continue
        if slug not in pages:
            continue
        title = pages[slug]["title"]
        target = _rel_page_link(current_path, slug)
        cards.append(
            f"<a class=\"card\" href=\"{_escape(target)}\"><h3>{_escape(title)}</h3><p>Placeholder summary for { _escape(title) }.</p></a>"
        )
    return "<div class=\"card-grid\">" + "".join(cards) + "</div>"


def _render_blog_index(posts: list[dict[str, str]], current_path: Path) -> str:
    if not posts:
        return "<p>No posts yet. Add a file to content/blog/ to publish the first update.</p>"
    cards = []
    for post in posts:
        target = _rel_dir_link(current_path, Path("blog") / post["slug"])
        excerpt = _split_paragraphs(post.get("body", ""))
        teaser = excerpt[0] if excerpt else ""
        cards.append(
            """
<article class="post-card">
  <p class="post-date">{date}</p>
  <h3><a href="{href}">{title}</a></h3>
  <p>{teaser}</p>
</article>
""".format(
                date=_escape(post.get("date", "")),
                href=_escape(target),
                title=_escape(post.get("title", "")),
                teaser=_escape(teaser),
            )
        )
    return "<div class=\"post-grid\">" + "".join(cards) + "</div>"


def _render_digest_index(digests: list[dict[str, str]], current_path: Path) -> str:
    if not digests:
        return "<p>No digests yet. Add feeds and run tools/fetch_digest.py to publish the first issue.</p>"
    cards = []
    for digest in digests:
        target = _rel_dir_link(current_path, Path("digest") / digest["slug"])
        cards.append(
            """
<article class="digest-card">
  <p class="post-date">{date}</p>
  <h3><a href="{href}">{title}</a></h3>
</article>
""".format(
                date=_escape(digest.get("date", "")),
                href=_escape(target),
                title=_escape(digest.get("title", "")),
            )
        )
    return "<div class=\"digest-grid\">" + "".join(cards) + "</div>"


def _render_digest_page(digest: dict[str, str], pages: dict[str, dict[str, object]], site: dict[str, str], links: list[dict[str, str]]) -> None:
    slug = digest["slug"]
    current_path = Path("digest") / slug / "index.html"
    css_href = _rel_link(current_path, Path("assets/css/style.css"))
    header = _render_header("digest", pages, current_path)
    footer = _render_footer(site, pages, current_path, links)
    back_link = _rel_page_link(current_path, "digest")
    body_html = _render_markdown(_read_block(digest.get("source_md", "")))
    doc = f"""<!doctype html>
<html lang=\"en\">
{_render_head(digest.get('title', ''), css_href, site.get('meta_description', ''))}
<body data-newsletter-mode="{_escape(site.get('newsletter_mode', 'local'))}" data-newsletter-url="{_escape(site.get('newsletter_provider_url', ''))}">
  <div class="page-shell">
    {header}
    <main>
      <section class="page-hero">
        <div class="page-hero-inner">
          <p class="eyebrow">Research Digest</p>
          <h1>{_escape(digest.get('title', ''))}</h1>
          <p class="post-date">{_escape(digest.get('date', ''))}</p>
        </div>
      </section>
      <section class="page-body">
        <div class="content-block">
          {body_html}
          <a class="button ghost" href="{_escape(back_link)}">Back to digest</a>
        </div>
      </section>
    </main>
    {footer}
  </div>
  <script src="{_escape(_rel_link(current_path, Path('assets/js/main.js')))}"></script>
</body>
</html>
"""
    output_path = SITE_DIR / current_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(doc, encoding="utf-8")


def _render_blog_post(post: dict[str, str], pages: dict[str, dict[str, object]]) -> None:
    slug = post["slug"]
    current_path = Path("blog") / slug / "index.html"
    css_href = _rel_link(current_path, Path("assets/css/style.css"))
    header = _render_header("blog", pages, current_path)
    footer = _render_footer(_read_site_config(), pages, current_path, _read_links())
    back_link = _rel_page_link(current_path, "blog")
    body_html = _render_paragraphs(post.get("body", ""))
    doc = f"""<!doctype html>
<html lang=\"en\">
{_render_head(post.get('title', ''), css_href, _read_site_config().get('meta_description', ''))}
<body data-newsletter-mode="{_escape(_read_site_config().get('newsletter_mode', 'local'))}" data-newsletter-url="{_escape(_read_site_config().get('newsletter_provider_url', ''))}">
  <div class="page-shell">
    {header}
    <main>
      <section class="page-hero">
        <div class="page-hero-inner">
          <p class="eyebrow">Institute Blog</p>
          <h1>{_escape(post.get('title', ''))}</h1>
          <p class="post-date">{_escape(post.get('date', ''))}</p>
        </div>
      </section>
      <section class="page-body">
        <div class="content-block">
          {body_html}
          <a class="button ghost" href="{_escape(back_link)}">Back to blog</a>
        </div>
      </section>
    </main>
    {footer}
  </div>
  <script src="{_escape(_rel_link(current_path, Path('assets/js/main.js')))}"></script>
</body>
</html>
"""
    output_path = SITE_DIR / current_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(doc, encoding="utf-8")



def _build_css(site: dict[str, Any]) -> str:
    theme = site.get("theme", {})
    if not isinstance(theme, dict):
        theme = {}
        
    # Defaults (ALI Bordeaux)
    primary = theme.get("primary", "#65141c")
    primary_dark = theme.get("primary_dark", "#3a1016")
    primary_bright = theme.get("primary_bright", "#92202b")
    cream = theme.get("background", "#f3f1f0")
    paper = theme.get("paper", "#f9f8f7")
    gold = theme.get("accent", "#e0b15a")
    text_main = theme.get("text_main", "#1a1a1a")
    text_muted = theme.get("text_muted", "#4a4a4a")

    return f"""
:root {{
  color-scheme: light;
  
  /* Dynamic Theme Tokens */
  --bordeaux: {primary};
  --bordeaux-dark: {primary_dark};
  --bordeaux-bright: {primary_bright};
  --cream: {cream};
  --paper: {paper};
  --gold: {gold};
  
  --bg-dark: var(--bordeaux-dark);
  --bg-light: var(--paper);
  --text-main: {text_main};
  --text-muted: {text_muted};
  
  --header-bg: {cream}d9;
  --card: #ffffff;
  --card-border: {primary}1a;
  --glass: rgba(255, 255, 255, 0.6);
  --shadow: {primary_dark}1a;
  
  --font-heading: "Cormorant Garamond", serif;
  --font-body: "Outfit", sans-serif;
  --radius: 8px;
  --max-width: 1000px;
}}

/* Base */
body {{
  margin: 0;
  font-family: var(--font-body);
  background: var(--paper);
  color: var(--text-main);
  line-height: 1.6;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.03'/%3E%3C/svg%3E");
}}

/* Typography */
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Outfit:wght@300;400;500&display=swap');

h1, h2, h3 {{
  font-family: var(--font-heading);
  color: var(--bordeaux);
  margin-top: 0;
}}

h1 {{ font-size: 3.5rem; letter-spacing: -0.01em; margin-bottom: 0.5rem; }}
h2 {{ font-size: 2.2rem; margin-bottom: 1.5rem; border-bottom: 2px solid var(--gold); display: inline-block; padding-bottom: 5px; }}
a {{ color: var(--bordeaux); text-decoration: none; font-weight: 500; transition: color 0.2s; }}
a:hover {{ color: var(--bordeaux-bright); }}

/* Layout */
.page-shell {{ min-height: 100vh; display: flex; flex-direction: column; }}
main {{ flex: 1; padding-top: 100px; }}

/* Header */
.site-header {{
  position: fixed;
  top: 0;
  width: 100%;
  padding: 20px 5vw;
  display: flex;
  justify-content: space-between;
  align-items: center;
  z-index: 100;
  background: var(--header-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--card-border);
}}

.logo {{
  font-family: var(--font-heading);
  font-size: 24px;
  font-weight: 700;
  color: var(--bordeaux);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}

.nav {{ display: flex; gap: 30px; }}
.nav a {{ color: var(--text-muted); text-transform: uppercase; font-size: 14px; letter-spacing: 0.1em; }}
.nav a:hover, .nav a.active {{ color: var(--bordeaux); }}

/* Components */
.card, .profile-card {{
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: var(--radius);
  padding: 40px;
  box-shadow: 0 10px 30px -10px var(--shadow);
  transition: transform 0.3s;
}}

.card:hover {{ transform: translateY(-5px); }}

.button {{
  padding: 12px 28px;
  background: var(--bordeaux);
  color: #fff;
  border-radius: 4px;
  text-transform: uppercase;
  font-size: 14px;
  letter-spacing: 0.1em;
  border: none;
  cursor: pointer;
}}
.button:hover {{ background: var(--bordeaux-bright); box-shadow: 0 5px 15px rgba(101, 20, 28, 0.2); }}

/* Forms */
input, textarea {{
  width: 100%;
  padding: 15px;
  border: 1px solid var(--card-border);
  border-radius: 4px;
  background: #fff;
  font-family: var(--font-body);
  margin-bottom: 20px;
}}
input:focus, textarea:focus {{ border-color: var(--bordeaux); outline: none; }}

/* Footer */
.site-footer {{
  background: var(--bordeaux-dark);
  color: var(--cream);
  padding: 60px 5vw;
  margin-top: auto;
}}
.site-footer a {{ color: var(--gold); }}
"""


def _build_js() -> str:
    return """
const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

function revealOnScroll() {
  const revealItems = document.querySelectorAll('.reveal');
  if (prefersReduced) {
    revealItems.forEach((item) => item.classList.add('is-visible'));
    return;
  }
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.2 });

  revealItems.forEach((item) => observer.observe(item));
}

function smoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener('click', (event) => {
      const targetId = link.getAttribute('href');
      if (!targetId || targetId.length < 2) return;
      const target = document.querySelector(targetId);
      if (!target) return;
      event.preventDefault();
      target.scrollIntoView({ behavior: prefersReduced ? 'auto' : 'smooth' });
    });
  });
}

function setupNewsletter() {
  const form = document.querySelector('[data-newsletter-form]');
  if (!form) return;
  const status = form.querySelector('.form-status');
  const body = document.body;
  const mode = body.dataset.newsletterMode || 'local';
  const providerUrl = body.dataset.newsletterUrl || '';
  const setStatus = (message, state) => {
    if (!status) return;
    status.textContent = message;
    if (state) {
      status.dataset.state = state;
    } else {
      status.removeAttribute('data-state');
    }
  };
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (mode !== 'local' && !providerUrl) {
      setStatus('Newsletter endpoint is not configured.', 'error');
      return;
    }
    const emailInput = form.querySelector('input[name="email"]');
    const email = emailInput ? emailInput.value.trim() : '';
    if (!email) {
      setStatus('Please enter a valid email.', 'error');
      return;
    }
    const companyInput = form.querySelector('input[name="company"]');
    const company = companyInput ? companyInput.value.trim() : '';
    const endpoint = mode === 'local' || !providerUrl ? form.getAttribute('action') : providerUrl;
    if (!endpoint) {
      setStatus('Newsletter endpoint is not configured.', 'error');
      return;
    }
    setStatus('Submitting...', 'pending');
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ email, company })
      });
      const payload = await response.json().catch(() => null);
      const ok = response.ok && (payload === null || typeof payload.ok === 'undefined' || payload.ok);
      if (ok) {
        setStatus('Thanks for subscribing.', 'success');
        form.reset();
      } else {
        setStatus((payload && payload.error) || 'Subscription failed. Please try again.', 'error');
      }
    } catch (error) {
      setStatus('Subscription failed. Please try again.', 'error');
    }
  });
}

function setupContactForm() {
  const form = document.querySelector('[data-contact-form]');
  if (!form) return;
  const status = form.querySelector('.form-status');
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const nameInput = form.querySelector('input[name="name"]');
    const emailInput = form.querySelector('input[name="email"]');
    const messageInput = form.querySelector('textarea[name="message"]');
    const companyInput = form.querySelector('input[name="company"]');
    const name = nameInput ? nameInput.value.trim() : '';
    const email = emailInput ? emailInput.value.trim() : '';
    const message = messageInput ? messageInput.value.trim() : '';
    const company = companyInput ? companyInput.value.trim() : '';
    if (!name || !email || !message) {
      status.textContent = 'Please complete all required fields.';
      return;
    }
    const endpoint = form.getAttribute('action');
    if (!endpoint) {
      status.textContent = 'Contact endpoint is not configured.';
      return;
    }
    status.textContent = 'Sending...';
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ name, email, message, company })
      });
      const payload = await response.json().catch(() => ({}));
      if (response.ok && payload.ok) {
        status.textContent = 'Message sent. Thank you.';
        form.reset();
      } else {
        status.textContent = payload.error || 'Message failed. Please try again.';
      }
    } catch (error) {
      status.textContent = 'Message failed. Please try again.';
    }
  });
}

window.addEventListener('DOMContentLoaded', () => {
  revealOnScroll();
  smoothScroll();
  setupNewsletter();
  setupContactForm();
});
""".lstrip()


def _render_archive_layout(site: dict[str, str], pages: dict[str, dict[str, object]], current_path: Path, hero_heading: str, hero_body: str, sections_html: str, overview_html: str, page_body_html: str) -> str:
    """Render archive layout with dual-sidebar structure."""
    return f"""
      <section class="archive-layout">
        <aside class="archive-sidebar-left">
          <nav class="archive-nav">
            <h3>The Index</h3>
            <ul>
              <li><a href="#overview">Overview</a></li>
              <li><a href="#research">Research</a></li>
              <li><a href="#projects">Projects</a></li>
              <li><a href="#publications">Publications</a></li>
            </ul>
          </nav>
        </aside>
        <main class="archive-main">
          <header class="archive-header">
            <h1>{_escape(hero_heading)}</h1>
            {hero_body}
          </header>
          {overview_html}
          {sections_html}
          {page_body_html}
        </main>
        <aside class="archive-sidebar-right">
          <div class="archive-metadata">
            <h3>Citations</h3>
            <p>Quick reference metadata appears here.</p>
          </div>
        </aside>
      </section>
"""


def _render_mescia_landing(site: dict[str, str], pages: dict[str, dict[str, object]], current_path: Path) -> str:
    hero_title = _escape(site.get("site_name", "Mescia"))
    tagline = _escape(site.get("site_tagline", ""))
    
    # Generate navigation zones data
    zones_html = ""
    for slug, page in pages.items():
        if slug == "": continue
        title = _escape(page.get("title", slug.title()))
        url = _escape(_rel_page_link(current_path, slug))
        # Data attributes for the JS to pick up
        zones_html += f'<a href="{url}" class="landing-zone" data-label="{title}"><span class="zone-label">{title}</span></a>'
        
    return f"""
      <section class="mescia-landing">
        <canvas id="mescia-canvas"></canvas>
        <div class="mescia-overlay">
            <div class="landing-zones-container">
                {zones_html}
            </div>
            <div class="main-entrance">
                <h1>{hero_title}</h1>
                <p>{tagline}</p>
                <a href="#research" class="enter-button" id="enter-site-btn">Enter</a>
            </div>
        </div>
      </section>
"""


def _build_placeholder_svg(label: str) -> str:
    safe_label = _escape(label)
    return f"""<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 600 400\" role=\"img\" aria-label=\"{safe_label}\">
  <defs>
    <linearGradient id=\"g\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"1\">
      <stop offset=\"0%\" stop-color=\"#6b0f1a\" stop-opacity=\"0.2\" />
      <stop offset=\"100%\" stop-color=\"#e0b15a\" stop-opacity=\"0.3\" />
    </linearGradient>
  </defs>
  <rect width=\"600\" height=\"400\" fill=\"#f4ecea\" />
  <rect x=\"40\" y=\"40\" width=\"520\" height=\"320\" fill=\"url(#g)\" rx=\"26\" />
  <circle cx=\"470\" cy=\"130\" r=\"70\" fill=\"#6b0f1a\" fill-opacity=\"0.16\" />
  <rect x=\"120\" y=\"230\" width=\"240\" height=\"18\" rx=\"9\" fill=\"#6b0f1a\" fill-opacity=\"0.25\" />
  <rect x=\"120\" y=\"260\" width=\"180\" height=\"12\" rx=\"6\" fill=\"#0f0f0f\" fill-opacity=\"0.2\" />
  <text x=\"120\" y=\"205\" fill=\"#3e0a11\" font-family=\"Georgia, serif\" font-size=\"22\">{safe_label}</text>
</svg>
"""


def _write_site_assets(site: dict[str, Any]) -> None:
    CSS_DIR.mkdir(parents=True, exist_ok=True)
    JS_DIR.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    (CSS_DIR / "style.css").write_text(_build_css(site), encoding="utf-8")
    (JS_DIR / "main.js").write_text(_build_js(), encoding="utf-8")
    
    # Copy landing assets if they exist in content/assets, otherwise use defaults (which we'll define)
    # Actually, simpler to just write them here directly or rely on the copy block below.
    # The build script copies assets from CONTENT_DIR/assets usually?
    # No, it copies from MEDIA_DIR (content/media) to IMG_DIR.
    # It hardcodes style.css and main.js from strings in the script.
    
    # We will assume landing assets are placed in content/assets/css/landing.css and content/assets/js/landing.js
    # and we need to copy them to SITE_DIR/assets
    
    # I should modify this to copy content/assets to site/assets if it exists.
    src_assets = CONTENT_DIR / "assets"
    if src_assets.exists():
        for path in src_assets.rglob("*"):
            if path.is_file():
                rel = path.relative_to(src_assets)
                dest = ASSETS_DIR / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists(): # Don't overwrite generated files like style.css unless intended
                    shutil.copy2(path, dest)

    for name, label in PLACEHOLDER_IMAGES.items():
        (IMG_DIR / name).write_text(_build_placeholder_svg(label), encoding="utf-8")
    if MEDIA_DIR.exists():
        for path in MEDIA_DIR.rglob("*"):
            if path.is_dir():
                continue
            target = IMG_DIR / path.relative_to(MEDIA_DIR)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def _write_subscribe_php() -> None:
    php = """<?php
header('Content-Type: application/json');

function fail($code, $error) {
  http_response_code($code);
  echo json_encode(['ok' => false, 'error' => $error]);
  exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
  fail(405, 'method_not_allowed');
}

$honeypot = trim($_POST['company'] ?? '');
if ($honeypot !== '') {
  fail(400, 'invalid_request');
}

$email = trim($_POST['email'] ?? '');
if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
  fail(400, 'invalid_email');
}

$dataDir = __DIR__ . '/data';
if (!is_dir($dataDir)) {
  mkdir($dataDir, 0750, true);
}

$rateFile = $dataDir . '/ratelimit.json';
$ip = $_SERVER['REMOTE_ADDR'] ?? 'unknown';
$now = time();
$window = 3600;
$limit = 8;

$rateHandle = fopen($rateFile, 'c+');
if (!$rateHandle) {
  fail(500, 'storage_unavailable');
}
flock($rateHandle, LOCK_EX);
$contents = stream_get_contents($rateHandle);
$rateData = $contents ? json_decode($contents, true) : [];
if (!is_array($rateData)) {
  $rateData = [];
}
$entries = $rateData[$ip] ?? [];
$entries = array_values(array_filter($entries, function($ts) use ($now, $window) {
  return $ts >= ($now - $window);
}));
if (count($entries) >= $limit) {
  flock($rateHandle, LOCK_UN);
  fclose($rateHandle);
  fail(429, 'rate_limited');
}
$entries[] = $now;
$rateData[$ip] = $entries;
rewind($rateHandle);
ftruncate($rateHandle, 0);
fwrite($rateHandle, json_encode($rateData, JSON_PRETTY_PRINT));
flock($rateHandle, LOCK_UN);
fclose($rateHandle);

$file = $dataDir . '/newsletter_signups.csv';
$handle = fopen($file, 'a');
if (!$handle) {
  fail(500, 'storage_unavailable');
}
flock($handle, LOCK_EX);
fputcsv($handle, [gmdate('c'), $email, $ip]);
flock($handle, LOCK_UN);
fclose($handle);

echo json_encode(['ok' => true]);
"""
    (SITE_DIR / "subscribe.php").write_text(php, encoding="utf-8")


def _write_contact_php() -> None:
    php = """<?php
header('Content-Type: application/json');

function fail($code, $error) {
  http_response_code($code);
  echo json_encode(['ok' => false, 'error' => $error]);
  exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
  fail(405, 'method_not_allowed');
}

$honeypot = trim($_POST['company'] ?? '');
if ($honeypot !== '') {
  fail(400, 'invalid_request');
}

$name = trim($_POST['name'] ?? '');
$email = trim($_POST['email'] ?? '');
$message = trim($_POST['message'] ?? '');

if ($name === '' || $email === '' || $message === '') {
  fail(400, 'missing_fields');
}
if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
  fail(400, 'invalid_email');
}
if (mb_strlen($message) > 4000) {
  fail(400, 'message_too_long');
}

$dataDir = __DIR__ . '/data';
if (!is_dir($dataDir)) {
  mkdir($dataDir, 0750, true);
}

$rateFile = $dataDir . '/ratelimit.json';
$ip = $_SERVER['REMOTE_ADDR'] ?? 'unknown';
$now = time();
$window = 3600;
$limit = 6;

$rateHandle = fopen($rateFile, 'c+');
if (!$rateHandle) {
  fail(500, 'storage_unavailable');
}
flock($rateHandle, LOCK_EX);
$contents = stream_get_contents($rateHandle);
$rateData = $contents ? json_decode($contents, true) : [];
if (!is_array($rateData)) {
  $rateData = [];
}
$entries = $rateData[$ip] ?? [];
$entries = array_values(array_filter($entries, function($ts) use ($now, $window) {
  return $ts >= ($now - $window);
}));
if (count($entries) >= $limit) {
  flock($rateHandle, LOCK_UN);
  fclose($rateHandle);
  fail(429, 'rate_limited');
}
$entries[] = $now;
$rateData[$ip] = $entries;
rewind($rateHandle);
ftruncate($rateHandle, 0);
fwrite($rateHandle, json_encode($rateData, JSON_PRETTY_PRINT));
flock($rateHandle, LOCK_UN);
fclose($rateHandle);

$file = $dataDir . '/contact_messages.csv';
$handle = fopen($file, 'a');
if (!$handle) {
  fail(500, 'storage_unavailable');
}
flock($handle, LOCK_EX);
fputcsv($handle, [gmdate('c'), $name, $email, $message, $ip]);
flock($handle, LOCK_UN);
fclose($handle);

echo json_encode(['ok' => true]);
"""
    (SITE_DIR / "contact.php").write_text(php, encoding="utf-8")


def _write_data_protection() -> None:
    data_dir = SITE_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    htaccess = """Require all denied
<FilesMatch \\.(csv|json)$>
  Require all denied
</FilesMatch>
"""
    (data_dir / ".htaccess").write_text(htaccess, encoding="utf-8")


def build_site() -> None:
    pages = _read_control()
    site = _read_site_config()
    links = _read_links()
    posts = _read_blog_posts()
    digests = _read_digests()
    meta_description = site.get("meta_description", "")
    layout_variant = (site.get("layout_variant") or "standard").strip().lower()
    if layout_variant not in {"standard", "linkhub", "profile", "mescia_landing", "archive"}:
        layout_variant = "standard"
    show_digest_home = str(site.get("show_digest_home", "")).strip().lower() in {"1", "true", "yes", "on"}

    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    _write_site_assets(site)
    _write_subscribe_php()
    _write_contact_php()
    _write_data_protection()

    for slug, page in sorted(pages.items(), key=lambda item: item[1].get("order", 0)):
        current_path = _page_output_path(slug)
        css_href = _rel_link(current_path, Path("assets/css/style.css"))
        js_href = _rel_link(current_path, Path("assets/js/main.js"))
        extra_css = ""
        if slug == "" and layout_variant == "mescia_landing":
            extra_css = f'<link rel="stylesheet" href="{_escape(_rel_link(current_path, Path("assets/css/landing.css")))}" />'

        header = _render_header(slug, pages, current_path)
        footer = _render_footer(site, pages, current_path, links)
        sections = list(page["sections"])
        if slug == "" and not show_digest_home:
            sections = [section for section in sections if section.get("kind") != "digest_list"]
        hero = next((section for section in sections if section.get("kind") == "hero"), sections[0] if sections else {})
        hero_heading = hero.get("title") or page["title"]
        hero_body = _render_markdown(_read_block(hero.get("source_md", "")))
        hero_cta_text = _escape(hero.get("cta_text", ""))
        hero_cta_url = _resolve_cta_url(hero.get("cta_url", ""), pages, current_path)
        hero_cta = ""
        if hero_cta_text and hero_cta_url:
            hero_cta = f"<a class=\"button\" href=\"{_escape(hero_cta_url)}\">{hero_cta_text}</a>"
        hero_image_src = _resolve_image_src(hero.get("hero_image", ""), current_path)

        content_sections = [section for section in sections if section is not hero]
        sections_html = "".join(
            _render_section(section, current_path, pages, digests)
            for section in content_sections
        )

        newsletter_html = ""
        if slug in {"", "contact", "digest"}:
            newsletter_html = _render_newsletter_form(site, current_path)

        overview_html = ""
        if slug == "":
            overview_html = _render_home_overview(pages, current_path)

        blog_index_html = ""
        if slug == "blog":
            blog_index_html = _render_blog_index(posts, current_path)

        digest_index_html = ""
        if slug == "digest":
            digest_index_html = _render_digest_index(digests, current_path)

        contact_links_html = _render_links(links) if slug == "contact" else ""
        page_body_inner = "".join([blog_index_html, digest_index_html, newsletter_html, contact_links_html]).strip()
        page_body_html = ""
        if page_body_inner:
            page_body_html = f"""
      <section class="page-body">
        <div class="content-block reveal">
          {page_body_inner}
        </div>
      </section>"""

        if slug == "":
            if layout_variant == "archive":
                homepage_body = _render_archive_layout(site, pages, current_path, hero_heading, hero_body, sections_html, overview_html, page_body_html)
            elif layout_variant == "linkhub":
                homepage_body = f"""
      <section class="linkhub">
        <div class="linkhub-inner">
          <p class="eyebrow">{_escape(site.get('site_name', 'Artificial Life Institute'))}</p>
          <h1>{_escape(hero_heading)}</h1>
          <p class="subtitle">{_escape(site.get('site_tagline', ''))}</p>
          {_render_paragraphs(site.get('contact_blurb', ''))}
          {_render_linkhub_links(links)}
          {newsletter_html}
        </div>
      </section>
"""
            elif layout_variant == "mescia_landing":
                homepage_body = _render_mescia_landing(site, pages, current_path)
            elif layout_variant == "profile":
                homepage_body = f"""
      <section class="hero">
        <div class="hero-orbit"></div>
        <div class="hero-inner">
          <div>
            <p class="eyebrow">{_escape(site.get('site_name', 'Artificial Life Institute'))}</p>
            <h1>{_escape(hero_heading)}</h1>
            <p class="subtitle">{_escape(site.get('site_tagline', ''))}</p>
            {hero_body}
            <div class="hero-actions">{hero_cta}</div>
          </div>
          <div class="hero-art">
            <figure class="image-frame"><img src="{_escape(hero_image_src)}" alt="{_escape(hero_heading)} image" /></figure>
            <h3>Institute profile</h3>
            <p>{_escape(site.get('contact_blurb', ''))}</p>
          </div>
        </div>
      </section>
      <section class="profile-section">
        <div class="profile-grid">
          <div class="profile-card"><h3>Core questions</h3><p>Placeholder for the institute's core research questions.</p></div>
          <div class="profile-card"><h3>Methods</h3><p>Placeholder for modeling, experimentation, and field integration.</p></div>
          <div class="profile-card"><h3>Community</h3><p>Placeholder for seminars, visitors, and collaborations.</p></div>
        </div>
      </section>
      <section class="profile-section">
        <div class="content-block reveal">
          <h2>Selected outputs</h2>
          <ul class="outputs-list">
            <li>Placeholder output: paper, dataset, or public demonstration.</li>
            <li>Placeholder output: workshop, symposium, or lecture series.</li>
            <li>Placeholder output: open-source tool or platform.</li>
          </ul>
          {newsletter_html}
        </div>
      </section>
"""
            else:
                homepage_body = f"""
      <section class="hero">
        <div class="hero-orbit"></div>
        <div class="hero-inner">
          <div>
            <p class="eyebrow">{_escape(site.get('site_name', 'Artificial Life Institute'))}</p>
            <h1>{_escape(hero_heading)}</h1>
            <p class="subtitle">{_escape(site.get('site_tagline', ''))}</p>
            {hero_body}
            <div class="hero-actions">{hero_cta}</div>
          </div>
          <div class="hero-art">
            <figure class="image-frame"><img src="{_escape(hero_image_src)}" alt="{_escape(hero_heading)} image" /></figure>
            <h3>Dynamic systems, grounded experiments</h3>
            <p>Placeholder for a concise, compelling institute statement.</p>
            <div class="hero-metrics">
              <div><span>12+</span>Active research threads</div>
              <div><span>4</span>Cross-faculty labs</div>
              <div><span>20</span>Years of ALife history</div>
            </div>
          </div>
        </div>
      </section>
      {overview_html}
      {sections_html}
      {page_body_html}
"""
        else:
            homepage_body = f"""
      <section class="hero">
        <div class="hero-orbit"></div>
        <div class="hero-inner">
          <div>
            <p class="eyebrow">{_escape(site.get('site_name', 'Artificial Life Institute'))}</p>
            <h1>{_escape(hero_heading)}</h1>
            <p class="subtitle">{_escape(site.get('site_tagline', ''))}</p>
            {hero_body}
            <div class="hero-actions">{hero_cta}</div>
          </div>
          <div class="hero-art">
            <figure class="image-frame"><img src="{_escape(hero_image_src)}" alt="{_escape(hero_heading)} image" /></figure>
            <h3>Dynamic systems, grounded experiments</h3>
            <p>Placeholder for a concise, compelling institute statement.</p>
            <div class="hero-metrics">
              <div><span>12+</span>Active research threads</div>
              <div><span>4</span>Cross-faculty labs</div>
              <div><span>20</span>Years of ALife history</div>
            </div>
          </div>
        </div>
      </section>
      {overview_html}
      {sections_html}
      {page_body_html}
"""

        doc = f"""<!doctype html>
<html lang=\"en\">
{_render_head(page['title'], css_href, meta_description, extra_css=extra_css)}
<body data-newsletter-mode="{_escape(site.get('newsletter_mode', 'local'))}" data-newsletter-url="{_escape(site.get('newsletter_provider_url', ''))}">
  <div class="page-shell">
    {header}
    <main>
      {homepage_body}
    </main>
    {footer}
  </div>
  <script src="{_escape(js_href)}"></script>
  {f'<script src="{_escape(_rel_link(current_path, Path("assets/js/landing.js")))}"></script>' if slug == "" and layout_variant == "mescia_landing" else ''}
</body>
</html>
"""
        output_path = SITE_DIR / current_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(doc, encoding="utf-8")

    for post in posts:
        _render_blog_post(post, pages)

    for digest in digests:
        _render_digest_page(digest, pages, site, links)


if __name__ == "__main__":
    build_site()
