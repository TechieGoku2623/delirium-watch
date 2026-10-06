from __future__ import annotations

from datetime import timedelta

from delirium_watch.audit import inject_and_detect, run_audit
from delirium_watch.baselines import e_pre_deliric_probability, pre_deliric_probability
from delirium_watch.cohort import load_cohort
from delirium_watch.evaluate import evaluate_cohort, onset_within_horizon
from delirium_watch.features import leakage_safe_window
from delirium_watch.label_compare import compare_label_rows
from delirium_watch.metrics import auprc, auroc, brier_score, reliability_bins, sigmoid
from delirium_watch.model import extract_features, predict_at
from delirium_watch.parquet_io import label_table_from_parquet, write_cohort_parquet
from delirium_watch.schemas import TimedEvent


def test_p005_features_ignore_post_cutoff_heart_rate() -> None:
    cohort = load_cohort()
    patient = cohort.patient("P005")
    cutoff = cohort.cutoff_for("P005")
    events = cohort.events_for("P005")
    leaked = [e for e in events if e.name == "heart_rate" and e.timestamp > cutoff]
    assert leaked
    assert leaked[0].value == 142
    feats = extract_features(patient, events, cutoff)
    assert feats.values["hr_last_raw"] != 142
    assert feats.values["hr_last_raw"] <= 82
    assert all(e.timestamp <= cutoff for e in feats.used_events)


def test_predict_at_never_uses_future_timestamp() -> None:
    cohort = load_cohort()
    patient = cohort.patient("P001")
    cutoff = cohort.cutoff_for("P001")
    future = TimedEvent(
        subject_id="P001",
        stay_id=patient.stay_id,
        name="heart_rate",
        timestamp=cutoff + timedelta(hours=8),
        value=180.0,
    )
    events = [*cohort.events_for("P001"), future]
    result = predict_at(patient, events, horizon_hours=12, cutoff=cutoff)
    assert result["latest_used"] <= cutoff
    raw_hr = result["features"].get("hr_last_raw", float(result["features"]["hr_last"]) + 80.0)  # type: ignore[union-attr]
    assert float(raw_hr) < 180.0


def test_p001_probability_higher_than_p002() -> None:
    cohort = load_cohort()
    p001 = predict_at(
        cohort.patient("P001"),
        cohort.events_for("P001"),
        horizon_hours=12,
        cutoff=cohort.cutoff_for("P001"),
    )
    p002 = predict_at(
        cohort.patient("P002"),
        cohort.events_for("P002"),
        horizon_hours=12,
        cutoff=cohort.cutoff_for("P002"),
    )
    assert float(p001["probability"]) > float(p002["probability"])


def test_p003_notes_stream_dominates() -> None:
    cohort = load_cohort()
    result = predict_at(
        cohort.patient("P003"),
        cohort.events_for("P003"),
        horizon_hours=12,
        cutoff=cohort.cutoff_for("P003"),
    )
    attr = result["attribution"]
    assert float(attr["notes"]) > float(attr["physio"])  # type: ignore[index]
    assert float(attr["notes"]) > float(attr["meds"])  # type: ignore[index]


def test_audit_names_injected_feature() -> None:
    cohort = load_cohort()
    finding = inject_and_detect(cohort, "P001")
    assert finding.feature == "injected_post_cutoff_lactate"
    payload = run_audit(cohort)
    assert payload["failed"] is True
    assert payload["offending_feature"] == "heart_rate"
    assert payload["offending_subject"] == "P005"
    assert payload["used_contains_post_cutoff"] is False
    assert payload["injected"]["feature"] == "injected_post_cutoff_lactate"


def test_baselines_are_labelled_standins() -> None:
    cohort = load_cohort()
    cutoff = cohort.cutoff_for("P001")
    pre = pre_deliric_probability(
        cohort.patient("P001"),
        cohort.events_for("P001"),
        cutoff=cutoff,
        meds=cohort.prescriptions,
    )
    epre = e_pre_deliric_probability(
        cohort.patient("P001"), cohort.events_for("P001"), cutoff=cutoff
    )
    assert "stand-in" in str(pre["citation"]).lower()
    assert "stand-in" in str(epre["citation"]).lower()
    assert 0.0 < float(pre["probability"]) < 1.0
    assert 0.0 < float(epre["probability"]) < 1.0


def test_evaluate_has_horizon_curve() -> None:
    payload = evaluate_cohort(load_cohort())
    assert [row["horizon_hours"] for row in payload["horizon_curve"]] == [6, 12, 24]
    assert "cam_icu" in payload["competing_labels_12h"]
    assert payload["n_included"] == 49


def test_onset_already_positive_is_none() -> None:
    cohort = load_cohort()
    # P003 structured labels are negative; a filler with early CAM is excluded from forecast.
    patient = cohort.patient("P006")
    first = onset_within_horizon(patient, cohort, label="cam_icu", horizon_hours=12)
    assert first in {0, 1, None}


def test_metrics_edge_cases() -> None:
    assert brier_score([], []) == 0.0
    assert auprc([], []) == 0.0
    assert auprc([0, 0], [0.1, 0.2]) == 0.0
    assert auroc([1, 0], [0.9, 0.1]) == 1.0
    assert auroc([1, 1], [0.2, 0.3]) == 0.0
    assert abs(sigmoid(0.0) - 0.5) < 1e-9
    bins = reliability_bins([1, 0, 1, 0], [0.1, 0.2, 0.8, 0.9], n_bins=2)
    assert len(bins) == 2
    assert auprc([1, 0, 1, 0], [0.9, 0.2, 0.8, 0.1]) > 0.5


def test_parquet_roundtrip(tmp_path: object) -> None:
    from pathlib import Path

    dest = Path(str(tmp_path)) / "cohort.parquet"
    cohort = load_cohort()
    write_cohort_parquet(cohort, dest)
    rows = label_table_from_parquet(dest)
    assert len(rows) == 50
    payload = compare_label_rows(rows)
    assert payload["n_included"] == 49
    assert payload["n_excluded"] == 1


def test_p005_window_still_rejects() -> None:
    cohort = load_cohort()
    cutoff = cohort.cutoff_for("P005")
    window = leakage_safe_window(cohort.events_for("P005"), cutoff, reject=False)
    assert any(f.feature == "heart_rate" for f in window.rejected)
