"""Three competing delirium labels over a stay.

Pairwise disagreement on the synthetic cohort is the Phase 0 question:
if CAM-ICU-like assessments, antipsychotic administration, and restraint
orders do not agree, label choice dominates every downstream number.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from delirium_watch.schemas import (
    ChartEvent,
    LabelCall,
    LabelName,
    Patient,
    Prescription,
    ProcedureEvent,
)

ANTIPSYCHOTICS: frozenset[str] = frozenset(
    {
        "haloperidol",
        "quetiapine",
        "olanzapine",
        "risperidone",
        "ziprasidone",
        "aripiprazole",
    }
)


def hours_since_intime(intime: datetime, when: datetime) -> float:
    return (when - intime).total_seconds() / 3600.0


def cam_icu_label(patient: Patient, assessments: Sequence[ChartEvent]) -> LabelCall:
    positives = [
        ev
        for ev in assessments
        if ev.stay_id == patient.stay_id and ev.item == "cam_icu" and ev.value.lower() == "positive"
    ]
    first = None
    if positives:
        first_ev = min(positives, key=lambda ev: ev.charttime)
        first = hours_since_intime(patient.icu_intime, first_ev.charttime)
    return LabelCall(
        subject_id=patient.subject_id,
        stay_id=patient.stay_id,
        label="cam_icu",
        positive=bool(positives),
        first_event_hours=first,
    )


def antipsychotic_label(patient: Patient, meds: Sequence[Prescription]) -> LabelCall:
    hits = [
        ev for ev in meds if ev.stay_id == patient.stay_id and ev.drug.lower() in ANTIPSYCHOTICS
    ]
    first = None
    if hits:
        first_ev = min(hits, key=lambda ev: ev.starttime)
        first = hours_since_intime(patient.icu_intime, first_ev.starttime)
    return LabelCall(
        subject_id=patient.subject_id,
        stay_id=patient.stay_id,
        label="antipsychotic",
        positive=bool(hits),
        first_event_hours=first,
    )


def restraint_label(patient: Patient, procedures: Sequence[ProcedureEvent]) -> LabelCall:
    hits = [
        ev for ev in procedures if ev.stay_id == patient.stay_id and ev.item.lower() == "restraint"
    ]
    first = None
    if hits:
        first_ev = min(hits, key=lambda ev: ev.starttime)
        first = hours_since_intime(patient.icu_intime, first_ev.starttime)
    return LabelCall(
        subject_id=patient.subject_id,
        stay_id=patient.stay_id,
        label="restraint",
        positive=bool(hits),
        first_event_hours=first,
    )


def label_by_name(
    name: LabelName,
    patient: Patient,
    *,
    assessments: Sequence[ChartEvent],
    meds: Sequence[Prescription],
    procedures: Sequence[ProcedureEvent],
) -> LabelCall:
    if name == "cam_icu":
        return cam_icu_label(patient, assessments)
    if name == "antipsychotic":
        return antipsychotic_label(patient, meds)
    return restraint_label(patient, procedures)


def all_labels(
    patient: Patient,
    *,
    assessments: Sequence[ChartEvent],
    meds: Sequence[Prescription],
    procedures: Sequence[ProcedureEvent],
) -> dict[LabelName, LabelCall]:
    return {
        "cam_icu": cam_icu_label(patient, assessments),
        "antipsychotic": antipsychotic_label(patient, meds),
        "restraint": restraint_label(patient, procedures),
    }


def cohen_kappa(pairs: Sequence[tuple[bool, bool]]) -> float:
    """Cohen's kappa for two binary raters. 0.0 when n=0."""

    n = len(pairs)
    if n == 0:
        return 0.0
    both = sum(1 for a, b in pairs if a and b)
    a_only = sum(1 for a, b in pairs if a and not b)
    b_only = sum(1 for a, b in pairs if (not a) and b)
    neither = sum(1 for a, b in pairs if (not a) and not b)
    po = (both + neither) / n
    p_a = (both + a_only) / n
    p_b = (both + b_only) / n
    pe = p_a * p_b + (1 - p_a) * (1 - p_b)
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def percent_agreement(pairs: Sequence[tuple[bool, bool]]) -> float:
    if not pairs:
        return 0.0
    return sum(1 for a, b in pairs if a == b) / len(pairs)
