"""Run every Phase 0 harness and regenerate the memo and evaluation tables."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from delirium_watch.cohort import generate_and_write

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HARNESSES = (
    HERE / "label_agreement" / "run.py",
    HERE / "base_rate" / "run.py",
    HERE / "leakage_audit" / "run.py",
    HERE / "render_docs.py",
)


def main() -> None:
    generate_and_write()
    for script in HARNESSES:
        print(f"\n=== {script.relative_to(ROOT)} ===\n")
        subprocess.run([sys.executable, str(script)], check=True, cwd=ROOT)


if __name__ == "__main__":
    main()
