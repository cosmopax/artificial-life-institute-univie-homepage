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
from typing import Iterable

BASE_DIR = Path(__file__).resolve().parents[1]
CONTENT_DIR = BASE_DIR / "content"
SITE_DIR = BASE_DIR / "site"
ASSETS_DIR = SITE_DIR / "assets"
CSS_DIR = ASSETS_DIR / "css"
JS_DIR = ASSETS_DIR / "js"
IMG_DIR = ASSETS_DIR / "img"
BLOG_DIR = CONTENT_DIR / "blog"
MEDIA_DIR = CONTENT_DIR / "media"

SITE_JSON = CONTENT_DIR / "site.json"
PAGES_CSV = CONTENT_DIR / "pages.csv"
LINKS_CSV = CONTENT_DIR / "links.csv"

PLACEHOLDER_IMAGES = {
    "placeholder-hero.svg": "Warm abstract hero placeholder",
    "placeholder-studio.svg": "Studio placeholder",
    "placeholder-lab.svg": "Lab placeholder",
    "placeholder-portrait.svg": "Portrait placeholder",
    "placeholder-grid.svg": "Project grid placeholder",
}

NAV_SLUGS = ["", "about", "research", "projects", "blog", "contact"]


def _escape(text: str) -> str:
    return html.escape(text or "", quote=True)


def _slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\s-]", "", text or "")
    cleaned = re.sub(r"\s+", "-", cleaned.strip())
    return cleaned.lower() or "post"


def _split_paragraphs(text: str) -> list[str]:
    normalized = (text or "").replace("\\n", "\n").strip()
    if not normalized:
        return []
    chunks = re.split(r"\n\s*\n", normalized)
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _render_paragraphs(text: str) -> str:
    return "\n".join(f"<p>{_escape(p)}</p>" for p in _split_paragraphs(text))


def _read_site_config() -> dict[str, str]:
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


def _rel_link(current_path: Path, target_path: Path) -> str:
    current_dir = current_path.parent.as_posix()
    target = target_path.as_posix()
    rel = os.path.relpath(target, start=current_dir)
    return rel


def _read_pages() -> dict[str, dict[str, object]]:
    if not PAGES_CSV.exists():
        raise SystemExit(f"Missing pages file: {PAGES_CSV}")
    pages: dict[str, dict[str, object]] = {}
    with PAGES_CSV.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            data = {key: (value or "").strip() for key, value in row.items()}
            slug = _normalize_slug(data.get("page_slug", ""))
            order = int(data.get("order") or 0)
            entry = pages.setdefault(
                slug,
                {
                    "title": data.get("page_title") or slug.title() or "Home",
                    "sections": [],
                },
            )
            entry["sections"].append({**data, "order": order, "page_slug": slug})
            if data.get("page_title"):
                entry["title"] = data["page_title"]
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


def _parse_blog_post(path: Path) -> dict[str, str]:
    raw = path.read_text(encoding="utf-8")
    title = ""
    date = ""
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
    slug = _slugify(path.stem)
    return {"title": title, "date": date, "body": body, "slug": slug}


def _read_blog_posts() -> list[dict[str, str]]:
    if not BLOG_DIR.exists():
        return []
    posts = [_parse_blog_post(path) for path in sorted(BLOG_DIR.glob("*.txt"))]
    posts.sort(key=lambda item: item.get("date", ""), reverse=True)
    return posts


def _resolve_cta_url(raw_url: str, pages: dict[str, dict[str, object]], current_path: Path) -> str:
    if not raw_url:
        return ""
    if raw_url.startswith("http") or raw_url.startswith("mailto:") or raw_url.startswith("#"):
        return raw_url
    slug = _normalize_slug(raw_url)
    if slug in pages:
        return _rel_link(current_path, _page_output_path(slug))
    return raw_url


