"""Regenerate the committed synthetic MIMIC-like cohort. Seed 0. No MIMIC rows."""

from __future__ import annotations

from delirium_watch.cohort import generate_and_write

if __name__ == "__main__":
    generate_and_write()
