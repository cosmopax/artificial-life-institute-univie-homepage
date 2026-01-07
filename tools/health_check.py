#!/usr/bin/env python3
"""
tools/health_check.py
Operational Health Check for Patrick Schimpl's Academic Homepage.
Performs:
1. JSON Syntax Validation (site.json)
2. Local Asset Verification (Images/Links in Markdown)
3. Report Generation (HEALTH_REPORT.md)
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

BASE_DIR = Path(__file__).resolve().parents[1]
CONTENT_DIR = BASE_DIR / "content"
SITE_JSON = CONTENT_DIR / "site.json"
ASSETS_DIR = BASE_DIR / "site" / "assets" / "img" # Assumes images are here for checking

# Regex for Markdown images/links: ![alt](url) or [text](url)
MD_LINK_RE = re.compile(r'!?\[.*?\]\((.*?)\)')

def check_json():
    print(f"[-] Checking {SITE_JSON.relative_to(BASE_DIR)}...")
    if not SITE_JSON.exists():
        return False, "site.json missing"
    try:
        data = json.loads(SITE_JSON.read_text())
        return True, f"Valid JSON. Keys: {list(data.keys())}"
    except json.JSONDecodeError as e:
        return False, f"JSON Error: {e}"

def check_assets():
    print("[-] Verifying local asset links in Markdown files...")
    errors = []
    checked_count = 0
    
    # Walk through all markdown files in content
    for md_file in CONTENT_DIR.rglob("*.md"):
        rel_path = md_file.relative_to(CONTENT_DIR)
        content = md_file.read_text()
        
        links = MD_LINK_RE.findall(content)
        for link in links:
            # Skip external links, anchors, and mailto
            if link.startswith(('http', 'https', 'mailto:', '#')):
                continue
            
            # Normalize path
            # If it starts with /, it's relative to site root? Or content root? 
            # Usually in these static sites, standardizing on checking relative to expected locations.
            # For now, let's assume images are in assets/img and check there if it looks like an image
            
            clean_link = link.split('?')[0].split('#')[0]
            
            # Simple heuristic: Check if file exists relative to md file OR in assets
            # 1. Check relative to MD file
            candidate_1 = (md_file.parent / clean_link).resolve()
            
            # 2. Check if it's an absolute-like path to assets (e.g. /assets/img/...)
            if clean_link.startswith('/'):
                # relative to site root (which is usually 'site' folder in this setup)
                candidate_2 = (BASE_DIR / "site" / clean_link.lstrip('/')).resolve()
            else:
                candidate_2 = (BASE_DIR / "site" / clean_link).resolve()

            if candidate_1.exists() or candidate_2.exists():
                checked_count += 1
                continue
            else:
                errors.append(f"Broken Link in {rel_path}: {link}")

    return errors, checked_count

def main():
    report_lines = ["# Operational Health Check Report", ""]
    
    # 1. JSON Check
    json_ok, json_msg = check_json()
    status = "PASS" if json_ok else "FAIL"
    report_lines.append(f"## 1. Site Configuration (`site.json`)\n- Status: **{status}**\n- Details: {json_msg}\n")
    
    # 2. Asset Check
    asset_errors, count = check_assets()
    if not asset_errors:
        report_lines.append(f"## 2. Content Integrity\n- Status: **PASS**\n- Verified {count} local links.\n")
    else:
        report_lines.append(f"## 2. Content Integrity\n- Status: **FAIL**\n- Verified {count} links.\n- **Errors Found:**")
        for err in asset_errors:
            report_lines.append(f"  - {err}")
            
    # Write Report
    report_path = BASE_DIR / "HEALTH_REPORT.md"
    report_path.write_text("\n".join(report_lines))
    print(f"\n[+] Health Check Complete. Report written to {report_path.name}")
    print("\n".join(report_lines))

if __name__ == "__main__":
    main()