def _render_newsletter_form(site: dict[str, str], current_path: Path) -> str:
    mode = (site.get("newsletter_mode") or "local").strip()
    provider_url = (site.get("newsletter_provider_url") or "").strip()
    if mode == "local" or not provider_url:
        endpoint = _rel_link(current_path, Path("subscribe.php"))
    else:
        endpoint = provider_url
    return f"""
<div class=\"newsletter\" id=\"newsletter\">
  <div>
    <h3>Newsletter</h3>
    <p>Subscribe for institute updates, events, and research highlights.</p>
  </div>
  <form class=\"newsletter-form\" data-newsletter-form action=\"{_escape(endpoint)}\" method=\"post\">
    <label class=\"sr-only\" for=\"newsletter-email\">Email</label>
    <input id=\"newsletter-email\" name=\"email\" type=\"email\" placeholder=\"you@example.org\" required />
    <button class=\"button\" type=\"submit\">Subscribe</button>
    <p class=\"form-status\" aria-live=\"polite\"></p>
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


def _render_head(title: str, css_href: str, description: str) -> str:
    return f"""
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{_escape(title)}</title>
  <meta name=\"description\" content=\"{_escape(description)}\" />
  <link rel=\"stylesheet\" href=\"{_escape(css_href)}\" />
</head>
"""


def _render_header(current_slug: str, pages: dict[str, dict[str, object]], current_path: Path) -> str:
    nav_links = []
    for slug in NAV_SLUGS:
        if slug not in pages:
            continue
        title = pages[slug]["title"]
        href = _rel_link(current_path, _page_output_path(slug))
        active = "active" if slug == current_slug else ""
        nav_links.append(f"<a class=\"{active}\" href=\"{_escape(href)}\">{_escape(title)}</a>")
    cta_href = _rel_link(current_path, _page_output_path("contact")) if "contact" in pages else "#"
    return f"""
<header class=\"site-header\">
  <a class=\"logo\" href=\"{_escape(_rel_link(current_path, _page_output_path("")))}\">ALI</a>
  <nav class=\"nav\">{''.join(nav_links)}</nav>
  <a class=\"cta\" href=\"{_escape(cta_href)}\">Get in touch</a>
</header>
"""


def _render_footer(site: dict[str, str], pages: dict[str, dict[str, object]], current_path: Path, links: list[dict[str, str]]) -> str:
    footer_links = []
    for slug in ("privacy", "imprint"):
        if slug in pages:
            href = _rel_link(current_path, _page_output_path(slug))
            footer_links.append(f"<a href=\"{_escape(href)}\">{_escape(pages[slug]['title'])}</a>")
    links_html = "".join(footer_links)
    digital_html = _render_links(links)
    address = _escape(site.get("address", ""))
    note = _escape(site.get("footer_note", ""))
    domain = _escape(site.get("domain", ""))
    return f"""
<footer class=\"site-footer\">
  <div class=\"footer-grid\">
    <div>
      <p class=\"footer-title\">Artificial Life Institute</p>
      <p>{address}</p>
      <p>{note}</p>
      <p><a href=\"{domain}\">{domain}</a></p>
    </div>
    <div>
      <p class=\"footer-title\">Digital presence</p>
      {digital_html}
    </div>
    <div>
      <p class=\"footer-title\">Legal</p>
      <div class=\"footer-links\">{links_html}</div>
    </div>
  </div>
</footer>
"""


def _render_section(section: dict[str, str], current_path: Path, pages: dict[str, dict[str, object]]) -> str:
    heading = _escape(section.get("heading", ""))
    body = _render_paragraphs(section.get("body", ""))
    cta_text = _escape(section.get("cta_text", ""))
    raw_cta_url = section.get("cta_url", "")
    cta_url = _resolve_cta_url(raw_cta_url, pages, current_path)
    cta = ""
    if cta_text and cta_url:
        cta = f"<a class=\"button ghost\" href=\"{_escape(cta_url)}\">{cta_text}</a>"
    image_name = section.get("hero_image", "") or "placeholder-hero.svg"
    image_src = _rel_link(current_path, Path("assets/img") / image_name)
    image = f"<figure class=\"image-frame\"><img src=\"{_escape(image_src)}\" alt=\"{heading} image\" /></figure>"
    section_id = _escape(section.get("section_id", ""))
    return f"""
<section class=\"content-section\" id=\"{section_id}\">
  <div class=\"content-grid\">
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


