from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from delirium_watch.cli import app

runner = CliRunner()


def test_labels_compare(tmp_path: object) -> None:
    dest = Path(str(tmp_path))
    built = runner.invoke(app, ["demo-data", "--dest", str(dest)])
    assert built.exit_code == 0, built.stdout
    result = runner.invoke(app, ["labels", "compare", "--cohort", str(dest / "cohort.parquet")])
    assert result.exit_code == 0, result.stdout
    assert "cam_icu" in result.stdout
    assert "antipsychotic" in result.stdout
    assert "Mean pairwise kappa" in result.stdout
    assert "not for patient care" in result.stdout.lower()


def test_predict_explain_p001() -> None:
    result = runner.invoke(app, ["predict", "--patient", "P001", "--horizon", 12, "--explain"])
    assert result.exit_code == 0, result.stdout
    assert "calibrated P" in result.stdout
    assert "physio" in result.stdout
    assert "meds" in result.stdout
    assert "notes" in result.stdout
    assert "PRE-DELIRIC stand-in" in result.stdout
    assert "timestamp <=" in result.stdout or "timestamp <= T" in result.stdout


def test_predict_unknown_and_bad_horizon() -> None:
    bad_h = runner.invoke(app, ["predict", "--patient", "P001", "--horizon", 9])
    assert bad_h.exit_code != 0
    missing = runner.invoke(app, ["predict", "--patient", "P999", "--horizon", 12])
    assert missing.exit_code != 0


def test_predict_excludes_comfort_care() -> None:
    result = runner.invoke(app, ["predict", "--patient", "P004", "--horizon", 12])
    assert result.exit_code == 2
    assert "comfort-care" in result.stdout


def test_audit_leakage_nonzero() -> None:
    result = runner.invoke(app, ["audit-leakage"])
    assert result.exit_code == 1
    assert "OFFENDING FEATURE" in result.stdout
    assert "heart_rate" in result.stdout or "injected_post_cutoff_lactate" in result.stdout
    assert "FAIL" in result.stdout


def test_eval_and_demo_exit_zero() -> None:
    ev = runner.invoke(app, ["eval"])
    assert ev.exit_code == 0, ev.stdout
    assert "Horizon curve" in ev.stdout
    assert "PRE-DELIRIC" in ev.stdout
    demo = runner.invoke(app, ["demo"])
    assert demo.exit_code == 0, demo.stdout
    assert "50 synthetic patients" in demo.stdout
    assert "P001" in demo.stdout
