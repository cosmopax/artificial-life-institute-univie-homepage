#!/usr/bin/env python3
from __future__ import annotations

import csv
import html
import shutil
from pathlib import Path
from typing import Iterable

BASE_DIR = Path(__file__).resolve().parent
CONTENT_PATH = BASE_DIR / "content" / "content.csv"
SITE_DIR = BASE_DIR / "site"
CSS_DIR = SITE_DIR / "assets" / "css"
JS_DIR = SITE_DIR / "assets" / "js"
IMAGE_SRC_DIR = BASE_DIR / "assets" / "images"
IMAGE_SITE_DIR = SITE_DIR / "assets" / "images"

SECTION_ORDER = ["hero", "about", "research", "projects", "contact"]


def _split_paragraphs(text: str) -> list[str]:
    text = (text or "").replace("\\n", "\n")
    return [chunk.strip() for chunk in text.split("\n") if chunk.strip()]


def _split_bullets(text: str) -> list[str]:
    if not text:
        return []
    return [item.strip() for item in text.split("|") if item.strip()]


def _escape(text: str) -> str:
    return html.escape(text, quote=True)


def _render_paragraphs(paragraphs: Iterable[str]) -> str:
    return "\n".join(f"<p>{_escape(p)}</p>" for p in paragraphs)


def _render_bullets(items: Iterable[str]) -> str:
    items = list(items)
    if not items:
        return ""
    li = "\n".join(f"<li>{_escape(item)}</li>" for item in items)
    return f"<ul>\n{li}\n</ul>"


def _render_contact_list(items: Iterable[str]) -> str:
    items = list(items)
    if not items:
        return ""
    rendered = []
    for item in items:
        if "@" in item:
            safe = _escape(item)
            rendered.append(f"<li><a href=\"mailto:{safe}\">{safe}</a></li>")
        else:
            rendered.append(f"<li>{_escape(item)}</li>")
    return "<ul>\n" + "\n".join(rendered) + "\n</ul>"


def _render_image(src: str, alt: str, class_name: str = "image-frame") -> str:
    image_src = src or "placeholder.svg"
    safe_src = _escape(image_src)
    safe_alt = _escape(alt)
    return (
        f"<figure class=\"{class_name}\">"
        f"<img src=\"assets/images/{safe_src}\" alt=\"{safe_alt}\" />"
        f"</figure>"
    )


def _render_newsletter(data: dict[str, str]) -> str:
    text = data.get("newsletter_text", "")
    action = data.get("newsletter_action", "")
    placeholder = data.get("newsletter_placeholder", "Your email")
    if not (text or action):
        return ""
    note = f"<p class=\"newsletter-text\">{_escape(text)}</p>" if text else ""
    action_attr = _escape(action) if action else "#"
    placeholder_attr = _escape(placeholder)
    return (
        "<div class=\"newsletter\">"
        "<h3>Newsletter</h3>"
        f"{note}"
        f"<form class=\"newsletter-form\" action=\"{action_attr}\" method=\"post\" target=\"_blank\" rel=\"noopener\">"
        f"<input type=\"email\" name=\"email\" placeholder=\"{placeholder_attr}\" required />"
        "<button type=\"submit\" class=\"button\">Subscribe</button>"
        "</form>"
        "</div>"
    )


def load_content() -> dict[str, dict[str, str]]:
    if not CONTENT_PATH.exists():
        raise SystemExit(f"Missing content source: {CONTENT_PATH}")
    sections: dict[str, dict[str, str]] = {}
    with CONTENT_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            section = (row.get("section") or "").strip()
            if not section:
                continue
            sections[section] = {key: (value or "").strip() for key, value in row.items()}
    return sections


def _copy_images() -> None:
    if not IMAGE_SRC_DIR.exists():
        return
    if IMAGE_SITE_DIR.exists():
        shutil.rmtree(IMAGE_SITE_DIR)
    shutil.copytree(IMAGE_SRC_DIR, IMAGE_SITE_DIR)


def _render_head(title: str) -> str:
    return f"""<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>{title}</title>
    <meta name=\"description\" content=\"Artificial Life Institute at the University of Vienna\" />
    <link rel=\"stylesheet\" href=\"assets/css/style.css\" />
  </head>"""


