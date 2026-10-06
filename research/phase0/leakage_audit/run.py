"""Inject post-cutoff data and confirm the feature window rejects it."""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

from delirium_watch.cohort import load_cohort
from delirium_watch.features import LeakageError, leakage_safe_window, notes_signal
from delirium_watch.schemas import TimedEvent

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _lib import md_table, write_json  # noqa: E402

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"


def _audit_reject(events: list[TimedEvent], cutoff: object, label: str) -> dict[str, object]:
    try:
        result = leakage_safe_window(events, cutoff, reject=True)  # type: ignore[arg-type]
    except LeakageError as exc:
        finding = exc.finding
        return {
            "case": label,
            "rejected": True,
            "feature": finding.feature,
            "timestamp": finding.timestamp.isoformat(),
            "subject_id": finding.subject_id,
            "used_count": 0,
            "exit_if_used": "would be non-zero",
        }
    leaked_used = [e for e in result.used if e.timestamp > result.cutoff]
    if leaked_used:
        sys.exit(1)
    return {
        "case": label,
        "rejected": False,
        "feature": None,
        "timestamp": None,
        "subject_id": None,
        "used_count": len(result.used),
        "exit_if_used": "clean",
    }


def main() -> None:
    cohort = load_cohort()
    p005 = cohort.patient("P005")
    cutoff_p005 = cohort.cutoff_for("P005")
    p005_events = cohort.events_for("P005")
    p001_events = cohort.events_for("P001")
    cutoff_p001 = cohort.cutoff_for("P001")

    injected = TimedEvent(
        subject_id="P001",
        stay_id=cohort.patient("P001").stay_id,
        name="injected_post_cutoff_lactate",
        timestamp=cutoff_p001 + timedelta(hours=6),
        value=4.2,
    )

    cases = [
        _audit_reject(p005_events, cutoff_p005, "P005 committed post-cutoff heart_rate"),
        _audit_reject(
            [*p001_events, injected],
            cutoff_p001,
            "P001 injected post-cutoff lactate",
        ),
    ]
    # Audit mode: reject=False must still keep leaked events out of `used`.
    audit = leakage_safe_window(p005_events, cutoff_p005, reject=False)
    leaked_in_used = [e for e in audit.used if e.timestamp > cutoff_p005]
    if leaked_in_used:
        print("leakage present in used features", file=sys.stderr)
        sys.exit(1)

    p003_cutoff = cohort.cutoff_for("P003")
    p003_notes = notes_signal(cohort.events_for("P003"), p003_cutoff)
    p003_without_notes = notes_signal(
        [e for e in cohort.events_for("P003") if e.name != "nursing_note"],
        p003_cutoff,
    )

    if not all(case["rejected"] for case in cases):
        print("pipeline failed to reject injected or committed leakage", file=sys.stderr)
        sys.exit(1)

    p005_case = cases[0]
    payload = {
        "pipeline_rejected_leakage": True,
        "offending_feature": p005_case["feature"],
        "offending_timestamp": p005_case["timestamp"],
        "offending_subject": p005_case["subject_id"],
        "n_rejected_on_p005": len(audit.rejected),
        "n_used_on_p005": len(audit.used),
        "p005_cutoff_hours": p005.prediction_cutoff_hours,
        "cases": cases,
        "p003_notes_signal": p003_notes,
        "p003_notes_ablated_signal": p003_without_notes,
        "notes_ablation_loses_p003": p003_notes and not p003_without_notes,
        "nonzero_exit_when_leakage_present": True,
        "gold_source": "Synthetic P005 plus an injected P001 event. Not MIMIC-IV.",
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    write_json(RESULTS / "results.json", payload)
    table = md_table(
        ["case", "rejected", "feature", "timestamp", "subject"],
        [
            [
                str(c["case"]),
                str(c["rejected"]),
                str(c["feature"]),
                str(c["timestamp"]),
                str(c["subject_id"]),
            ]
            for c in cases
        ],
    )
    md = (
        "# leakage_audit results\n\n"
        f"Pipeline rejected leakage: true. Offending feature on P005: "
        f"{p005_case['feature']} at {p005_case['timestamp']}.\n\n"
        f"P003 notes signal: {p003_notes}. After ablating notes: "
        f"{p003_without_notes}. Ablation loses P003: "
        f"{p003_notes and not p003_without_notes}.\n\n"
        f"{table}\n"
    )
    (RESULTS / "results.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
