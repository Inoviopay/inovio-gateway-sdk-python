#!/usr/bin/env python3
"""Runs every example in order.

Mock transport by default. Set INOVIO_LIVE=1 with credentials to run the same
code against the real gateway.
"""
import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _harness import LIVE  # noqa: E402

here = Path(__file__).parent
files = sorted(f for f in here.glob("[0-9][0-9]_*.py"))

print(f"Running {len(files)} examples against "
      f"{'the LIVE gateway' if LIVE else 'a mock transport'}\n")

failed = 0
for f in files:
    title = f.stem[3:].replace("_", " ")
    print(f"── {title}")
    try:
        runpy.run_path(str(f), run_name="__main__")
    except Exception as e:  # noqa: BLE001 - examples report their own failures
        failed += 1
        print(f"  ✗ {type(e).__name__}: {e}")
    print()

print(f"✅ all {len(files)} examples ran" if failed == 0
      else f"❌ {failed} of {len(files)} failed")
sys.exit(0 if failed == 0 else 1)
