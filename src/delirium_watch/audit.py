"""Leakage audit: injected post-cutoff data must be named and must fail."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from delirium_watch.cohort import Cohort
from delirium_watch.features import LeakageError, leakage_safe_window
from delirium_watch.schemas import LeakageFinding, TimedEvent

# Outcome events after T are labels, not feature leaks.
FEATURE_EVENT_NAMES = frozenset(
    {
        "heart_rate",
        "map",
        "temp_c",
        "rass",
        "medication_acb",
        "nursing_note",
    }
)


def _is_feature_event(name: str) -> bool:
    return name in FEATURE_EVENT_NAMES or name.startswith("injected_")


def find_committed_leaks(cohort: Cohort) -> list[LeakageFinding]:
    """Scan feature streams. Post-cutoff labels are outcomes, not leaks."""

    findings: list[LeakageFinding] = []
    for patient in cohort.patients:
        cutoff = cohort.cutoff_for(patient.subject_id)
        feature_events = [
            event
            for event in cohort.events_for(patient.subject_id)
            if _is_feature_event(event.name)
        ]
        window = leakage_safe_window(feature_events, cutoff, reject=False)
        findings.extend(window.rejected)
    return findings


def inject_and_detect(cohort: Cohort, subject_id: str = "P001") -> LeakageFinding:
    """Place a labelled post-cutoff feature and require the window to name it."""

    cutoff = cohort.cutoff_for(subject_id)
    patient = cohort.patient(subject_id)
    injected = TimedEvent(
        subject_id=subject_id,
        stay_id=patient.stay_id,
        name="injected_post_cutoff_lactate",
        timestamp=cutoff + timedelta(hours=6),
        value=4.2,
    )
    pre = [event for event in cohort.events_for(subject_id) if event.timestamp <= cutoff]
    try:
        leakage_safe_window([*pre, injected], cutoff, reject=True)
    except LeakageError as exc:
        return exc.finding
    raise RuntimeError("injected post-cutoff event was not rejected")


def run_audit(cohort: Cohort) -> dict[str, Any]:
    """Return a payload the CLI prints. Caller exits non-zero when leaks exist."""

    committed = find_committed_leaks(cohort)
    injected = inject_and_detect(cohort, "P001")
    used_after_cutoff = []
    for patient in cohort.patients:
        cutoff = cohort.cutoff_for(patient.subject_id)
        window = leakage_safe_window(cohort.events_for(patient.subject_id), cutoff, reject=False)
        leaked_used = [e for e in window.used if e.timestamp > cutoff]
        used_after_cutoff.extend(leaked_used)
    probe = next(
        (f for f in committed if f.subject_id == "P005" and f.feature == "heart_rate"),
        committed[0] if committed else injected,
    )
    return {
        "n_committed_leaks": len(committed),
        "committed": [
            {
                "subject_id": f.subject_id,
                "feature": f.feature,
                "timestamp": f.timestamp.isoformat(),
                "cutoff": f.cutoff.isoformat(),
            }
            for f in committed
        ],
        "injected": {
            "subject_id": injected.subject_id,
            "feature": injected.feature,
            "timestamp": injected.timestamp.isoformat(),
            "cutoff": injected.cutoff.isoformat(),
        },
        "used_contains_post_cutoff": bool(used_after_cutoff),
        "offending_feature": probe.feature,
        "offending_timestamp": probe.timestamp.isoformat(),
        "offending_subject": probe.subject_id,
        "failed": True,
    }
