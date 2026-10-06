"""Pairwise agreement of three delirium label definitions."""

from __future__ import annotations

import sys
from pathlib import Path

from delirium_watch.cohort import load_cohort
from delirium_watch.exclusions import included_patients
from delirium_watch.labels import all_labels, cohen_kappa, percent_agreement

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _lib import md_table, pct, write_json  # noqa: E402

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
PAIRS = (("cam_icu", "antipsychotic"), ("cam_icu", "restraint"), ("antipsychotic", "restraint"))
KAPPA_THRESHOLD = 0.60


def main() -> None:
    cohort = load_cohort()
    patients = included_patients(cohort.patients)
    rows: list[dict[str, object]] = []
    kappas: list[float] = []
    table_rows: list[list[str]] = []
    for left, right in PAIRS:
        pairs: list[tuple[bool, bool]] = []
        for patient in patients:
            calls = all_labels(
                patient,
                assessments=cohort.chartevents,
                meds=cohort.prescriptions,
                procedures=cohort.procedureevents,
            )
            pairs.append((calls[left].positive, calls[right].positive))  # type: ignore[index]
        kappa = cohen_kappa(pairs)
        agree = percent_agreement(pairs)
        both = sum(1 for a, b in pairs if a and b)
        left_only = sum(1 for a, b in pairs if a and not b)
        right_only = sum(1 for a, b in pairs if (not a) and b)
        neither = sum(1 for a, b in pairs if (not a) and not b)
        kappas.append(kappa)
        rec = {
            "left": left,
            "right": right,
            "n": len(pairs),
            "both_positive": both,
            "left_only": left_only,
            "right_only": right_only,
            "neither": neither,
            "percent_agreement": agree,
            "kappa": kappa,
        }
        rows.append(rec)
        table_rows.append(
            [
                f"{left} vs {right}",
                str(len(pairs)),
                str(both),
                str(left_only),
                str(right_only),
                str(neither),
                pct(agree),
                pct(kappa),
            ]
        )

    mean_kappa = sum(kappas) / len(kappas)
    dominates = mean_kappa < KAPPA_THRESHOLD
    decision = (
        "Label choice dominates downstream results. Mean pairwise kappa is "
        f"{mean_kappa:.3f} (< {KAPPA_THRESHOLD:.2f}). Phase 2 must treat the "
        "three definitions as competing endpoints, not pick a silent primary."
        if dominates
        else (
            f"Labels agree enough to share a primary endpoint (mean kappa "
            f"{mean_kappa:.3f} ≥ {KAPPA_THRESHOLD:.2f}). Still report all three."
        )
    )
    positives = {"cam_icu": 0, "antipsychotic": 0, "restraint": 0}
    for patient in patients:
        calls = all_labels(
            patient,
            assessments=cohort.chartevents,
            meds=cohort.prescriptions,
            procedures=cohort.procedureevents,
        )
        for name, call in calls.items():
            if call.positive:
                positives[name] += 1

    payload = {
        "n_included": len(patients),
        "n_raw": len(cohort.patients),
        "kappa_threshold": KAPPA_THRESHOLD,
        "mean_kappa": mean_kappa,
        "label_choice_dominates": dominates,
        "decision": decision,
        "positives": positives,
        "pairs": rows,
        "gold_source": (
            "Synthetic seeded cohort (seed 0). Not MIMIC-IV. Replacing this "
            "measurement with credentialed MIMIC-IV CAM-ICU / med / restraint "
            "extracts is the measurement that would retire that limitation."
        ),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    write_json(RESULTS / "results.json", payload)
    table = md_table(
        [
            "pair",
            "n",
            "both+",
            "left only",
            "right only",
            "neither",
            "agreement",
            "kappa",
        ],
        table_rows,
    )
    md = (
        "# label_agreement results\n\n"
        f"n included = {len(patients)} (raw {len(cohort.patients)}; "
        "comfort-care excluded).\n\n"
        f"Mean pairwise kappa = {mean_kappa:.3f}. "
        f"Label choice dominates: {dominates}.\n\n"
        f"{decision}\n\n"
        f"{table}\n"
    )
    (RESULTS / "results.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