def _render_home_overview(pages: dict[str, dict[str, object]], current_path: Path) -> str:
    cards = []
    for slug in NAV_SLUGS:
        if slug in ("", "blog", "contact"):
            continue
        if slug not in pages:
            continue
        title = pages[slug]["title"]
        target = _rel_link(current_path, _page_output_path(slug))
        cards.append(
            f"<a class=\"card\" href=\"{_escape(target)}\"><h3>{_escape(title)}</h3><p>Placeholder summary for { _escape(title) }.</p></a>"
        )
    return "<div class=\"card-grid\">" + "".join(cards) + "</div>"


def _render_blog_index(posts: list[dict[str, str]], current_path: Path) -> str:
    if not posts:
        return "<p>No posts yet. Add a file to content/blog/ to publish the first update.</p>"
    cards = []
    for post in posts:
        target = _rel_link(current_path, Path("blog") / post["slug"] / "index.html")
        excerpt = _split_paragraphs(post.get("body", ""))
        teaser = excerpt[0] if excerpt else ""
        cards.append(
            """
<article class=\"post-card\">
  <p class=\"post-date\">{date}</p>
  <h3><a href=\"{href}\">{title}</a></h3>
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


def _render_blog_post(post: dict[str, str], pages: dict[str, dict[str, object]]) -> None:
    slug = post["slug"]
    current_path = Path("blog") / slug / "index.html"
    css_href = _rel_link(current_path, Path("assets/css/style.css"))
    header = _render_header("blog", pages, current_path)
    footer = _render_footer(_read_site_config(), pages, current_path, _read_links())
    back_link = _rel_link(current_path, Path("blog/index.html"))
    body_html = _render_paragraphs(post.get("body", ""))
    doc = f"""<!doctype html>
<html lang=\"en\">
{_render_head(post.get('title', ''), css_href, _read_site_config().get('meta_description', ''))}
<body data-newsletter-mode=\"{_escape(_read_site_config().get('newsletter_mode', 'local'))}\" data-newsletter-url=\"{_escape(_read_site_config().get('newsletter_provider_url', ''))}\">
  <div class=\"page-shell\">
    {header}
    <main>
      <section class=\"page-hero\">
        <div class=\"page-hero-inner\">
          <p class=\"eyebrow\">Institute Blog</p>
          <h1>{_escape(post.get('title', ''))}</h1>
          <p class=\"post-date\">{_escape(post.get('date', ''))}</p>
        </div>
      </section>
      <section class=\"page-body\">
        <div class=\"content-block\">
          {body_html}
          <a class=\"button ghost\" href=\"{_escape(back_link)}\">Back to blog</a>
        </div>
      </section>
    </main>
    {footer}
  </div>
  <script src=\"{_escape(_rel_link(current_path, Path('assets/js/main.js')))}\"></script>
</body>
</html>
"""
    output_path = SITE_DIR / current_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(doc, encoding="utf-8")


def _build_css() -> str:
    return """
:root {
  color-scheme: only light;
  --bordeaux: #6b0f1a;
  --bordeaux-dark: #3e0a11;
  --bordeaux-bright: #a31621;
  --ink: #0f0f0f;
  --paper: #f7f0ee;
  --fog: #efe4e0;
  --accent: #e0b15a;
  --line: rgba(107, 15, 26, 0.18);
  --shadow: rgba(15, 15, 15, 0.18);
  --radius: 20px;
  --max-width: 1120px;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: "Work Sans", "Optima", "Gill Sans", sans-serif;
  background: radial-gradient(circle at top, #fbf5f2 0%, var(--paper) 45%, var(--fog) 100%);
  color: var(--ink);
  line-height: 1.6;
}

a {
  color: inherit;
  text-decoration: none;
}

img {
  max-width: 100%;
  display: block;
}

.page-shell {
  position: relative;
  overflow: hidden;
}

.site-header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
  padding: 18px 6vw;
  background: rgba(247, 240, 238, 0.94);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--line);
}

.logo {
  font-family: "Cormorant Garamond", "Baskerville", "Garamond", serif;
  font-weight: 700;
  font-size: 26px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--bordeaux);
}

