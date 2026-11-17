#!/usr/bin/env python3
"""
HUCE-KMS — Database Seeder CLI Runner (scripts/seed.py)

Usage:
    uv run python scripts/seed.py
"""

import asyncio
import sys
from pathlib import Path

# Ensure backend root and src are in pythonpath
current_dir = Path(__file__).resolve().parent
backend_root = current_dir.parent
src_dir = backend_root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from api.core.seeder import seed_initial_data

if __name__ == "__main__":
    asyncio.run(seed_initial_data())
