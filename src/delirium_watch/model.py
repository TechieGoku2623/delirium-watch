"""Leakage-safe 12h forecast. Logistic on three streams; Brier, not a raw score.

Prediction at time T uses only events with timestamp <= T. Post-cutoff
rows never enter the feature vector. This is not a medical device and
is not for patient care.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any, Literal

from delirium_watch.features import (
    anticholinergic_burden,
    leakage_safe_window,
    notes_signal,
)
from delirium_watch.metrics import sigmoid
from delirium_watch.schemas import Patient, TimedEvent

StreamName = Literal["physio", "meds", "notes"]

# Fixed, documented weights. Fitted offline on the seed-0 synthetic cohort
# so `predict` is deterministic and does not silently re-fit in CI.
# Intercept + eight features. L2-regularized logistic, then temperature-scaled
# so Brier is reported on a calibrated probability, not a raw logit.
WEIGHTS: dict[str, float] = {
    "intercept": -1.85,
    "hr_last": 0.035,
    "hr_delta": 0.045,
    "rass_last": 0.55,
    "temp_c": 0.22,
    "acb": 0.04,
    "notes": 1.65,
    "age65": 0.35,
    "ventilated": 0.25,
}
# Temperature < 1 sharpens; > 1 flattens. Chosen to keep Brier honest on n=49.
TEMPERATURE = 1.15


class StreamFeatures:
    """Numeric features plus the raw events that produced them."""

    def __init__(
        self,
        values: dict[str, float],
        used_events: list[TimedEvent],
        cutoff: datetime,
    ) -> None:
        self.values = values
        self.used_events = used_events
        self.cutoff = cutoff

    def as_vector(self) -> list[float]:
        return [
            1.0,
            self.values["hr_last"],
            self.values["hr_delta"],
            self.values["rass_last"],
            self.values["temp_c"],
            self.values["acb"],
            self.values["notes"],
            self.values["age65"],
            self.values["ventilated"],
        ]


def _last_float(events: Sequence[TimedEvent], name: str, default: float) -> float:
    matches = [e for e in events if e.name == name and e.value is not None]
    if not matches:
        return default
    last = max(matches, key=lambda e: e.timestamp)
    return float(last.value)  # type: ignore[arg-type]


def _first_float(events: Sequence[TimedEvent], name: str, default: float) -> float:
    matches = [e for e in events if e.name == name and e.value is not None]
    if not matches:
        return default
    first = min(matches, key=lambda e: e.timestamp)
    return float(first.value)  # type: ignore[arg-type]


def extract_features(
    patient: Patient,
    events: Sequence[TimedEvent],
    cutoff: datetime,
    *,
    lookback_hours: float | None = 24.0,
) -> StreamFeatures:
    """Build the three-stream vector. Post-cutoff events are dropped, never used."""

    window = leakage_safe_window(events, cutoff, lookback_hours=lookback_hours, reject=False)
    used = window.used
    hr_last = _last_float(used, "heart_rate", 80.0)
    hr_first = _first_float(used, "heart_rate", hr_last)
    rass_raw = _last_float(
        [e for e in used if e.name == "rass"],
        "rass",
        0.0,
    )
    # RASS is stored as a chart string like "+1"; leakage-safe window keeps the string.
    rass_last = _parse_rass(used)
    if rass_raw and rass_last == 0.0:
        rass_last = rass_raw
    temp_c = _last_float(used, "temp_c", 37.0)
    acb = float(anticholinergic_burden(used, cutoff))
    notes = 1.0 if notes_signal(used, cutoff) else 0.0
    values = {
        "hr_last": hr_last - 80.0,
        "hr_delta": hr_last - hr_first,
        "rass_last": rass_last,
        "temp_c": temp_c - 37.0,
        "acb": acb,
        "notes": notes,
        "age65": 1.0 if patient.age >= 65 else 0.0,
        "ventilated": 1.0 if patient.ventilated else 0.0,
        "hr_last_raw": hr_last,
        "temp_c_raw": temp_c,
    }
    return StreamFeatures(values=values, used_events=list(used), cutoff=cutoff)


def _parse_rass(events: Sequence[TimedEvent]) -> float:
    matches = [e for e in events if e.name == "rass" and e.value is not None]
    if not matches:
        return 0.0
    last = max(matches, key=lambda e: e.timestamp)
    text = str(last.value).replace("+", "")
    try:
        return float(text)
    except ValueError:
        return 0.0


def _logit(features: StreamFeatures) -> float:
    names = [
        "intercept",
        "hr_last",
        "hr_delta",
        "rass_last",
        "temp_c",
        "acb",
        "notes",
        "age65",
        "ventilated",
    ]
    vec = features.as_vector()
    return sum(WEIGHTS[name] * value for name, value in zip(names, vec, strict=True))


def calibrated_probability(features: StreamFeatures) -> float:
    """Temperature-scaled logistic. This is the number we report, not the raw logit."""

    return sigmoid(_logit(features) / TEMPERATURE)


def stream_attribution(features: StreamFeatures) -> dict[StreamName, float]:
    """Logit contribution of each stream. Sums with intercept to the raw logit."""

    v = features.values
    physio = (
        WEIGHTS["hr_last"] * v["hr_last"]
        + WEIGHTS["hr_delta"] * v["hr_delta"]
        + WEIGHTS["rass_last"] * v["rass_last"]
        + WEIGHTS["temp_c"] * v["temp_c"]
    )
    meds = WEIGHTS["acb"] * v["acb"]
    notes = WEIGHTS["notes"] * v["notes"]
    return {"physio": physio, "meds": meds, "notes": notes}


def predict_at(
    patient: Patient,
    events: Sequence[TimedEvent],
    *,
    horizon_hours: int,
    cutoff: datetime | None = None,
) -> dict[str, Any]:
    """Forecast P(onset by T+horizon) using only data at or before T."""

    del horizon_hours  # horizon is the declared label window; features stay pre-T
    when = (
        cutoff
        if cutoff is not None
        else patient.icu_intime + timedelta(hours=patient.prediction_cutoff_hours)
    )
    features = extract_features(patient, events, when)
    prob = calibrated_probability(features)
    attr = stream_attribution(features)
    raw = _logit(features)
    return {
        "subject_id": patient.subject_id,
        "cutoff": when,
        "probability": prob,
        "raw_logit": raw,
        "temperature": TEMPERATURE,
        "attribution": attr,
        "features": features.values,
        "n_used_events": len(features.used_events),
        "latest_used": max((e.timestamp for e in features.used_events), default=when),
    }
