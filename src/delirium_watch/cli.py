"""Phase 0–3 CLI. Synthetic cohort only. Not a medical device. Not for patient care."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from delirium_watch import HORIZONS_HOURS, SAFETY_DISCLAIMER, __version__
from delirium_watch.audit import run_audit
from delirium_watch.baselines import e_pre_deliric_probability, pre_deliric_probability
from delirium_watch.cohort import designed_samples, generate_and_write, load_cohort
from delirium_watch.config import get_settings
from delirium_watch.evaluate import evaluate_cohort, format_eval_text
from delirium_watch.exclusions import excluded_patients, included_patients
from delirium_watch.label_compare import compare_label_rows
from delirium_watch.labels import all_labels
from delirium_watch.logging import configure_logging
from delirium_watch.model import predict_at
from delirium_watch.parquet_io import label_table_from_parquet
from delirium_watch.schemas import LabelName

app = typer.Typer(no_args_is_help=True, add_completion=False)
labels_app = typer.Typer(no_args_is_help=True, add_completion=False)
app.add_typer(labels_app, name="labels")
console = Console(width=100)


@app.callback()
def _main() -> None:
    configure_logging()


def _print_disclaimer() -> None:
    console.print(SAFETY_DISCLAIMER)


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
    _print_disclaimer()
    if dry_run:
        console.print(
            "\nDry run only. `make demo` runs demo-data, labels compare, "
            "predict --explain, and the leakage audit."
        )
    console.print(f"Sample directory: {get_settings().sample_dir}")


def _print_cohort_stats(cohort: object, dest: Path) -> None:
    from delirium_watch.cohort import Cohort

    assert isinstance(cohort, Cohort)
    included = included_patients(cohort.patients)
    excluded = excluded_patients(cohort.patients)
    console.print(f"Wrote {len(cohort.patients)} synthetic patients to {dest}")
    console.print(f"Parquet: {dest / 'cohort.parquet'}")
    console.print(f"Included: {len(included)}   Excluded (comfort care): {len(excluded)}")
    if excluded:
        console.print("  excluded ids: " + ", ".join(p.subject_id for p in excluded))
    table = Table(title="Base rate on included stays (any-time label)")
    table.add_column("label")
    table.add_column("n+", justify="right")
    table.add_column("prevalence", justify="right")
    names: tuple[LabelName, ...] = ("cam_icu", "antipsychotic", "restraint")
    for name in names:
        n_pos = 0
        for patient in included:
            calls = all_labels(
                patient,
                assessments=cohort.chartevents,
                meds=cohort.prescriptions,
                procedures=cohort.procedureevents,
            )
            if calls[name].positive:
                n_pos += 1
        prev = n_pos / len(included) if included else 0.0
        table.add_row(name, str(n_pos), f"{prev:.3f}")
    console.print(table)
    console.print("Synthetic only. No MIMIC bytes. Not a population incidence.")
    _print_disclaimer()


@app.command("demo-data")
def demo_data(
    dest: Path | None = typer.Option(
        None,
        "--dest",
        help="Directory to write the synthetic tables. Defaults to data/sample.",
    ),
) -> None:
    """Generate the seeded 50-patient synthetic cohort and print counts."""

    out = dest or get_settings().sample_dir
    cohort = generate_and_write(sample_dir=out)
    _print_cohort_stats(cohort, out)


@labels_app.command("compare")
def labels_compare(
    cohort: Path = typer.Option(
        ...,
        "--cohort",
        exists=True,
        readable=True,
        help="Cohort parquet written by demo-data.",
    ),
) -> None:
    """Three label definitions and pairwise agreement."""

    rows = label_table_from_parquet(cohort)
    payload = compare_label_rows(rows)
    console.print("[bold]delirium-watch labels compare[/bold]")
    console.print(f"cohort: {cohort}")
    console.print(
        f"raw n={payload['n_raw']}  included n={payload['n_included']}  "
        f"excluded n={payload['n_excluded']}"
    )
    prev = payload["prevalence"]
    console.print(
        "prevalence (included): "
        f"CAM-ICU={prev['cam_icu']:.3f}  "
        f"antipsychotic={prev['antipsychotic']:.3f}  "
        f"restraint={prev['restraint']:.3f}"
    )
    table = Table(title="Pairwise agreement")
    table.add_column("pair")
    table.add_column("n", justify="right")
    table.add_column("both+", justify="right")
    table.add_column("left only", justify="right")
    table.add_column("right only", justify="right")
    table.add_column("neither", justify="right")
    table.add_column("agreement", justify="right")
    table.add_column("kappa", justify="right")
    for row in payload["pairs"]:
        table.add_row(
            str(row["pair"]),
            str(row["n"]),
            str(row["both+"]),
            str(row["left_only"]),
            str(row["right_only"]),
            str(row["neither"]),
            f"{float(row['agreement']):.3f}",
            f"{float(row['kappa']):.3f}",
        )
    console.print(table)
    console.print(f"Mean pairwise kappa: {payload['mean_kappa']:.3f}")
    if payload["label_choice_dominates"]:
        console.print(
            "Label choice dominates downstream results (mean kappa < 0.60). "
            "The three definitions stay competing endpoints."
        )
    _print_disclaimer()


@app.command("predict")
def predict(
    patient: str = typer.Option(..., "--patient", help="Synthetic subject id, e.g. P001."),
    horizon: int = typer.Option(12, "--horizon", help="Forecast horizon in hours: 6, 12, or 24."),
    explain: bool = typer.Option(False, "--explain/--no-explain"),
    sample_dir: Path | None = typer.Option(None, "--sample-dir"),
) -> None:
    """Calibrated onset probability using only data before the cutoff T."""

    if horizon not in HORIZONS_HOURS:
        raise typer.BadParameter(f"horizon must be one of {HORIZONS_HOURS}")
    cohort = load_cohort(sample_dir)
    try:
        stay = cohort.patient(patient)
    except KeyError as exc:
        raise typer.BadParameter(f"unknown patient {patient}") from exc
    if stay.comfort_care:
        console.print(f"{patient} is comfort-care and is excluded from prediction.")
        _print_disclaimer()
        raise typer.Exit(code=2)
    cutoff = cohort.cutoff_for(patient)
    result = predict_at(
        stay,
        cohort.events_for(patient),
        horizon_hours=horizon,
        cutoff=cutoff,
    )
    console.print("[bold]delirium-watch predict[/bold]")
    console.print(f"patient: {patient}  role: {stay.role}")
    console.print(f"horizon: {horizon}h  cutoff T: {cutoff.isoformat()}")
    console.print("Hard temporal cutoff: features use only events with timestamp <= T.")
    latest = result["latest_used"]
    console.print(f"latest used timestamp: {latest}")
    if latest > cutoff:  # pragma: no cover - would be a pipeline bug
        console.print("LEAKAGE: a used event is after T")
        raise typer.Exit(code=1)
    console.print(f"calibrated P(onset by T+{horizon}h): {float(result['probability']):.3f}")
    console.print(
        f"raw logit: {float(result['raw_logit']):.3f}  "
        f"temperature: {float(result['temperature']):.2f}  "
        "(Brier is reported by `make eval`, not a raw score)"
    )
    if explain:
        attr = result["attribution"]
        feats = result["features"]
        table = Table(title="Attribution across three streams (logit contribution)")
        table.add_column("stream")
        table.add_column("contribution", justify="right")
        table.add_column("features")
        table.add_row(
            "physio",
            f"{float(attr['physio']):+.3f}",
            f"hr_last={feats.get('hr_last_raw', feats['hr_last'] + 80):.1f}  "
            f"hr_delta={feats['hr_delta']:.1f}  "
            f"rass={feats['rass_last']:.1f}  "
            f"temp_c={feats.get('temp_c_raw', feats['temp_c'] + 37):.1f}",
        )
        table.add_row(
            "meds",
            f"{float(attr['meds']):+.3f}",
            f"anticholinergic_burden={feats['acb']:.1f}",
        )
        table.add_row(
            "notes",
            f"{float(attr['notes']):+.3f}",
            f"notes_signal={int(feats['notes'])}",
        )
        console.print(table)
        pre = pre_deliric_probability(
            stay, cohort.events_for(patient), cutoff=cutoff, meds=cohort.prescriptions
        )
        epre = e_pre_deliric_probability(stay, cohort.events_for(patient), cutoff=cutoff)
        console.print(
            f"PRE-DELIRIC stand-in (publication formula on synthetic features): "
            f"{float(pre['probability']):.3f}  — {pre['citation']}"
        )
        console.print(
            f"E-PRE-DELIRIC stand-in (publication formula on synthetic features): "
            f"{float(epre['probability']):.3f}  — {epre['citation']}"
        )
    _print_disclaimer()


@app.command("audit-leakage")
def audit_leakage(
    sample_dir: Path | None = typer.Option(None, "--sample-dir"),
) -> None:
    """Detect injected post-cutoff data. Exits non-zero and names feature+timestamp."""

    cohort = load_cohort(sample_dir)
    payload = run_audit(cohort)
    console.print("[bold]delirium-watch audit-leakage[/bold]")
    console.print("Injected post-cutoff probe and committed P005 probe:")
    inj = payload["injected"]
    assert isinstance(inj, dict)
    console.print(
        f"  injected: feature={inj['feature']}  "
        f"timestamp={inj['timestamp']}  subject={inj['subject_id']}"
    )
    for row in payload["committed"]:
        assert isinstance(row, dict)
        console.print(
            f"  committed: feature={row['feature']}  "
            f"timestamp={row['timestamp']}  subject={row['subject_id']}"
        )
    console.print(
        f"OFFENDING FEATURE: {payload['offending_feature']} "
        f"at {payload['offending_timestamp']} "
        f"({payload['offending_subject']})"
    )
    if payload["used_contains_post_cutoff"]:
        console.print("FAIL: a post-cutoff event was placed in `used`.")
    else:
        console.print("Window kept leaked events out of `used`. Source still contains leaks.")
    console.print("FAIL: leakage present. Non-zero exit.")
    _print_disclaimer()
    raise typer.Exit(code=1)


@app.command("eval")
def eval_cmd(
    sample_dir: Path | None = typer.Option(None, "--sample-dir"),
    summary: bool = typer.Option(False, "--summary", help="Alert-burden table only"),
) -> None:
    """Horizon curve, calibration, AUPRC, subgroups, alert-burden, both baselines."""

    cohort = load_cohort(sample_dir)
    payload = evaluate_cohort(cohort)
    if summary:
        console.print("delirium-watch eval  (synthetic cohort only)")
        console.print(str(payload["disclaimer"])[:100])
        h12 = next(row for row in payload["horizon_curve"] if int(row["horizon_hours"]) == 12)
        model = h12["model"]
        console.print(
            f"12h model AUPRC {float(model['auprc']):.3f}  Brier {float(model['brier']):.3f}"
        )
        console.print("Alert-burden (12h) — deployability is here, not AUROC")
        for row in payload["alert_burden_12h"][:4]:
            console.print(
                f"  threshold={row['threshold']:.2f}  alerts={int(row['n_alert'])}  "
                f"PPV={row['ppv']:.3f}  alarms/100-pt-days="
                f"{row['alarms_per_100_patient_days']:.2f}"
            )
    else:
        console.print(format_eval_text(payload))
    _print_disclaimer()


@app.command("demo")
def demo() -> None:
    """Full walkthrough: cohort, labels, predict, leakage audit. No credentials."""

    settings = get_settings()
    console.print("[bold]delirium-watch demo[/bold]  (synthetic only; no credentials)\n")
    cohort = generate_and_write(sample_dir=settings.sample_dir)
    _print_cohort_stats(cohort, settings.sample_dir)
    parquet = settings.sample_dir / "cohort.parquet"
    console.print()
    labels_compare(parquet)
    console.print()
    predict(patient="P001", horizon=12, explain=True, sample_dir=settings.sample_dir)
    console.print()
    console.print("Leakage audit (standalone command exits 1; demo continues after showing it):")
    payload = run_audit(cohort)
    console.print(
        f"  named feature={payload['offending_feature']} "
        f"timestamp={payload['offending_timestamp']} "
        f"subject={payload['offending_subject']}"
    )
    console.print("  `delirium-watch audit-leakage` exits non-zero on this finding.")
    console.print()
    _print_disclaimer()


@app.command("sample-path")
def sample_path() -> None:
    """Print the committed sample directory path."""

    console.print(str(get_settings().sample_dir.resolve()))


if __name__ == "__main__":
    app()
