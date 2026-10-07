"""Load shots.yaml. PyYAML is pulled in by `uv run --with pyyaml`."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def shots_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / "demo" / "script" / "shots.yaml"


def load_shots(path: Path | None = None) -> dict[str, Any]:
    target = path or shots_path()
    data = yaml.safe_load(target.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"shots.yaml must be a mapping: {target}")
    return data


def all_commands(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Shots plus the results beat, in video order."""

    shots = [dict(s) for s in data["shots"]]
    results = dict(data["results"])
    results.setdefault("id", "05-results")
    results.setdefault("failure_beat", False)
    results.setdefault("hold", 4.0)
    shots.append(results)
    return shots


def gif_beat_id(data: dict[str, Any]) -> str:
    if data.get("gif_beat"):
        return str(data["gif_beat"])
    return str(next(s["id"] for s in data["shots"] if s.get("failure_beat")))


def wrap_caption(text: str, width: int = 60, max_lines: int = 2) -> list[str]:
    raw_lines = [ln.strip() for ln in str(text).splitlines() if ln.strip()]
    lines: list[str] = []
    for raw in raw_lines:
        words = raw.split()
        current = ""
        for word in words:
            trial = word if not current else f"{current} {word}"
            if len(trial) <= width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
    if len(lines) > max_lines:
        raise ValueError(f"caption exceeds {max_lines} lines: {text!r}")
    for line in lines:
        if len(line) > width:
            raise ValueError(f"caption line exceeds {width} chars: {line!r}")
    return lines
