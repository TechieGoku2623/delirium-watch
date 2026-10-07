"""Record one command as an asciinema v2 cast: typed prompt + real latency."""

from __future__ import annotations

import json
import os
import re
import select
import shutil
import struct
import subprocess
import termios
import time
from pathlib import Path

from demo.lib.scrub import assert_clean, scrub_text

COLS = 100
ROWS = 30
TYPE_CPS = 12.0
PROMPT = "$ "


def clean_env(root: Path) -> dict[str, str]:
    keep = {
        "PATH",
        "TERM",
        "LANG",
        "LC_ALL",
        "COLUMNS",
        "LINES",
        "HOME",
        "TMPDIR",
        "TMP",
        "TEMP",
        "USER",
        "LOGNAME",
        "VIRTUAL_ENV",
        "UV_PROJECT_ENVIRONMENT",
        "PYTHONPATH",
        "PYTHONUNBUFFERED",
    }
    env = {k: v for k, v in os.environ.items() if k in keep}
    venv_bin = root / ".venv" / "bin"
    local_bin = Path.home() / ".local" / "bin"
    path_parts = [str(venv_bin), str(local_bin), env.get("PATH", "")]
    env["PATH"] = ":".join(p for p in path_parts if p)
    env["TERM"] = "xterm-256color"
    env["LANG"] = "C.UTF-8"
    env["LC_ALL"] = "C.UTF-8"
    env["COLUMNS"] = str(COLS)
    env["LINES"] = str(ROWS)
    env["PS1"] = PROMPT
    env["PYTHONUNBUFFERED"] = "1"
    env.pop("NO_COLOR", None)
    env["FORCE_COLOR"] = "1"
    env["CLICOLOR_FORCE"] = "1"
    env["HOME"] = str(root / "demo" / ".tmp" / "home")
    Path(env["HOME"]).mkdir(parents=True, exist_ok=True)
    return env


def _highlight(text: str, pattern: str | None) -> str:
    if not pattern:
        return text
    cre = re.compile(pattern)
    out: list[str] = []
    for line in text.splitlines(keepends=True):
        body = line[:-1] if line.endswith("\n") else line
        ending = "\n" if line.endswith("\n") else ""
        if cre.search(body):
            out.append(f"\x1b[48;5;220m\x1b[30m{body}\x1b[0m{ending}")
        else:
            out.append(line)
    return "".join(out)


def _run_pty(command: str, env: dict[str, str], cwd: Path) -> tuple[list[tuple[float, str]], int]:
    try:
        import pty
    except ImportError:
        return _run_pipe(command, env, cwd)

    master, slave = pty.openpty()
    winsize = struct.pack("HHHH", ROWS, COLS, 0, 0)
    try:
        import fcntl

        fcntl.ioctl(slave, termios.TIOCSWINSZ, winsize)
    except OSError:
        pass
    proc = subprocess.Popen(
        ["bash", "--norc", "--noprofile", "-c", command],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        cwd=cwd,
        env=env,
        close_fds=True,
    )
    os.close(slave)
    events: list[tuple[float, str]] = []
    t0 = time.monotonic()
    leftover = ""
    while True:
        ready, _, _ = select.select([master], [], [], 0.05)
        if ready:
            try:
                chunk = os.read(master, 4096)
            except OSError:
                chunk = b""
            if not chunk:
                if proc.poll() is not None:
                    break
                continue
            leftover += chunk.decode("utf-8", errors="replace")
            leftover = leftover.replace("\r\n", "\n")
            while "\n" in leftover:
                line, leftover = leftover.split("\n", 1)
                events.append((time.monotonic() - t0, line + "\n"))
            if leftover and proc.poll() is not None:
                events.append((time.monotonic() - t0, leftover))
                leftover = ""
        if proc.poll() is not None and not ready:
            # drain
            more, _, _ = select.select([master], [], [], 0.05)
            if not more:
                if leftover:
                    events.append((time.monotonic() - t0, leftover))
                break
    os.close(master)
    proc.wait()
    return events, int(proc.returncode or 0)


def _run_pipe(command: str, env: dict[str, str], cwd: Path) -> tuple[list[tuple[float, str]], int]:
    t0 = time.monotonic()
    proc = subprocess.run(
        ["bash", "--norc", "--noprofile", "-c", command],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.monotonic() - t0
    body = proc.stdout + (proc.stderr if proc.returncode else "")
    events = [(elapsed, body if body.endswith("\n") else body + "\n")]
    return events, int(proc.returncode or 0)


def record_command(
    command: str,
    dest: Path,
    *,
    root: Path,
    hold: float,
    highlight: str | None = None,
    extra_hold: float = 0.0,
) -> dict[str, float]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    env = clean_env(root)
    events: list[tuple[float, str]] = []
    t = 0.08
    events.append((t, PROMPT))
    for char in command:
        t += 1.0 / TYPE_CPS
        events.append((t, char))
    t += 0.06
    events.append((t, "\r\n"))
    typed_at = t

    raw_events, code = _run_pty(command, env, root)
    if not raw_events:
        raw_events = [(0.05, "\n")]
    # Keep real inter-byte gaps; shift so output starts after the typed newline.
    base = raw_events[0][0]
    for rel, chunk in raw_events:
        chunk = _highlight(scrub_text(chunk), highlight)
        t = typed_at + max(0.0, rel - base)
        events.append((t, chunk))
    hold_end = t + max(hold, 2.5) + extra_hold
    # agg collapses long idle gaps; keep the clock alive every 350ms.
    while t + 0.35 < hold_end:
        t += 0.35
        events.append((t, "\x1b[?25h"))
    t = hold_end
    events.append((t, "\x1b[0m"))

    header = {
        "version": 2,
        "width": COLS,
        "height": ROWS,
        "timestamp": 0,
        "env": {"SHELL": "/bin/bash", "TERM": "xterm-256color"},
    }
    lines = [json.dumps(header, separators=(",", ":"))]
    for ts, payload in events:
        lines.append(json.dumps([round(ts, 4), "o", payload], separators=(",", ":")))
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert_clean(dest)
    return {
        "duration": t,
        "caption_start": typed_at,
        "exit_code": float(code),
    }


def write_shot_script(path: Path, command: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"#!/usr/bin/env bash\nset +e\n{command}\nexit $?\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | 0o111)


def which_or_hint(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise SystemExit(f"required tool not on PATH: {name}")
    return found
