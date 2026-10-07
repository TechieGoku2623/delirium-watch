#!/usr/bin/env python3
"""Read shots.yaml, write one script + caption + cast per beat."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from demo.lib.captions import write_srt  # noqa: E402
from demo.lib.record_cast import record_command, write_shot_script  # noqa: E402
from demo.lib.shots import all_commands, load_shots, shots_path  # noqa: E402


def main() -> None:
    data = load_shots(shots_path(ROOT))
    script_dir = ROOT / "demo" / "script"
    caption_dir = script_dir / "captions"
    cast_dir = ROOT / "demo" / "cast"
    caption_dir.mkdir(parents=True, exist_ok=True)
    cast_dir.mkdir(parents=True, exist_ok=True)

    timings: dict[str, dict[str, float]] = {}
    for shot in all_commands(data):
        shot_id = str(shot["id"])
        command = str(shot["command"])
        hold = float(shot.get("hold", 3.0))
        extra = 6.0 if shot.get("failure_beat") else 0.0
        write_shot_script(script_dir / f"{shot_id}.sh", command)
        meta = record_command(
            command,
            cast_dir / f"{shot_id}.cast",
            root=ROOT,
            hold=hold,
            highlight=shot.get("highlight"),
            extra_hold=extra,
        )
        timings[shot_id] = meta
        write_srt(
            caption_dir / f"{shot_id}.srt",
            str(shot["caption"]),
            meta["caption_start"],
            meta["duration"],
        )
        print(
            f"recorded {shot_id}  {meta['duration']:.1f}s  exit={int(meta['exit_code'])}",
            flush=True,
        )

    (ROOT / "demo" / ".tmp").mkdir(parents=True, exist_ok=True)
    (ROOT / "demo" / ".tmp" / "timings.json").write_text(
        json.dumps(timings, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
