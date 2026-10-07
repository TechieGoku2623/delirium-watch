"""Write one .srt per shot from shots.yaml. Max two lines, 60 characters."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from demo.lib.shots import wrap_caption


def format_ts(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    millis = int(round(seconds * 1000))
    hours, rem = divmod(millis, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def write_srt(path: Path, caption: str, start: float, end: float) -> None:
    lines = wrap_caption(caption)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "1\n" + f"{format_ts(start)} --> {format_ts(end)}\n" + "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def write_shot_captions(
    data: dict[str, Any],
    dest: Path,
    timings: dict[str, tuple[float, float]],
) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    from demo.lib.shots import all_commands

    for shot in all_commands(data):
        start, end = timings[shot["id"]]
        write_srt(dest / f"{shot['id']}.srt", str(shot["caption"]), start, end)
