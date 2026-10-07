#!/usr/bin/env python3
"""Run every command in shots.yaml against committed sample data.

CI uses this instead of rendering video. A command that no longer exists, or
that exits unexpectedly, fails the job.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from demo.lib.shots import all_commands, load_shots, shots_path  # noqa: E402


def main() -> None:
    data = load_shots(shots_path(ROOT))
    env = os.environ.copy()
    env["PATH"] = f"{ROOT / '.venv' / 'bin'}:{env.get('PATH', '')}"
    env["TERM"] = "xterm-256color"
    env.pop("NO_COLOR", None)
    failed = 0
    for shot in all_commands(data):
        command = str(shot["command"])
        expected = int(shot.get("expect_exit", 0))
        print(f"$ {command}", flush=True)
        proc = subprocess.run(
            ["bash", "--norc", "--noprofile", "-c", command],
            cwd=ROOT,
            env=env,
            check=False,
        )
        if proc.returncode != expected:
            print(
                f"FAIL {shot['id']}: exit {proc.returncode}, expected {expected}",
                file=sys.stderr,
            )
            failed += 1
        else:
            print(f"ok   {shot['id']} (exit {proc.returncode})")
    if failed:
        raise SystemExit(failed)


if __name__ == "__main__":
    main()
