"""Class balance, exclusions, event timing, and horizon-specific rates."""

from __future__ import annotations

import statistics
import sys
from pathlib import Path

from delirium_watch import HORIZONS_HOURS
from delirium_watch.cohort import load_cohort
from delirium_watch.exclusions import excluded_patients, included_patients
from delirium_watch.labels import all_labels
from delirium_watch.warehouse import connect_sample

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _lib import md_table, pct, write_json  # noqa: E402

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    return float(statistics.median(values))


def main() -> None:
    cohort = load_cohort()
    included = included_patients(cohort.patients)
    excluded = excluded_patients(cohort.patients)
    con = connect_sample()
    duck_n = int(con.execute("SELECT COUNT(*) FROM patients").fetchone()[0])
    duck_excl = int(con.execute("SELECT COUNT(*) FROM patients WHERE comfort_care").fetchone()[0])

    per_label: dict[str, dict[str, object]] = {}
    table_rows: list[list[str]] = []
    for name in ("cam_icu", "antipsychotic", "restraint"):
        calls = [
            all_labels(
                patient,
                assessments=cohort.chartevents,
                meds=cohort.prescriptions,
                procedures=cohort.procedureevents,
            )[name]  # type: ignore[index]
            for patient in included
        ]
        times = [c.first_event_hours for c in calls if c.first_event_hours is not None]
        n_pos = sum(1 for c in calls if c.positive)
        horizon_rates: dict[str, float] = {}
        for horizon in HORIZONS_HOURS:
            n_h = sum(
                1
                for c in calls
                if c.first_event_hours is not None and c.first_event_hours <= horizon
            )
            horizon_rates[str(horizon)] = n_h / len(included) if included else 0.0
        per_label[name] = {
            "n_positive": n_pos,
            "prevalence": n_pos / len(included) if included else 0.0,
            "median_hours_to_event": _median(times),
            "n_with_timing": len(times),
            "horizon_prevalence": horizon_rates,
        }
        med = _median(times)
        table_rows.append(
            [
                name,
                str(n_pos),
                pct(n_pos / len(included) if included else 0.0),
                f"{med:.1f}" if med is not None else "unmeasured",
                pct(horizon_rates["6"]),
                pct(horizon_rates["12"]),
                pct(horizon_rates["24"]),
            ]
        )

    payload = {
        "n_raw": len(cohort.patients),
        "n_included": len(included),
        "n_excluded": len(excluded),
        "excluded_ids": [p.subject_id for p in excluded],
        "duckdb_n_patients": duck_n,
        "duckdb_n_comfort_care": duck_excl,
        "horizons_hours": list(HORIZONS_HOURS),
        "labels": per_label,
        "gold_source": (
            "Synthetic seeded cohort (seed 0). MIMIC-IV incidence is unmeasured "
            "until a credentialed extract is run."
        ),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    write_json(RESULTS / "results.json", payload)
    table = md_table(
        [
            "label",
            "n+",
            "prevalence",
            "median hours to event",
            "rate ≤6h",
            "rate ≤12h",
            "rate ≤24h",
        ],
        table_rows,
    )
    md = (
        "# base_rate results\n\n"
        f"Raw n = {len(cohort.patients)}. Included n = {len(included)}. "
        f"Excluded (comfort care) n = {len(excluded)} "
        f"({', '.join(p.subject_id for p in excluded) or 'none'}).\n\n"
        f"DuckDB row count matches JSON: {duck_n == len(cohort.patients)}.\n\n"
        f"{table}\n"
    )
    (RESULTS / "results.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
