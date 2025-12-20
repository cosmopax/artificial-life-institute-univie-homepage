#!/usr/bin/env python3
from __future__ import annotations

import csv
import html
from pathlib import Path
from typing import Iterable

BASE_DIR = Path(__file__).resolve().parent
CONTENT_PATH = BASE_DIR / "content" / "content.csv"
SITE_DIR = BASE_DIR / "site"
CSS_DIR = SITE_DIR / "assets" / "css"
JS_DIR = SITE_DIR / "assets" / "js"

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


def build_site() -> None:
    sections = load_content()
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    CSS_DIR.mkdir(parents=True, exist_ok=True)
    JS_DIR.mkdir(parents=True, exist_ok=True)

    nav_links = "\n".join(
        f"<a href=\"#{name}\">{_escape(sections.get(name, {}).get('title', name.title()))}</a>"
        for name in SECTION_ORDER
        if name in sections
    )

    hero = sections.get("hero", {})
    hero_title = _escape(hero.get("title", ""))
    hero_subtitle = _escape(hero.get("subtitle", ""))
    hero_body = _render_paragraphs(_split_paragraphs(hero.get("body", "")))
    hero_cta_text = _escape(hero.get("cta_text", ""))
    hero_cta_href = _escape(hero.get("cta_href", ""))
    hero_cta = ""
    if hero_cta_text and hero_cta_href:
        hero_cta = f"<a class=\"button\" href=\"{hero_cta_href}\">{hero_cta_text}</a>"

    def render_section(section_id: str) -> str:
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
        return (
            f"<section id=\"{section_id}\" class=\"panel reveal\">"
            f"<div class=\"panel-inner\">"
            f"<h2>{title}</h2>"
            f"{subtitle_html}"
            f"{body}"
            f"{bullet_html}"
            f"{cta}"
            f"</div>"
            f"</section>"
        )

    panels = "\n".join(render_section(section_id) for section_id in SECTION_ORDER if section_id != "hero")

    html_doc = f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>{hero_title or 'Artificial Life Institute'}</title>
    <meta name=\"description\" content=\"Artificial Life Institute at the University of Vienna\" />
    <link rel=\"stylesheet\" href=\"assets/css/style.css\" />
  </head>
  <body>
    <div class=\"grain\"></div>
    <header class=\"site-header\">
      <div class=\"logo\">ALI</div>
      <nav class=\"nav\">{nav_links}</nav>
      <a class=\"cta\" href=\"#contact\">Get in touch</a>
    </header>

    <main>
      <section id=\"hero\" class=\"hero\">
        <div class=\"hero-inner\">
          <div class=\"hero-copy\">
            <p class=\"eyebrow\">Artificial Life Institute</p>
            <h1>{hero_title}</h1>
            <p class=\"subtitle\">{hero_subtitle}</p>
            {hero_body}
            <div class=\"hero-actions\">{hero_cta}</div>
          </div>
          <div class=\"hero-card\">
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
      {panels}
    </main>

    <footer class=\"site-footer\">
      <p>Artificial Life Institute · University of Vienna</p>
      <p>https://artificial-life-institute.univie.ac.at</p>
    </footer>

    <script src=\"assets/js/main.js\"></script>
  </body>
</html>
"""

    (SITE_DIR / "index.html").write_text(html_doc, encoding="utf-8")
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
}

.nav a::after {
  content: '';
  position: absolute;
  left: 0;
  bottom: -6px;
  width: 100%;
  height: 2px;
  background: var(--bordeaux);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.3s ease;
}

.nav a:hover::after,
.nav a:focus::after {
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
}

.button.ghost {
  background: transparent;
  border: 1px solid var(--bordeaux);
  color: var(--bordeaux);
}

.hero-card {
  background: #fff;
  border-radius: var(--radius);
  padding: 28px;
  box-shadow: 0 24px 50px var(--shadow);
  border: 1px solid rgba(122, 16, 31, 0.1);
}

.hero-card h3 {
  margin-top: 0;
  font-family: 'Cormorant Garamond', serif;
  font-size: 26px;
  color: var(--ink);
}

.hero-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-top: 18px;
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

.panel {
  padding: 70px 6vw;
}

.panel-inner {
  max-width: var(--max-width);
  margin: 0 auto;
  background: #fff;
  border-radius: var(--radius);
  padding: clamp(26px, 4vw, 46px);
  box-shadow: 0 20px 40px var(--shadow);
  border: 1px solid rgba(122, 16, 31, 0.08);
}

.panel h2 {
  font-family: 'Cormorant Garamond', serif;
  font-size: clamp(28px, 3.5vw, 42px);
  color: var(--bordeaux);
  margin-top: 0;
}

.panel ul {
  padding-left: 18px;
}

.panel li {
  margin: 8px 0;
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