.nav {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
  font-size: 13px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.nav a {
  position: relative;
  padding-bottom: 4px;
}

.nav a::after {
  content: "";
  position: absolute;
  left: 0;
  bottom: 0;
  height: 2px;
  width: 100%;
  background: var(--bordeaux-bright);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.3s ease;
}

.nav a:hover::after,
.nav a:focus::after,
.nav a.active::after {
  transform: scaleX(1);
}

.cta {
  padding: 10px 18px;
  border-radius: 999px;
  background: var(--ink);
  color: #fff;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.hero {
  position: relative;
  padding: 110px 6vw 60px;
  overflow: hidden;
}

.hero-inner {
  max-width: var(--max-width);
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 40px;
  align-items: center;
}

.eyebrow {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.3em;
  color: var(--bordeaux-dark);
  margin: 0 0 10px;
}

.hero h1 {
  font-family: "Cormorant Garamond", "Baskerville", "Garamond", serif;
  font-size: clamp(40px, 6vw, 78px);
  margin: 0 0 12px;
  color: var(--bordeaux);
}

.hero .subtitle {
  font-size: 18px;
  color: var(--bordeaux-dark);
}

.hero-art {
  position: relative;
  background: #fff;
  border-radius: var(--radius);
  padding: 26px;
  border: 1px solid var(--line);
  box-shadow: 0 28px 48px var(--shadow);
}

.hero-art::before {
  content: "";
  position: absolute;
  inset: -40% -20% auto auto;
  height: 260px;
  width: 260px;
  background: radial-gradient(circle, rgba(163, 22, 33, 0.45), transparent 70%);
  filter: blur(4px);
  animation: orbit 14s ease-in-out infinite;
  z-index: 0;
}

.hero-art > * {
  position: relative;
  z-index: 1;
}

.hero-orbit {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 70% 20%, rgba(107, 15, 26, 0.18), transparent 40%),
    radial-gradient(circle at 20% 80%, rgba(224, 177, 90, 0.2), transparent 50%);
  animation: pulse 12s ease-in-out infinite;
  z-index: 0;
}

.hero-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.hero-metrics span {
  display: block;
  font-size: 24px;
  font-weight: 600;
  color: var(--bordeaux);
}

.button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border-radius: 999px;
  border: none;
  background: var(--bordeaux);
  color: #fff;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 13px;
  box-shadow: 0 14px 30px var(--shadow);
  cursor: pointer;
}

.button.ghost {
  background: transparent;
  color: var(--bordeaux);
  border: 1px solid var(--bordeaux);
  box-shadow: none;
}

.content-section {
  padding: 20px 6vw 60px;
}

.content-grid {
  max-width: var(--max-width);
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 28px;
  align-items: center;
}

.content-section h2 {
  font-family: "Cormorant Garamond", "Baskerville", "Garamond", serif;
  font-size: clamp(26px, 3.4vw, 40px);
  color: var(--bordeaux);
}

.image-frame {
  background: #fff;
  border-radius: var(--radius);
  padding: 14px;
  border: 1px solid var(--line);
  box-shadow: 0 18px 36px var(--shadow);
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 18px;
}

.card {
  background: #fff;
  border-radius: var(--radius);
  padding: 18px;
  border: 1px solid var(--line);
  box-shadow: 0 16px 30px var(--shadow);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.card:hover {
  transform: translateY(-6px);
  box-shadow: 0 20px 40px var(--shadow);
}

.linkhub {
  padding: 120px 6vw 80px;
}

.linkhub-inner {
  max-width: 720px;
  margin: 0 auto;
  display: grid;
  gap: 24px;
}

.linkhub-links {
  display: grid;
  gap: 14px;
}

.linkhub-link {
  display: block;
  padding: 16px 18px;
  border-radius: var(--radius);
  border: 1px solid var(--line);
  background: #fff;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 13px;
  box-shadow: 0 16px 30px var(--shadow);
}

.linkhub-link.placeholder {
  opacity: 0.7;
}

.profile-section {
  padding: 60px 6vw 80px;
}

.profile-grid {
  max-width: var(--max-width);
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 18px;
}

.profile-card {
  background: #fff;
  border-radius: var(--radius);
  border: 1px solid var(--line);
  padding: 18px;
  box-shadow: 0 16px 30px var(--shadow);
}

.outputs-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 12px;
}

