"""Phase 3 evaluation on the synthetic cohort. Not MIMIC-IV. Not for patient care."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from delirium_watch.baselines import e_pre_deliric_probability, pre_deliric_probability
from delirium_watch.cohort import Cohort
from delirium_watch.exclusions import included_patients, is_excluded
from delirium_watch.labels import all_labels
from delirium_watch.metrics import alert_burden, auprc, auroc, brier_score, reliability_bins
from delirium_watch.model import calibrated_probability, extract_features
from delirium_watch.schemas import LabelName, Patient

HORIZONS = (6, 12, 24)
PRIMARY_LABEL: LabelName = "cam_icu"
ALERT_THRESHOLDS = (0.20, 0.40)


def onset_within_horizon(
    patient: Patient,
    cohort: Cohort,
    *,
    label: LabelName,
    horizon_hours: int,
) -> int | None:
    """1 if first event is in (T, T+H], 0 if later or never, None if already + at T.

    Patients already positive at the cutoff are not forecast targets.
    """

    if is_excluded(patient):
        return None
    calls = all_labels(
        patient,
        assessments=cohort.chartevents,
        meds=cohort.prescriptions,
        procedures=cohort.procedureevents,
    )
    first = calls[label].first_event_hours
    t = patient.prediction_cutoff_hours
    if first is not None and first <= t:
        return None
    if first is None:
        return 0
    return 1 if first <= t + horizon_hours else 0


def _at_risk(
    cohort: Cohort,
    *,
    label: LabelName,
    horizon_hours: int,
) -> list[tuple[Patient, int]]:
    rows: list[tuple[Patient, int]] = []
    for patient in included_patients(cohort.patients):
        y = onset_within_horizon(patient, cohort, label=label, horizon_hours=horizon_hours)
        if y is None:
            continue
        rows.append((patient, y))
    return rows


def _model_probs(cohort: Cohort, patients: Sequence[Patient]) -> list[float]:
    probs: list[float] = []
    for patient in patients:
        cutoff = cohort.cutoff_for(patient.subject_id)
        feats = extract_features(patient, cohort.events_for(patient.subject_id), cutoff)
        probs.append(calibrated_probability(feats))
    return probs


def _baseline_probs(
    cohort: Cohort,
    patients: Sequence[Patient],
    which: str,
) -> list[float]:
    out: list[float] = []
    for patient in patients:
        cutoff = cohort.cutoff_for(patient.subject_id)
        events = cohort.events_for(patient.subject_id)
        if which == "pre":
            payload = pre_deliric_probability(
                patient, events, cutoff=cutoff, meds=cohort.prescriptions
            )
        else:
            payload = e_pre_deliric_probability(patient, events, cutoff=cutoff)
        out.append(float(payload["probability"]))
    return out


def _metric_block(y: Sequence[int], p: Sequence[float], patient_days: float) -> dict[str, Any]:
    return {
        "n": len(y),
        "n_pos": int(sum(y)),
        "prevalence": (sum(y) / len(y)) if y else 0.0,
        "auprc": auprc(y, p),
        "auroc": auroc(y, p),
        "brier": brier_score(y, p),
        "reliability": reliability_bins(y, p),
        "alert_burden": [
            alert_burden(y, p, threshold=th, patient_days=patient_days) for th in ALERT_THRESHOLDS
        ],
    }


def evaluate_cohort(cohort: Cohort) -> dict[str, Any]:
    """Horizon curve, calibration, AUPRC, subgroups, alert-burden, both baselines."""

    horizon_curve: list[dict[str, Any]] = []
    for horizon in HORIZONS:
        risk = _at_risk(cohort, label=PRIMARY_LABEL, horizon_hours=horizon)
        patients = [p for p, _ in risk]
        y = [lab for _, lab in risk]
        days = sum(p.los_hours / 24.0 for p in patients)
        model_p = _model_probs(cohort, patients)
        pre_p = _baseline_probs(cohort, patients, "pre")
        epre_p = _baseline_probs(cohort, patients, "epre")
        horizon_curve.append(
            {
                "horizon_hours": horizon,
                "label": PRIMARY_LABEL,
                "model": _metric_block(y, model_p, days),
                "pre_deliric_standin": _metric_block(y, pre_p, days),
                "e_pre_deliric_standin": _metric_block(y, epre_p, days),
            }
        )

    # Default reporting horizon is 12h.
    risk12 = _at_risk(cohort, label=PRIMARY_LABEL, horizon_hours=12)
    patients12 = [p for p, _ in risk12]
    y12 = [lab for _, lab in risk12]
    p12 = _model_probs(cohort, patients12)
    days12 = sum(p.los_hours / 24.0 for p in patients12)

    subgroups: list[dict[str, Any]] = []
    masks = {
        "age>=65": [p.age >= 65 for p in patients12],
        "age<65": [p.age < 65 for p in patients12],
        "sex=F": [p.sex == "F" for p in patients12],
        "sex=M": [p.sex == "M" for p in patients12],
        "ventilated": [p.ventilated for p in patients12],
        "not_ventilated": [not p.ventilated for p in patients12],
    }
    for name, mask in masks.items():
        yy = [lab for lab, keep in zip(y12, mask, strict=True) if keep]
        pp = [prob for prob, keep in zip(p12, mask, strict=True) if keep]
        sub_days = sum(p.los_hours / 24.0 for p, keep in zip(patients12, mask, strict=True) if keep)
        block = _metric_block(yy, pp, sub_days)
        block["subgroup"] = name
        subgroups.append(block)

    competing: dict[str, Any] = {}
    for label in ("cam_icu", "antipsychotic", "restraint"):
        risk = _at_risk(cohort, label=label, horizon_hours=12)
        pats = [p for p, _ in risk]
        yy = [lab for _, lab in risk]
        pp = _model_probs(cohort, pats)
        competing[label] = _metric_block(yy, pp, sum(p.los_hours / 24.0 for p in pats))

    excluded = [p.subject_id for p in cohort.patients if is_excluded(p)]
    return {
        "disclaimer": (
            "Synthetic cohort only. Not MIMIC-IV. Not a medical device. Not for patient care."
        ),
        "n_raw": len(cohort.patients),
        "n_included": len(included_patients(cohort.patients)),
        "excluded_ids": excluded,
        "primary_label": PRIMARY_LABEL,
        "horizon_curve": horizon_curve,
        "calibration_12h": reliability_bins(y12, p12),
        "subgroups_12h": subgroups,
        "competing_labels_12h": competing,
        "alert_burden_12h": [
            alert_burden(y12, p12, threshold=th, patient_days=days12) for th in ALERT_THRESHOLDS
        ],
        "baselines": "PRE-DELIRIC / E-PRE-DELIRIC are publication-formula stand-ins "
        "on synthetic features, not validated bedside ports.",
    }


def format_eval_text(payload: dict[str, Any]) -> str:
    lines = [
        "delirium-watch evaluation (synthetic cohort)",
        payload["disclaimer"],
        "",
        f"raw n={payload['n_raw']}  included n={payload['n_included']}  "
        f"excluded={', '.join(payload['excluded_ids']) or '(none)'}",
        f"primary label: {payload['primary_label']}  (three defs remain competing)",
        "",
        "Horizon curve (AUPRC / Brier)",
        f"{'H':>4}  {'n':>4}  {'n+':>4}  {'model AUPRC':>12}  {'model Brier':>12}  "
        f"{'PRE-DELIRIC':>12}  {'E-PRE-DELIRIC':>13}",
    ]
    for row in payload["horizon_curve"]:
        m = row["model"]
        pre = row["pre_deliric_standin"]
        epre = row["e_pre_deliric_standin"]
        lines.append(
            f"{row['horizon_hours']:>4}  {m['n']:>4}  {m['n_pos']:>4}  "
            f"{m['auprc']:>12.3f}  {m['brier']:>12.3f}  "
            f"{pre['auprc']:>12.3f}  {epre['auprc']:>13.3f}"
        )
    lines.append("")
    lines.append("Calibration (12h, reliability bins)")
    lines.append(f"{'bin':>8}  {'n':>4}  {'mean p':>8}  {'mean y':>8}")
    for bin_row in payload["calibration_12h"]:
        lines.append(
            f"{bin_row['lo']:.1f}-{bin_row['hi']:.1f}  {int(bin_row['n']):>4}  "
            f"{bin_row['mean_p']:>8.3f}  {bin_row['mean_y']:>8.3f}"
        )
    lines.append("")
    lines.append("Subgroup table (12h, model)")
    lines.append(f"{'subgroup':<16}  {'n':>4}  {'n+':>4}  {'AUPRC':>7}  {'Brier':>7}")
    for sub in payload["subgroups_12h"]:
        lines.append(
            f"{sub['subgroup']:<16}  {sub['n']:>4}  {sub['n_pos']:>4}  "
            f"{sub['auprc']:>7.3f}  {sub['brier']:>7.3f}"
        )
    lines.append("")
    lines.append("Alert-burden (12h)")
    for row in payload["alert_burden_12h"]:
        lines.append(
            f"  threshold={row['threshold']:.2f}  alerts={int(row['n_alert'])}  "
            f"PPV={row['ppv']:.3f}  alarms/100-pt-days={row['alarms_per_100_patient_days']:.2f}"
        )
    lines.append("")
    lines.append("Competing labels at 12h (same model, different endpoint)")
    for name, block in payload["competing_labels_12h"].items():
        lines.append(
            f"  {name:<14} n={block['n']}  n+={block['n_pos']}  "
            f"AUPRC={block['auprc']:.3f}  Brier={block['brier']:.3f}"
        )
    lines.append("")
    lines.append(str(payload["baselines"]))
    lines.append("PRE-DELIRIC / E-PRE-DELIRIC AUPRC are stand-ins, not published MIMIC numbers.")
    return "\n".join(lines)
