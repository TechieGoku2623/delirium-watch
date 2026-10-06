"""Leakage-safe feature window. Built before any model.

Any event timestamped after the prediction cutoff is a leak. The window
either rejects those events (raises) or returns them as named findings.
Tests audit this function; the leakage_audit harness exits non-zero if a
post-cutoff event is ever placed in ``used``.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from delirium_watch.schemas import LeakageFinding, TimedEvent, WindowResult

NOTE_TOKENS: tuple[str, ...] = (
    "oriented x1",
    "pulling at",
    "sundown",
    "not oriented",
    "called for deceased",
)


class LeakageError(Exception):
    """Raised when the pipeline is asked to use post-cutoff data."""

    def __init__(self, finding: LeakageFinding) -> None:
        self.finding = finding
        super().__init__(
            f"Leakage: feature {finding.feature!r} at {finding.timestamp.isoformat()} "
            f"for {finding.subject_id} is after cutoff {finding.cutoff.isoformat()}"
        )


def leakage_safe_window(
    events: Sequence[TimedEvent],
    cutoff: datetime,
    *,
    lookback_hours: float | None = None,
    reject: bool = True,
) -> WindowResult:
    """Return events with ``timestamp <= cutoff`` (and optional lookback).

    Post-cutoff events are never placed in ``used``. If ``reject`` is true
    and any leaked event is present, raise ``LeakageError`` naming the
    offending feature and timestamp. If ``reject`` is false, leaked events
    are listed in ``rejected`` and the caller (the audit harness) must treat
    a non-empty ``used`` leak as a failed pipeline.
    """

    used: list[TimedEvent] = []
    rejected: list[LeakageFinding] = []
    lookback_start = (
        cutoff - timedelta(hours=lookback_hours) if lookback_hours is not None else None
    )
    for event in events:
        if event.timestamp > cutoff:
            rejected.append(
                LeakageFinding(
                    subject_id=event.subject_id,
                    stay_id=event.stay_id,
                    feature=event.name,
                    timestamp=event.timestamp,
                    cutoff=cutoff,
                )
            )
            continue
        if lookback_start is not None and event.timestamp < lookback_start:
            continue
        used.append(event)
    if rejected and reject:
        earliest = min(rejected, key=lambda item: item.timestamp)
        raise LeakageError(earliest)
    return WindowResult(used=used, rejected=rejected, cutoff=cutoff, lookback_hours=lookback_hours)


def notes_signal(events: Sequence[TimedEvent], cutoff: datetime) -> bool:
    """True if a nursing note inside the leakage-safe window carries delirium language."""

    notes = [e for e in events if e.name == "nursing_note"]
    window = leakage_safe_window(notes, cutoff, reject=True)
    for event in window.used:
        text = str(event.value or "").lower()
        if any(token in text for token in NOTE_TOKENS):
            return True
    return False


def anticholinergic_burden(events: Sequence[TimedEvent], cutoff: datetime) -> int:
    """Sum of ACB scores inside the leakage-safe window."""

    meds = [e for e in events if e.name == "medication_acb"]
    window = leakage_safe_window(meds, cutoff, reject=True)
    total = 0
    for event in window.used:
        if event.value is None:
            continue
        total += int(event.value)
    return total
