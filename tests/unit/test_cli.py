from __future__ import annotations

from typer.testing import CliRunner

from delirium_watch.cli import app

runner = CliRunner()


def test_demo_plan_lists_five_designed_paths() -> None:
    result = runner.invoke(app, ["demo-plan", "--dry-run"])
    assert result.exit_code == 0, result.stdout
    assert "P001" in result.stdout
    assert "P002" in result.stdout
    assert "P003" in result.stdout
    assert "P004" in result.stdout
    assert "P005" in result.stdout
    assert "prodrome_positive" in result.stdout
    assert "Research tool only" in result.stdout
    assert "Dry run only" in result.stdout


def test_demo_plan_no_dry_run() -> None:
    result = runner.invoke(app, ["demo-plan", "--no-dry-run"])
    assert result.exit_code == 0
    assert "Dry run only" not in result.stdout


def test_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "delirium-watch" in result.stdout


def test_sample_path() -> None:
    result = runner.invoke(app, ["sample-path"])
    assert result.exit_code == 0
    assert "data/sample" in result.stdout.replace("\\", "/")


def test_demo_data_writes_cohort(tmp_path: object) -> None:
    from pathlib import Path

    dest = Path(str(tmp_path))
    result = runner.invoke(app, ["demo-data", "--dest", str(dest)])
    assert result.exit_code == 0, result.stdout
    assert (dest / "patients.json").is_file()
    assert "50 synthetic patients" in result.stdout
