#!/usr/bin/env python3
import sys
from pathlib import Path

# Configuration
CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
BLOCKS_DIR = CONTENT_DIR / "blocks"
QUEUE_DIR = CONTENT_DIR / "_queue"
DRAFT_DIR = QUEUE_DIR / "draft"
REVIEW_DIR = QUEUE_DIR / "review"
PUBLISHED_DIR = QUEUE_DIR / "published"

MIN_COL_WIDTH = 30

def print_header(title):
    print(f"\n=== {title} ===")
    print(f"{'Filename':<{MIN_COL_WIDTH}} | {'Status/Location':<15}")
    print("-" * (MIN_COL_WIDTH + 18))

def list_files(directory, status_label):
    if not directory.exists():
        return
    
    files = sorted([f for f in directory.glob("*.md") if f.is_file()])
    if not files:
        print(f"(No files in {directory.name})")
        return

    for f in files:
        print(f"{f.name:<{MIN_COL_WIDTH}} | {status_label}")

def run():
    print(f"Content Dashboard for: {CONTENT_DIR.parent.name}")
    
    # Active Blocks
    print_header("Active Blocks (Homepage)")
    list_files(BLOCKS_DIR, "[Live]")

    # Queue
    print_header("Publishing Queue")
    list_files(DRAFT_DIR, "[Draft]")
    list_files(REVIEW_DIR, "[Review]")
    list_files(PUBLISHED_DIR, "[Published/Archived]")
    
    print("\n")

if __name__ == "__main__":
    run()
