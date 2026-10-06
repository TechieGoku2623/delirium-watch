"""Phase 0 CLI. Prediction and serving are Phase 2."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from delirium_watch import SAFETY_DISCLAIMER, __version__
from delirium_watch.cohort import designed_samples, generate_and_write, load_cohort
from delirium_watch.config import get_settings
from delirium_watch.logging import configure_logging

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console(width=140)


@app.callback()
def _main() -> None:
    configure_logging()


@app.command("version")
def version() -> None:
    """Print the package version."""

    console.print(f"delirium-watch {__version__}")


@app.command("demo-plan")
def demo_plan(
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run"),
) -> None:
    """Print the five designed synthetic patients and the path each exercises."""

    cohort = load_cohort()
    samples = designed_samples(cohort.patients)
    console.print("[bold]delirium-watch designed synthetic patients[/bold]\n")
    for sample in samples:
        console.print(f"[bold]{sample.subject_id}[/bold]  {sample.role}")
        console.print(f"  path:     {sample.path_exercised}")
        console.print(f"  expected: {sample.expected_behavior}\n")
    console.print()
    console.print(SAFETY_DISCLAIMER)
    if dry_run:
        console.print(
            "\nDry run only. Prediction (`delirium-watch predict`) is Phase 2; "
            "this command exists so `make demo` can show that the sample set "
            "is designed, not sampled from MIMIC."
        )
    console.print(f"Sample directory: {get_settings().sample_dir}")


@app.command("demo-data")
def demo_data(
    dest: Path | None = typer.Option(
        None,
        "--dest",
        help="Directory to write the synthetic tables. Defaults to data/sample.",
    ),
) -> None:
    """Regenerate the seeded 50-patient synthetic cohort."""

    cohort = generate_and_write(sample_dir=dest)
    console.print(
        f"Wrote {len(cohort.patients)} synthetic patients to {dest or get_settings().sample_dir}"
    )
    console.print(SAFETY_DISCLAIMER)


@app.command("sample-path")
def sample_path() -> None:
    """Print the committed sample directory path."""

    console.print(str(get_settings().sample_dir.resolve()))
