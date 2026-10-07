"""Refuse to commit a cast that leaked a home path, hostname, or key-like token."""

from __future__ import annotations

import re
from pathlib import Path

LEAK_PATTERNS = (
    re.compile(r"/Users/[A-Za-z0-9._-]+"),
    re.compile(r"/home/[A-Za-z0-9._-]+"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"(?:sk|rk|ghp|github_pat|xox[baprs])-[A-Za-z0-9_-]{8,}"),
)


def scrub_text(text: str) -> str:
    cleaned = text
    cleaned = LEAK_PATTERNS[0].sub("~", cleaned)
    cleaned = LEAK_PATTERNS[1].sub("~", cleaned)
    cleaned = LEAK_PATTERNS[2].sub("[redacted]", cleaned)
    cleaned = LEAK_PATTERNS[3].sub("[redacted]", cleaned)
    return cleaned


def assert_clean(path: Path) -> None:
    body = path.read_text(encoding="utf-8")
    remaining: list[str] = []
    for pattern in LEAK_PATTERNS:
        hit = pattern.search(body)
        if hit:
            remaining.append(f"{path}: {hit.group(0)}")
    if remaining:
        raise SystemExit("cast leaked machine or secret data:\n  " + "\n  ".join(remaining))
