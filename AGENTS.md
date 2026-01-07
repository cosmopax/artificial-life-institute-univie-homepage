# AGENT PROTOCOLS: Artificial Life Institute

## 1. Status: V1 (Legacy)

This site uses the V1 Python build system. It renders markdown files to HTML.

## 2. GOAL: Upgrade to V2 (Academic Futurism)

**Reference Implementation:** `../patrick-homepage-univie/AGENTS.md`

### Upgrade Checklist (for autonomous agents)

1. **Data Structure:** extract content from detailed markdown files into `content/research.json`, `content/team.json`.
2. **Renderer:** Update `tools/build.py` to copy the V2 renderers from Patrick's repo.
3. **Styles:** Copy `content/assets/css/landing.css` from Patrick's repo (adjusting primary accent colors if needed).
4. **Interaction:** Implement "Burger Menu" and "Scroll Reveal".

## 3. Maintenance (Current)

* **Build:** `python3 tools/build.py`
* **Deploy:** `./deploy.sh`
