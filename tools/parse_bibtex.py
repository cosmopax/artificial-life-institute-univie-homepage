#!/usr/bin/env python3
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Taxonomy Mapping
TYPE_MAP = {
    'article': 'Journal Articles',
    'inproceedings': 'Conference Papers',
    'proceedings': 'Conference Papers',
    'book': 'Books',
    'incollection': 'Book Chapters',
    'phdthesis': 'Theses',
    'mastersthesis': 'Theses',
    'techreport': 'Technical Reports',
    'unpublished': 'Working Papers',
    'misc': 'Other'
}

def parse_bibtex(content: str) -> List[Dict[str, str]]:
    """
    Parses BibTeX content into a list of dictionaries.
    Handles standard BibTeX format with nested braces or quotes.
    """
    entries = []
    # Regex to find entry start: @type{key,
    entry_pattern = re.compile(r'@(\w+)\s*{\s*([^,]+),', re.MULTILINE)
    
    pos = 0
    while True:
        match = entry_pattern.search(content, pos)
        if not match:
            break
            
        entry_type = match.group(1).lower()
        key = match.group(2).strip()
        start_pos = match.end()
        
        # Parse fields
        fields = {}
        current_pos = start_pos
        brace_balance = 1 # We are inside the entry brace (not strictly true for the regex but logically) 
        
        # Scan forward to find the closing brace of the entry
        # and parse "field = {value}" pairs within
        
        # Simple field parser loop
        while True:
            # Skip whitespace
            while current_pos < len(content) and content[current_pos].isspace():
                current_pos += 1
            
            if current_pos >= len(content): break
            
            if content[current_pos] == '}':
                # End of entry
                entries.append({'type': entry_type, 'key': key, **fields})
                pos = current_pos + 1
                break
            
            # Match field name
            field_match = re.match(r'(\w+)\s*=\s*', content[current_pos:])
            if field_match:
                field_name = field_match.group(1).lower()
                current_pos += field_match.end()
                
                # Parse value
                value = ""
                if content[current_pos] == '{':
                    # Braced value
                    current_pos += 1
                    balance = 1
                    start_val = current_pos
                    while balance > 0 and current_pos < len(content):
                        if content[current_pos] == '{': balance += 1
                        elif content[current_pos] == '}': balance -= 1
                        current_pos += 1
                    value = content[start_val:current_pos-1]
                elif content[current_pos] == '"':
                    # Quoted value
                    current_pos += 1
                    start_val = current_pos
                    while current_pos < len(content):
                        if content[current_pos] == '"' and content[current_pos-1] != '\\':
                            break
                        current_pos += 1
                    value = content[start_val:current_pos]
                    current_pos += 1
                else:
                    # Raw value (number or string)
                    start_val = current_pos
                    while current_pos < len(content) and content[current_pos] not in ',}':
                        current_pos += 1
                    value = content[start_val:current_pos].strip()
                
                # Clean value (latex symbols)
                value = value.replace('\n', ' ').replace('\r', '').strip()
                value = re.sub(r'\s+', ' ', value)
                fields[field_name] = value
                
                # Skip comma
                while current_pos < len(content) and content[current_pos].isspace():
                    current_pos += 1
                if current_pos < len(content) and content[current_pos] == ',':
                    current_pos += 1
            else:
                # Unexpected char, skip to next closing brace or comma to recover
                current_pos += 1

    return entries

def format_entry(entry: Dict[str, str]) -> str:
    """Formats a single BibTeX entry into Markdown."""
    authors = entry.get('author', 'Unknown').replace(' and ', ', ')
    year = entry.get('year', 'n.d.')
    title = entry.get('title', 'Untitled')
    source = entry.get('journal') or entry.get('booktitle') or entry.get('publisher') or entry.get('school') or entry.get('institution') or ""
    note = entry.get('note', '')
    
    # Bold authors
    # Simplifying names could be added here (e.g. "Schimpl, P.")
    
    md = f"* **{authors}** ({year}). *{title}*."
    if source:
        md += f" {source}."
    if note:
        md += f" ({note})."
        
    return md

def generate_markdown(bib_path: str, output_path: str):
    path = Path(bib_path)
    if not path.exists():
        print(f"Error: {bib_path} not found.")
        return

    content = path.read_text(encoding='utf-8')
    entries = parse_bibtex(content)
    
    # Group by category
    grouped = {}
    for entry in entries:
        etype = entry.get('type', 'misc')
        category = TYPE_MAP.get(etype, 'Other')
        
        # Override for Keynotes
        if entry.get('note', '').lower().startswith('keynote'):
            category = 'Keynotes'
            
        if category not in grouped:
            grouped[category] = []
        grouped[category].append(entry)
        
    # Sort Categories
    preferred_order = [
        'Journal Articles', 'Conference Papers', 'Books', 'Book Chapters', 
        'Keynotes', 'Working Papers', 'Technical Reports', 'Theses', 'Other'
    ]
    
    md_output = "# Publications\n\n"
    
    for category in preferred_order:
        if category in grouped:
            entries_list = grouped[category]
            # Sort by year descending
            entries_list.sort(key=lambda x: x.get('year', '0000'), reverse=True)
            
            md_output += f"## {category}\n\n"
            for entry in entries_list:
                md_output += format_entry(entry) + "\n"
            md_output += "\n"
            
    # Handle categories not in preferred order
    for category, entries_list in grouped.items():
        if category not in preferred_order:
            entries_list.sort(key=lambda x: x.get('year', '0000'), reverse=True)
            md_output += f"## {category}\n\n"
            for entry in entries_list:
                md_output += format_entry(entry) + "\n"
            md_output += "\n"

    Path(output_path).write_text(md_output, encoding='utf-8')
    print(f"Generated {output_path} from {bib_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: parse_bibtex.py <input.bib> <output.md>")
    else:
        generate_markdown(sys.argv[1], sys.argv[2])
