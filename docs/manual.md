# Univie Homepages – Working Manual (ALI + PATRICK)

## Grundprinzip
- **Nie `site/` editieren.** `site/` ist **Build-Output**.
- Du editierst **immer** in `content/` (und ggf. `tools/`), dann:
  1) `python3 tools/build.py`
  2) Lokal preview
  3) erst dann `./deploy.sh` (wenn Webspace gemountet)

## Wo du Inhalte schreibst (WICHTIG)
### Beide Repos (gleiche Logik)
- Seitenstruktur / Reihenfolge / welche Blöcke auf welche Seite: `content/control.csv`
- Texte pro Abschnitt (ein Block = eine Datei): `content/blocks/*.md`
- Links / Presence: `content/links.csv`
- Blogposts: `content/blog/*.txt`
- Site-Metadaten / Layout-Toggles: `content/site.json`
- Bilder: `content/media/` (werden beim Build nach `site/assets/img/` kopiert)
- Feeds/Digests: `content/feeds/feeds.txt` + `python3 tools/fetch_digest.py`

## Standard-Workflow (immer gleich)
1) Inhalte ändern: `content/...`
2) Build: `python3 tools/build.py`
3) Lokal preview:
   - `python3 -m http.server 8787 -d site` (z.B. ALI)
   - `python3 -m http.server 8788 -d site` (z.B. PATRICK)
4) Deploy (nur wenn SMB gemountet): `./deploy.sh`
5) Live-Check:
   - `curl -s -o /dev/null -w "%{http_code}\n" "<URL>"`
   - `curl -s "<URL>" | head -n 20`

## Git Hygiene (Safety)
- Vor jedem Push:
  - `git remote -v`
  - `git log -1 --oneline`
  - `git status --porcelain=v1`
- **Stop on unexpected changes:** wenn `git status` etwas zeigt, erst `git diff` ansehen.

## Webspace Mount (SMB)
- Voraussetzung: Univie VPN (BIG-IP) ON.
- Host: `webspace-access.univie.ac.at`
- Domain-Login (robust in mount_smbfs): `u;a0402554`
- Finder-Login: `u\a0402554` (Backslash-Variante)

Mount-Pfade (Beispiele):
- ALI webroot: `~/WebspaceMount/a0402554/artificiat27/html`
- PATRICK webroot: `~/WebspaceMount/a0402554/holobionte98/html`

## Troubleshooting
- “Seite nicht erreichbar”: erst `curl` testen (HTTP-Code).
- “Mount Passwort wird nicht akzeptiert”:
  - Keychain-Eintrag löschen (falls falsche Credentials cached sind)
  - dann neu mounten und Credentials sauber eingeben.
