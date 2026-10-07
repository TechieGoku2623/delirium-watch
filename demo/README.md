# Regenerating the video

The demo is the same commands the README walkthrough runs. Nothing is
performed by hand. `make record` rebuilds every cast, gif, svg, and mp4.

```bash
make setup
make record
```

`make record` is `demo/record.sh` then `demo/render.sh`.

CI runs `make demo-shots`, which executes every command in
`demo/script/shots.yaml` against committed sample data. It does not render
video.

## Layout

```
demo/
  script/shots.yaml          source of truth: command, caption, hold
  script/01-*.sh             generated from shots.yaml
  script/captions/*.srt      one caption file per shot
  cast/*.cast                asciinema v2 recordings
  frames/                    title / problem / end / last-frame stills
  out/delirium-watch-demo.mp4   assembled video
  out/delirium-watch-demo.gif   10-12s header loop (failure beat)
  out/delirium-watch-<shot>.gif per-shot loops for the walkthrough
  record.sh                  pinned terminal + record_all.py
  render.sh                  agg + ffmpeg + burned-in captions
```

## Pinned tool versions

| Tool | Version | Role |
| --- | --- | --- |
| asciinema | 2.4.0 | v2 cast format (this pipeline writes the same JSONL) |
| agg | 1.5.0 | cast → gif |
| ffmpeg | 6.1.1 | assembly, caption overlay, title/end cards |
| svg-term-cli | latest via `npx --yes` | optional cast → svg |
| Python | 3.11 | record/render helpers |
| Pillow | pulled by `uv run --with pillow` | title / problem / end / caption cards |

Terminal enforced by `record.sh`:

- 100×30
- `TERM=xterm-256color`
- `LC_ALL=C.UTF-8`
- prompt `$ ` (never the real shell prompt)
- `NO_COLOR` unset
- credential-like environment variables unset
- `$HOME` remapped under `demo/.tmp/home` so paths cannot leak

Typing is simulated at 12 characters per second. Command latency is the real
runtime of the CLI against committed sample data. Hold time from shots.yaml
is applied at render (a still of the last frame) because agg collapses long
idle gaps in the cast.

Every `.cast` is grepped for `/Users/`, `/home/`, `@`, and key-like tokens
before it is written.

## Size budget

- Header gif (`out/delirium-watch-demo.gif`): under 2 MB, 10–15 s
- Per-shot gifs: under 1 MB
- Full mp4: under 15 MB

If a file is over budget, cut hold time, not resolution.