.outputs-list li {
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.9);
}

.page-hero {
  padding: 110px 6vw 40px;
}

.page-hero-inner {
  max-width: var(--max-width);
  margin: 0 auto;
}

.page-hero h1 {
  font-family: "Cormorant Garamond", "Baskerville", "Garamond", serif;
  font-size: clamp(36px, 5vw, 64px);
  color: var(--bordeaux);
  margin: 0 0 10px;
}

.page-body {
  padding: 10px 6vw 80px;
}

.content-block {
  max-width: var(--max-width);
  margin: 0 auto;
  background: #fff;
  border-radius: var(--radius);
  padding: clamp(24px, 4vw, 44px);
  border: 1px solid var(--line);
  box-shadow: 0 18px 36px var(--shadow);
  display: grid;
  gap: 18px;
}

.post-grid {
  display: grid;
  gap: 16px;
}

.post-card {
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 18px;
  background: #fff;
  box-shadow: 0 16px 30px var(--shadow);
}

.post-date {
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--bordeaux-dark);
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.tag {
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid var(--line);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--bordeaux-dark);
}

.tag.primary {
  background: var(--bordeaux);
  color: #fff;
}

.newsletter {
  margin-top: 18px;
  padding: 18px;
  border-radius: var(--radius);
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.9);
  display: grid;
  gap: 10px;
}

.newsletter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.newsletter-form input {
  flex: 1 1 220px;
  padding: 12px 14px;
  border-radius: 999px;
  border: 1px solid var(--line);
  font-size: 14px;
}

.form-status {
  font-size: 13px;
  color: var(--bordeaux-dark);
}

.site-footer {
  padding: 60px 6vw 80px;
  border-top: 1px solid var(--line);
  background: rgba(247, 240, 238, 0.7);
}

.footer-grid {
  max-width: var(--max-width);
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 24px;
}

.footer-title {
  font-family: "Cormorant Garamond", "Baskerville", "Garamond", serif;
  color: var(--bordeaux);
  font-size: 18px;
  margin-bottom: 8px;
}

.footer-links {
  display: grid;
  gap: 8px;
}

.reveal {
  opacity: 0;
  transform: translateY(18px);
  transition: opacity 0.6s ease, transform 0.6s ease;
}

.reveal.is-visible {
  opacity: 1;
  transform: translateY(0);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
}

@keyframes orbit {
  0% { transform: translate3d(0, 0, 0); }
  50% { transform: translate3d(-30px, 20px, 0); }
  100% { transform: translate3d(0, 0, 0); }
}

@keyframes pulse {
  0% { opacity: 0.7; }
  50% { opacity: 1; }
  100% { opacity: 0.7; }
}

@media (max-width: 860px) {
  .site-header {
    position: static;
    flex-direction: column;
    align-items: flex-start;
  }

  .cta {
    align-self: stretch;
    text-align: center;
  }
}

@media (max-width: 600px) {
  .hero {
    padding-top: 80px;
  }

  .hero-inner {
    gap: 24px;
  }
}
""".lstrip()


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
  form.addEventListener('submit', async (event) => {
    if (mode !== 'local' && !providerUrl) return;
    event.preventDefault();
    const emailInput = form.querySelector('input[name="email"]');
    const email = emailInput ? emailInput.value.trim() : '';
    if (!email) {
      status.textContent = 'Please enter a valid email.';
      return;
    }
    const endpoint = mode === 'local' || !providerUrl ? form.getAttribute('action') : providerUrl;
    if (!endpoint) {
      status.textContent = 'Newsletter endpoint is not configured.';
      return;
    }
    status.textContent = 'Submitting...';
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ email })
      });
      const payload = await response.json().catch(() => ({}));
      if (response.ok && payload.ok) {
        status.textContent = 'Thanks for subscribing.';
        form.reset();
      } else {
        status.textContent = payload.error || 'Subscription failed. Please try again.';
      }
    } catch (error) {
      status.textContent = 'Subscription failed. Please try again.';
    }
  });
}

window.addEventListener('DOMContentLoaded', () => {
  revealOnScroll();
  smoothScroll();
  setupNewsletter();
});
""".lstrip()


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


