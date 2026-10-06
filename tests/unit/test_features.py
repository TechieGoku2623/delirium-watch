from __future__ import annotations

from datetime import timedelta

import pytest

from delirium_watch.cohort import load_cohort
from delirium_watch.features import (
    LeakageError,
    anticholinergic_burden,
    leakage_safe_window,
    notes_signal,
)
from delirium_watch.schemas import PredictionConfig, TimedEvent


def test_p005_window_rejects_named_heart_rate() -> None:
    cohort = load_cohort()
    cutoff = cohort.cutoff_for("P005")
    events = cohort.events_for("P005")
    with pytest.raises(LeakageError) as exc:
        leakage_safe_window(events, cutoff, reject=True)
    assert exc.value.finding.feature == "heart_rate"
    assert exc.value.finding.timestamp == cutoff + timedelta(hours=6)
    assert "heart_rate" in str(exc.value)


def test_p005_audit_mode_keeps_leak_out_of_used() -> None:
    cohort = load_cohort()
    cutoff = cohort.cutoff_for("P005")
    result = leakage_safe_window(cohort.events_for("P005"), cutoff, reject=False)
    assert result.rejected
    assert all(event.timestamp <= cutoff for event in result.used)
    assert any(finding.feature == "heart_rate" for finding in result.rejected)


def test_lookback_drops_old_events() -> None:
    cohort = load_cohort()
    cutoff = cohort.cutoff_for("P001")
    pre = [event for event in cohort.events_for("P001") if event.timestamp <= cutoff]
    result = leakage_safe_window(pre, cutoff, lookback_hours=1.0, reject=True)
    assert all(event.timestamp >= cutoff - timedelta(hours=1) for event in result.used)


def test_p003_notes_signal_lost_when_ablated() -> None:
    cohort = load_cohort()
    cutoff = cohort.cutoff_for("P003")
    events = cohort.events_for("P003")
    assert notes_signal(events, cutoff) is True
    without = [e for e in events if e.name != "nursing_note"]
    assert notes_signal(without, cutoff) is False


def test_p002_anticholinergic_burden_high() -> None:
    cohort = load_cohort()
    cutoff = cohort.cutoff_for("P002")
    assert anticholinergic_burden(cohort.events_for("P002"), cutoff) >= 9


def test_horizon_config_accepts_declared_values() -> None:
    for horizon in (6, 12, 24):
        cfg = PredictionConfig(horizon_hours=horizon)  # type: ignore[arg-type]
        assert cfg.horizon_hours == horizon


def test_injected_event_is_rejected() -> None:
    cohort = load_cohort()
    cutoff = cohort.cutoff_for("P001")
    leaked = TimedEvent(
        subject_id="P001",
        stay_id="S001",
        name="future_lab",
        timestamp=cutoff + timedelta(hours=3),
        value=1.0,
    )
    pre = [event for event in cohort.events_for("P001") if event.timestamp <= cutoff]
    with pytest.raises(LeakageError) as exc:
        leakage_safe_window([*pre, leaked], cutoff, reject=True)
    assert exc.value.finding.feature == "future_lab"


def test_acb_skips_null_values() -> None:
    cohort = load_cohort()
    cutoff = cohort.cutoff_for("P002")
    extra = TimedEvent(
        subject_id="P002",
        stay_id="S002",
        name="medication_acb",
        timestamp=cutoff - timedelta(hours=1),
        value=None,
    )
    total = anticholinergic_burden([*cohort.events_for("P002"), extra], cutoff)
    assert total >= 9
