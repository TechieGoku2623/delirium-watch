#!/usr/bin/env python3
"""cast -> gif/svg/mp4 via agg + ffmpeg. Captions burned in. No voiceover."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from demo.lib.cards import (  # noqa: E402
    write_caption_bar,
    write_end,
    write_problem,
    write_title,
)
from demo.lib.shots import (  # noqa: E402
    all_commands,
    gif_beat_id,
    load_shots,
    shots_path,
    wrap_caption,
)

TITLE_S = 8.0
PROBLEM_S = 26.0
END_S = 12.0
WIDTH = 1280
HEIGHT = 720
FPS = 15


def run(cmd: list[str], **kwargs: object) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, **kwargs)  # type: ignore[arg-type]


def which(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise SystemExit(f"required tool not on PATH: {name}")
    return found


def ffmpeg() -> str:
    return which("ffmpeg")


def still_to_mp4(png: Path, dest: Path, seconds: float) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            ffmpeg(),
            "-y",
            "-loop",
            "1",
            "-i",
            str(png),
            "-t",
            f"{seconds:.2f}",
            "-r",
            str(FPS),
            "-vf",
            f"scale={WIDTH}:{HEIGHT},format=yuv420p",
            "-an",
            str(dest),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def agg_gif(cast: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        which("agg"),
        "--font-size",
        "18",
        "--fps-cap",
        str(FPS),
        "--cols",
        "100",
        "--rows",
        "30",
        "--theme",
        "monokai",
        "--idle-time-limit",
        "30",
        "--last-frame-duration",
        "0.2",
        str(cast),
        str(dest),
    ]
    run(cmd)


def maybe_svg(cast: Path, dest: Path) -> None:
    svg_term = shutil.which("svg-term")
    cmd: list[str] | None
    if svg_term:
        cmd = [svg_term, "--in", str(cast), "--out", str(dest), "--window"]
    else:
        npx = shutil.which("npx")
        if not npx:
            print("svg-term not installed; skipping SVG stills", flush=True)
            return
        cmd = [
            npx,
            "--yes",
            "svg-term-cli",
            "--in",
            str(cast),
            "--out",
            str(dest),
            "--width",
            "100",
            "--height",
            "30",
            "--window",
        ]
    try:
        run(cmd)
    except subprocess.CalledProcessError as exc:
        print(f"svg-term skipped ({exc.returncode}); PNG stills still written", flush=True)


def gif_to_captioned_mp4(gif: Path, caption_png: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    vf = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
        f"fps={FPS},format=yuv420p"
    )
    # Overlay the caption bar in the bottom third.
    filter_complex = f"[0:v]{vf}[base];[1:v]format=rgba[bar];[base][bar]overlay=(W-w)/2:H-h-24"
    run(
        [
            ffmpeg(),
            "-y",
            "-i",
            str(gif),
            "-i",
            str(caption_png),
            "-filter_complex",
            filter_complex,
            "-an",
            str(dest),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def last_frame(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            ffmpeg(),
            "-y",
            "-sseof",
            "-0.1",
            "-i",
            str(src),
            "-frames:v",
            "1",
            str(dest),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def concat_mp4(parts: list[Path], dest: Path, listing: Path) -> None:
    listing.parent.mkdir(parents=True, exist_ok=True)
    listing.write_text("".join(f"file '{p.resolve()}'\n" for p in parts), encoding="utf-8")
    run(
        [
            ffmpeg(),
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(listing),
            "-c",
            "copy",
            str(dest),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def still_gif(png: Path, dest: Path, seconds: float) -> None:
    """Loop a still as a small gif. ffmpeg's native gif encoder is too large."""

    from PIL import Image

    dest.parent.mkdir(parents=True, exist_ok=True)
    frame = Image.open(png)
    if frame.width > 960:
        height = int(960 * frame.height / frame.width)
        frame = frame.resize((960, height), Image.Resampling.LANCZOS)
    frame = frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=64)
    n = max(2, int(seconds * 2))
    frame.save(
        dest,
        save_all=True,
        append_images=[frame] * (n - 1),
        duration=500,
        loop=0,
        optimize=True,
    )