def _render_header(current_page: str, nav_items: Iterable[tuple[str, str, str]]) -> str:
    nav_links = "\n".join(
        f"<a href=\"{href}\" class=\"{ 'active' if current_page == key else '' }\">{_escape(label)}</a>"
        for key, href, label in nav_items
    )
    return (
        "<header class=\"site-header\">"
        "<a class=\"logo\" href=\"index.html\">ALI</a>"
        f"<nav class=\"nav\">{nav_links}</nav>"
        "<a class=\"cta\" href=\"contact.html\">Get in touch</a>"
        "</header>"
    )


def _render_footer() -> str:
    return (
        "<footer class=\"site-footer\">"
        "<p>Artificial Life Institute · University of Vienna</p>"
        "<p>https://artificial-life-institute.univie.ac.at</p>"
        "</footer>"
    )


def build_site() -> None:
    sections = load_content()
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    CSS_DIR.mkdir(parents=True, exist_ok=True)
    JS_DIR.mkdir(parents=True, exist_ok=True)
    _copy_images()

    hero = sections.get("hero", {})
    hero_title = _escape(hero.get("title", ""))
    hero_subtitle = _escape(hero.get("subtitle", ""))
    hero_body = _render_paragraphs(_split_paragraphs(hero.get("body", "")))
    hero_cta_text = _escape(hero.get("cta_text", ""))
    hero_cta_href = _escape(hero.get("cta_href", ""))
    hero_cta = ""
    if hero_cta_text and hero_cta_href:
        hero_cta = f"<a class=\"button\" href=\"{hero_cta_href}\">{hero_cta_text}</a>"

    nav_items = [("home", "index.html", "Home")]
    for section_id in SECTION_ORDER:
        if section_id == "hero":
            continue
        if section_id in sections:
            nav_items.append((section_id, f"{section_id}.html", sections[section_id].get("title", section_id.title())))

    overview_cards = []
    for section_id in SECTION_ORDER:
        if section_id in ("hero",):
            continue
        data = sections.get(section_id, {})
        title = _escape(data.get("title", ""))
        teaser = _split_paragraphs(data.get("body", ""))
        snippet = _escape(teaser[0]) if teaser else ""
        image_html = _render_image(data.get("image", ""), f"{title} image", "card-image")
        overview_cards.append(
            "<a class=\"card\" href=\"{href}\">{image}<div class=\"card-body\"><h3>{title}</h3><p>{snippet}</p></div></a>".format(
                href=f"{section_id}.html",
                image=image_html,
                title=title,
                snippet=snippet,
            )
        )
    overview_html = "\n".join(overview_cards)

    hero_image = _render_image(hero.get("image", ""), "Institute overview", "hero-image")

    index_doc = f"""<!doctype html>
<html lang=\"en\">
  {_render_head(hero_title or 'Artificial Life Institute')}
  <body>
    <div class=\"grain\"></div>
    {_render_header('home', nav_items)}

    <main>
      <section class=\"hero\">
        <div class=\"hero-inner\">
          <div class=\"hero-copy\">
            <p class=\"eyebrow\">Artificial Life Institute</p>
            <h1>{hero_title}</h1>
            <p class=\"subtitle\">{hero_subtitle}</p>
            {hero_body}
            <div class=\"hero-actions\">{hero_cta}</div>
          </div>
          <div class=\"hero-card\">
            {hero_image}
            <h3>Dynamic systems, grounded experiments</h3>
            <p>We prototype lifelike behaviors in simulation and in the lab, translating emergent insights into robust scientific instruments.</p>
            <div class=\"hero-metrics\">
              <div><span>12+</span>Active research threads</div>
              <div><span>4</span>Cross-faculty labs</div>
              <div><span>20</span>Years of ALife history</div>
            </div>
          </div>
        </div>
        <div class=\"hero-swoosh\"></div>
      </section>

      <section class=\"overview reveal\">
        <div class=\"overview-inner\">
          <h2>Explore the institute</h2>
          <div class=\"card-grid\">{overview_html}</div>
        </div>
      </section>
    </main>

    {_render_footer()}
    <script src=\"assets/js/main.js\"></script>
  </body>
</html>
"""

    (SITE_DIR / "index.html").write_text(index_doc, encoding="utf-8")

    for section_id in SECTION_ORDER:
        if section_id == "hero":
            continue
        data = sections.get(section_id, {})
        title = _escape(data.get("title", ""))
        subtitle = _escape(data.get("subtitle", ""))
        body = _render_paragraphs(_split_paragraphs(data.get("body", "")))
        bullets = _split_bullets(data.get("bullets", ""))
        cta_text = _escape(data.get("cta_text", ""))
        cta_href = _escape(data.get("cta_href", ""))
        cta = ""
        if cta_text and cta_href:
            cta = f"<a class=\"button ghost\" href=\"{cta_href}\">{cta_text}</a>"

        if section_id == "contact":
            bullet_html = _render_contact_list(bullets)
        else:
            bullet_html = _render_bullets(bullets)

        subtitle_html = f"<p class=\"subtitle\">{subtitle}</p>" if subtitle else ""
        image_html = _render_image(data.get("image", ""), f"{title} image", "page-image")
        newsletter_html = _render_newsletter(data) if section_id == "contact" else ""

        page_doc = f"""<!doctype html>
<html lang=\"en\">
  {_render_head(title or 'Artificial Life Institute')}
  <body>
    <div class=\"grain\"></div>
    {_render_header(section_id, nav_items)}

    <main>
      <section class=\"page-hero\">
        <div class=\"page-hero-inner\">
          <div class=\"page-copy\">
            <h1>{title}</h1>
            {subtitle_html}
            {body}
            {cta}
          </div>
          {image_html}
        </div>
      </section>

      <section class=\"page-content reveal\">
        <div class=\"page-content-inner\">
          {bullet_html}
          {newsletter_html}
          <a class=\"button ghost\" href=\"index.html\">Back to home</a>
        </div>
      </section>
    </main>

    {_render_footer()}
    <script src=\"assets/js/main.js\"></script>
  </body>
</html>
"""

        (SITE_DIR / f"{section_id}.html").write_text(page_doc, encoding="utf-8")

    (CSS_DIR / "style.css").write_text(_build_css(), encoding="utf-8")
    (JS_DIR / "main.js").write_text(_build_js(), encoding="utf-8")



