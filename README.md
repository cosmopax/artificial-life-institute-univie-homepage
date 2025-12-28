# Artificial Life Institute (University of Vienna) Homepage

This repo generates a static site for https://artificial-life-institute.univie.ac.at with a minimal, single-file content model.

## Edit content
- `content/site.json`: global settings (newsletter mode, footer note, domain).
- `content/pages.csv`: page sections and navigation.
- `content/links.csv`: digital presence links.
- `content/blog/*.txt`: blog posts (Title/Date/Body format).

## Build
```bash
python3 tools/build.py
```

Make-like command:
```bash
python3 tools/build.py && python3 tools/verify_links.py
```

## Deploy
```bash
./deploy.sh
```

Deployment targets `/Users/cosmopax/WebspaceMount/a0402554/artificiat27/html` and quarantines existing files under `__quarantine__/YYYYmmdd-HHMMSS/` before copying the new `site/` output.

## How to add images
1. Drop source images into `content/media/` (keep file names stable).
2. Reference the image filename in `content/pages.csv` (column `hero_image`).
3. Run `python3 tools/build.py` to copy images into `site/assets/img/`.

## Newsletter
The newsletter form posts to `subscribe.php` (deployed at webroot) which appends signups to `data/newsletter_signups.csv`. The `data/` directory is protected by `.htaccess`.