def _write_site_assets() -> None:
    CSS_DIR.mkdir(parents=True, exist_ok=True)
    JS_DIR.mkdir(parents=True, exist_ok=True)
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    (CSS_DIR / "style.css").write_text(_build_css(), encoding="utf-8")
    (JS_DIR / "main.js").write_text(_build_js(), encoding="utf-8")
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

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
  http_response_code(405);
  echo json_encode(['ok' => false, 'error' => 'method_not_allowed']);
  exit;
}

$email = trim($_POST['email'] ?? '');
if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
  http_response_code(400);
  echo json_encode(['ok' => false, 'error' => 'invalid_email']);
  exit;
}

$dataDir = __DIR__ . '/data';
if (!is_dir($dataDir)) {
  mkdir($dataDir, 0750, true);
}

$file = $dataDir . '/newsletter_signups.csv';
$timestamp = gmdate('c');
$line = $timestamp . ',' . str_replace(["\n", "\r"], '', $email) . "\n";

$handle = fopen($file, 'a');
if (!$handle) {
  http_response_code(500);
  echo json_encode(['ok' => false, 'error' => 'storage_unavailable']);
  exit;
}

flock($handle, LOCK_EX);
fwrite($handle, $line);
flock($handle, LOCK_UN);
fclose($handle);

echo json_encode(['ok' => true]);
"""
    (SITE_DIR / "subscribe.php").write_text(php, encoding="utf-8")
    data_dir = SITE_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / ".htaccess").write_text("Require all denied\n", encoding="utf-8")


def build_site() -> None:
    pages = _read_pages()
    site = _read_site_config()
    links = _read_links()
    posts = _read_blog_posts()
    meta_description = site.get("meta_description", "")
    layout_variant = (site.get("layout_variant") or "standard").strip().lower()
    if layout_variant not in {"standard", "linkhub", "profile"}:
        layout_variant = "standard"

    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    _write_site_assets()
    _write_subscribe_php()

    for slug, page in pages.items():
        current_path = _page_output_path(slug)
        css_href = _rel_link(current_path, Path("assets/css/style.css"))
        js_href = _rel_link(current_path, Path("assets/js/main.js"))
        header = _render_header(slug, pages, current_path)
        footer = _render_footer(site, pages, current_path, links)
        sections = page["sections"]
        hero = sections[0] if sections else {}
        hero_heading = hero.get("heading") or page["title"]
        hero_body = _render_paragraphs(hero.get("body", ""))
        hero_cta_text = _escape(hero.get("cta_text", ""))
        hero_cta_url = _resolve_cta_url(hero.get("cta_url", ""), pages, current_path)
        hero_cta = ""
        if hero_cta_text and hero_cta_url:
            hero_cta = f"<a class=\"button\" href=\"{_escape(hero_cta_url)}\">{hero_cta_text}</a>"
        hero_image_name = hero.get("hero_image") or "placeholder-hero.svg"
        hero_image_src = _rel_link(current_path, Path("assets/img") / hero_image_name)

        sections_html = "".join(
            _render_section(section, current_path, pages)
            for section in sections[1:]
        )

        newsletter_html = ""
        if slug in {"", "contact"}:
            newsletter_html = _render_newsletter_form(site, current_path)

        overview_html = ""
        if slug == "":
            overview_html = _render_home_overview(pages, current_path)

        blog_index_html = ""
        if slug == "blog":
            blog_index_html = _render_blog_index(posts, current_path)

        contact_links_html = _render_links(links) if slug == "contact" else ""
        page_body_inner = "".join([blog_index_html, newsletter_html, contact_links_html]).strip()
        page_body_html = ""
        if page_body_inner:
            page_body_html = f"""
      <section class=\"page-body\">
        <div class=\"content-block reveal\">
          {page_body_inner}
        </div>
      </section>"""

        if slug == "":
            if layout_variant == "linkhub":
                homepage_body = f"""
      <section class=\"linkhub\">
        <div class=\"linkhub-inner\">
          <p class=\"eyebrow\">{_escape(site.get('site_name', 'Artificial Life Institute'))}</p>
          <h1>{_escape(hero_heading)}</h1>
          <p class=\"subtitle\">{_escape(site.get('site_tagline', ''))}</p>
          {_render_paragraphs(site.get('contact_blurb', ''))}
          {_render_linkhub_links(links)}
          {newsletter_html}
        </div>
      </section>