def _build_css() -> str:
    return """
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=Work+Sans:wght@300;400;500;600&display=swap');

:root {
  color-scheme: only light;
  --bordeaux: #7a101f;
  --bordeaux-dark: #4c0913;
  --ink: #111111;
  --paper: #f8f2f0;
  --fog: #f3e8e6;
  --accent: #c84b31;
  --shadow: rgba(17, 17, 17, 0.15);
  --radius: 18px;
  --max-width: 1100px;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: 'Work Sans', sans-serif;
  color: var(--ink);
  background: radial-gradient(circle at top, #fff6f2 0%, var(--paper) 45%, var(--fog) 100%);
  line-height: 1.6;
}

a {
  color: inherit;
  text-decoration: none;
}

img {
  max-width: 100%;
  display: block;
  border-radius: 16px;
}

.grain {
  position: fixed;
  inset: 0;
  background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 120 120"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2" stitchTiles="stitch"/></filter><rect width="120" height="120" filter="url(%23n)" opacity="0.04"/></svg>');
  pointer-events: none;
  z-index: 1;
}

.site-header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 6vw;
  background: rgba(248, 242, 240, 0.95);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(122, 16, 31, 0.2);
}

.logo {
  font-family: 'Cormorant Garamond', serif;
  font-weight: 700;
  font-size: 24px;
  letter-spacing: 0.1em;
  color: var(--bordeaux);
}

.nav {
  display: flex;
  gap: 22px;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.nav a {
  position: relative;
  padding-bottom: 6px;
}

.nav a::after {
  content: '';
  position: absolute;
  left: 0;
  bottom: 0;
  width: 100%;
  height: 2px;
  background: var(--bordeaux);
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
  padding: 10px 20px;
  border-radius: 999px;
  background: var(--ink);
  color: #fff;
  font-size: 13px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

main {
  position: relative;
  z-index: 2;
}

.hero {
  padding: 120px 6vw 80px;
  position: relative;
  overflow: hidden;
}

.hero-inner {
  max-width: var(--max-width);
  margin: 0 auto;
  display: grid;
  gap: 48px;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  align-items: center;
}

.hero-copy h1 {
  font-family: 'Cormorant Garamond', serif;
  font-size: clamp(40px, 5vw, 76px);
  margin: 10px 0 12px;
  color: var(--bordeaux);
}

.eyebrow {
  letter-spacing: 0.3em;
  text-transform: uppercase;
  font-size: 12px;
  color: var(--bordeaux-dark);
  margin: 0;
}

.subtitle {
  font-size: 18px;
  color: var(--bordeaux-dark);
  margin-top: 0;
}

.hero-actions {
  margin-top: 24px;
}

.button {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 12px 22px;
  border-radius: 999px;
  background: var(--bordeaux);
  color: #fff;
  font-size: 14px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  box-shadow: 0 12px 24px var(--shadow);
  border: none;
  cursor: pointer;
}

.button.ghost {
  background: transparent;
  border: 1px solid var(--bordeaux);
  color: var(--bordeaux);
}

.hero-card {
  background: #fff;
  border-radius: var(--radius);
  padding: 24px;
  box-shadow: 0 24px 50px var(--shadow);
  border: 1px solid rgba(122, 16, 31, 0.1);
  display: grid;
  gap: 16px;
}

.hero-card h3 {
  margin: 0;
  font-family: 'Cormorant Garamond', serif;
  font-size: 26px;
  color: var(--ink);
}

.hero-image img {
  border-radius: 14px;
}

.hero-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-top: 8px;
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.hero-metrics span {
  display: block;
  font-size: 24px;
  color: var(--bordeaux);
  font-weight: 600;
}

.hero-swoosh {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 70% 30%, rgba(122, 16, 31, 0.15), transparent 55%),
    radial-gradient(circle at 20% 80%, rgba(200, 75, 49, 0.12), transparent 50%);
  z-index: -1;
}

.overview {
  padding: 40px 6vw 80px;
}

.overview-inner {
  max-width: var(--max-width);
  margin: 0 auto;
}

.overview-inner h2 {
  font-family: 'Cormorant Garamond', serif;
  font-size: clamp(28px, 3.5vw, 40px);
  color: var(--bordeaux);
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 20px;
  margin-top: 24px;
}

.card {
  background: #fff;
  border-radius: var(--radius);
  border: 1px solid rgba(122, 16, 31, 0.08);
  box-shadow: 0 16px 32px var(--shadow);
  overflow: hidden;
  display: grid;
  gap: 0;
}

.card-image img {
  border-radius: 0;
}

.card-body {
  padding: 18px 20px 22px;
}

.card h3 {
  margin: 0 0 8px;
  font-family: 'Cormorant Garamond', serif;
  font-size: 22px;
  color: var(--bordeaux);
}

.page-hero {
  padding: 120px 6vw 40px;
}

.page-hero-inner {
  max-width: var(--max-width);
  margin: 0 auto;
  display: grid;
  gap: 32px;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  align-items: center;
}

.page-image {
  align-self: center;
}

.page-copy h1 {
  font-family: 'Cormorant Garamond', serif;
  font-size: clamp(36px, 4.5vw, 60px);
  color: var(--bordeaux);
  margin-top: 0;
}

.page-content {
  padding: 20px 6vw 80px;
}

.page-content-inner {
  max-width: var(--max-width);
  margin: 0 auto;
  background: #fff;
  border-radius: var(--radius);
  padding: clamp(24px, 4vw, 44px);
  box-shadow: 0 20px 40px var(--shadow);
  border: 1px solid rgba(122, 16, 31, 0.08);
  display: grid;
  gap: 20px;
}

.page-content-inner ul {
  padding-left: 18px;
}

.newsletter {
  border-top: 1px solid rgba(122, 16, 31, 0.15);
  padding-top: 16px;
}

.newsletter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 12px;
}

.newsletter-form input {
  flex: 1 1 220px;
  padding: 12px 14px;
  border-radius: 999px;
  border: 1px solid rgba(17, 17, 17, 0.2);
  font-size: 14px;
}

.site-footer {
  padding: 60px 6vw 80px;
  text-align: center;
  color: rgba(17, 17, 17, 0.7);
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

@media (max-width: 820px) {
  .site-header {
    position: static;
    flex-direction: column;
    align-items: flex-start;
  }

  .nav {
    flex-wrap: wrap;
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

  .hero-card {
    order: -1;
  }
}
""".lstrip()


def _build_js() -> str:
    return """
const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

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

function revealOnScroll() {
  if (prefersReduced) {
    document.querySelectorAll('.reveal').forEach((el) => el.classList.add('is-visible'));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.2 }
  );

  document.querySelectorAll('.reveal').forEach((el) => observer.observe(el));
}

window.addEventListener('DOMContentLoaded', () => {
  smoothScroll();
  revealOnScroll();
});
""".lstrip()


if __name__ == "__main__":
    build_site()
