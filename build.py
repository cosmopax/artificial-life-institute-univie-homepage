#!/usr/bin/env python3
from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    build_path = Path(__file__).resolve().parent / "tools" / "build.py"
    runpy.run_path(build_path, run_name="__main__")