"""
            elif layout_variant == "profile":
                homepage_body = f"""
      <section class=\"hero\">
        <div class=\"hero-orbit\"></div>
        <div class=\"hero-inner\">
          <div>
            <p class=\"eyebrow\">{_escape(site.get('site_name', 'Artificial Life Institute'))}</p>
            <h1>{_escape(hero_heading)}</h1>
            <p class=\"subtitle\">{_escape(site.get('site_tagline', ''))}</p>
            {hero_body}
            <div class=\"hero-actions\">{hero_cta}</div>
          </div>
          <div class=\"hero-art\">
            <figure class=\"image-frame\"><img src=\"{_escape(hero_image_src)}\" alt=\"{_escape(hero_heading)} image\" /></figure>
            <h3>Institute profile</h3>
            <p>{_escape(site.get('contact_blurb', ''))}</p>
          </div>
        </div>
      </section>
      <section class=\"profile-section\">
        <div class=\"profile-grid\">
          <div class=\"profile-card\"><h3>Core questions</h3><p>Placeholder for the institute's core research questions.</p></div>
          <div class=\"profile-card\"><h3>Methods</h3><p>Placeholder for modeling, experimentation, and field integration.</p></div>
          <div class=\"profile-card\"><h3>Community</h3><p>Placeholder for seminars, visitors, and collaborations.</p></div>
        </div>
      </section>
      <section class=\"profile-section\">
        <div class=\"content-block reveal\">
          <h2>Selected outputs</h2>
          <ul class=\"outputs-list\">
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
      <section class=\"hero\">
        <div class=\"hero-orbit\"></div>
        <div class=\"hero-inner\">
          <div>
            <p class=\"eyebrow\">{_escape(site.get('site_name', 'Artificial Life Institute'))}</p>
            <h1>{_escape(hero_heading)}</h1>
            <p class=\"subtitle\">{_escape(site.get('site_tagline', ''))}</p>
            {hero_body}
            <div class=\"hero-actions\">{hero_cta}</div>
          </div>
          <div class=\"hero-art\">
            <figure class=\"image-frame\"><img src=\"{_escape(hero_image_src)}\" alt=\"{_escape(hero_heading)} image\" /></figure>
            <h3>Dynamic systems, grounded experiments</h3>
            <p>Placeholder for a concise, compelling institute statement.</p>
            <div class=\"hero-metrics\">
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
      <section class=\"hero\">
        <div class=\"hero-orbit\"></div>
        <div class=\"hero-inner\">
          <div>
            <p class=\"eyebrow\">{_escape(site.get('site_name', 'Artificial Life Institute'))}</p>
            <h1>{_escape(hero_heading)}</h1>
            <p class=\"subtitle\">{_escape(site.get('site_tagline', ''))}</p>
            {hero_body}
            <div class=\"hero-actions\">{hero_cta}</div>
          </div>
          <div class=\"hero-art\">
            <figure class=\"image-frame\"><img src=\"{_escape(hero_image_src)}\" alt=\"{_escape(hero_heading)} image\" /></figure>
            <h3>Dynamic systems, grounded experiments</h3>
            <p>Placeholder for a concise, compelling institute statement.</p>
            <div class=\"hero-metrics\">
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
{_render_head(page['title'], css_href, meta_description)}
<body data-newsletter-mode=\"{_escape(site.get('newsletter_mode', 'local'))}\" data-newsletter-url=\"{_escape(site.get('newsletter_provider_url', ''))}\">
  <div class=\"page-shell\">
    {header}
    <main>
      {homepage_body}
    </main>
    {footer}
  </div>
  <script src=\"{_escape(js_href)}\"></script>
</body>
</html>
"""
        output_path = SITE_DIR / current_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(doc, encoding="utf-8")

    for post in posts:
        _render_blog_post(post, pages)


if __name__ == "__main__":
    build_site()