def pad_gif(src: Path, dest: Path, seconds: float) -> None:
    """Keep the animated beat, then hold the last frame out to ``seconds``."""

    from PIL import Image

    im = Image.open(src)
    frames: list[Image.Image] = []
    durations: list[int] = []
    while True:
        frames.append(im.convert("P", palette=Image.Palette.ADAPTIVE, colors=64))
        durations.append(int(im.info.get("duration", 80)))
        try:
            im.seek(im.tell() + 1)
        except EOFError:
            break
    if not frames:
        raise SystemExit(f"empty gif: {src}")
    total_ms = sum(durations)
    remain = int(seconds * 1000) - total_ms
    if remain > 0:
        n = max(1, remain // 500)
        frames.extend([frames[-1]] * n)
        durations.extend([500] * n)
    dest.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        dest,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )


def probe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            ffmpeg().replace("ffmpeg", "ffprobe") if False else "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    )
    try:
        return float(out.strip())
    except ValueError:
        return 0.0


def main() -> None:
    which("ffmpeg")
    which("agg")
    data = load_shots(shots_path(ROOT))
    slug = str(data["title"])
    frames = ROOT / "demo" / "frames"
    out = ROOT / "demo" / "out"
    tmp = ROOT / "demo" / ".tmp"
    frames.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)

    write_title(frames / "title.png", str(data["title"]), str(data["tagline"]))
    write_problem(frames / "problem.png", list(data["problem"]))
    write_end(frames / "end.png", str(data["end_card"]["url"]), str(data["end_card"]["license"]))
    still_to_mp4(frames / "title.png", tmp / "title.mp4", TITLE_S)
    still_to_mp4(frames / "problem.png", tmp / "problem.mp4", PROBLEM_S)
    still_to_mp4(frames / "end.png", tmp / "end.mp4", END_S)

    parts = [tmp / "title.mp4", tmp / "problem.mp4"]
    beat = gif_beat_id(data)
    for shot in all_commands(data):
        shot_id = str(shot["id"])
        cast = ROOT / "demo" / "cast" / f"{shot_id}.cast"
        gif = out / f"{slug}-{shot_id}.gif"
        svg = frames / f"{shot_id}.svg"
        cap = tmp / f"{shot_id}-caption.png"
        mp4 = tmp / f"{shot_id}.mp4"
        write_caption_bar(cap, wrap_caption(str(shot["caption"])))
        agg_gif(cast, gif)
        maybe_svg(cast, svg)
        gif_to_captioned_mp4(gif, cap, mp4)
        last_png = frames / f"{shot_id}.png"
        last_frame(mp4, last_png)
        parts.append(mp4)
        hold = float(shot.get("hold", 3.0))
        if shot.get("failure_beat"):
            hold += 6.0
        hold_mp4 = tmp / f"{shot_id}-hold.mp4"
        still_to_mp4(last_png, hold_mp4, hold)
        parts.append(hold_mp4)
        size = gif.stat().st_size
        print(f"{gif.name}  {size / 1024:.0f} KiB  + {hold:.1f}s hold", flush=True)
        if size > 1_000_000:
            print(
                f"WARNING: {gif.name} is {size / 1_000_000:.2f} MB (budget 1 MB)",
                flush=True,
            )

    full = out / f"{slug}-demo.mp4"
    concat_mp4(parts + [tmp / "end.mp4"], full, tmp / "demo.concat.txt")
    header = out / f"{slug}-demo.gif"
    pad_gif(out / f"{slug}-{beat}.gif", header, 12.0)

    runtime = TITLE_S + PROBLEM_S + END_S
    for shot in all_commands(data):
        runtime += probe_duration(tmp / f"{shot['id']}.mp4")
        runtime += probe_duration(tmp / f"{shot['id']}-hold.mp4")

    manifest = {
        "runtime_s": round(runtime, 1),
        "mp4_bytes": full.stat().st_size,
        "header_gif_bytes": header.stat().st_size,
        "gif_beat": beat,
    }
    (tmp / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        f"runtime {runtime:.1f}s  mp4 {full.stat().st_size / 1_000_000:.2f} MB  "
        f"header gif {header.stat().st_size / 1_000_000:.2f} MB",
        flush=True,
    )
    if runtime < 90 or runtime > 150:
        print(f"WARNING: runtime {runtime:.1f}s is outside 90-150s target", flush=True)
    if full.stat().st_size > 15_000_000:
        print("WARNING: mp4 exceeds 15 MB — cut hold times, not resolution", flush=True)
    if header.stat().st_size > 2_000_000:
        print("WARNING: header gif exceeds 2 MB", flush=True)


if __name__ == "__main__":
    main()
