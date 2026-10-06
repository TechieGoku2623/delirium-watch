"""Write asciinema v2 casts from real CLI stdout. No credentials."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo"


def _run(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout + proc.stderr


def _cast(path: Path, title: str, sessions: list[tuple[str, int, str]]) -> None:
    header = {
        "version": 2,
        "width": 120,
        "height": 40,
        "timestamp": 0,
        "title": title,
        "env": {"TERM": "xterm-256color", "SHELL": "/bin/bash"},
    }
    lines = [json.dumps(header)]
    t = 0.05
    for prompt, code, out in sessions:
        lines.append(json.dumps([t, "o", f"$ {prompt}\r\n"]))
        t += 0.15
        for chunk in out.splitlines(keepends=True):
            text = chunk.replace("\n", "\r\n")
            lines.append(json.dumps([t, "o", text]))
            t += 0.02
        lines.append(json.dumps([t, "o", f"\r\n[exit {code}]\r\n"]))
        t += 0.2
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    DEMO.mkdir(parents=True, exist_ok=True)
    cli = [sys.executable, "-m", "delirium_watch.cli"]
    code, out = _run([*cli, "demo-data"])
    labels = _run(
        [
            *cli,
            "labels",
            "compare",
            "--cohort",
            "data/sample/cohort.parquet",
        ]
    )
    _cast(
        DEMO / "01-cohort-and-labels.cast",
        "delirium-watch cohort and labels",
        [
            ("delirium-watch demo-data", code, out),
            ("delirium-watch labels compare --cohort data/sample/cohort.parquet", *labels),
        ],
    )
    pred = _run(
        [*cli, "predict", "--patient", "P001", "--horizon", "12", "--explain"]
    )
    _cast(DEMO / "02-predict-explain.cast", "delirium-watch predict --explain", [
        ("delirium-watch predict --patient P001 --horizon 12 --explain", *pred),
    ])
    audit = _run([*cli, "audit-leakage"])
    _cast(DEMO / "03-leakage-audit.cast", "delirium-watch audit-leakage", [
        ("delirium-watch audit-leakage", *audit),
    ])
    ev = _run([*cli, "eval"])
    _cast(DEMO / "04-evaluation.cast", "delirium-watch eval", [
        ("make eval / delirium-watch eval", *ev),
    ])
    print(f"wrote casts in {DEMO}")
    if audit[0] == 0:
        raise SystemExit("audit-leakage should exit non-zero")


if __name__ == "__main__":
    main()
