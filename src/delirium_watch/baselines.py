"""Published-formula stand-ins: PRE-DELIRIC and E-PRE-DELIRIC.

Coefficients are transcribed from the publications and applied to
*synthetic* features. They are not a validated port of the bedside
calculators and are not for patient care.

Sources
-------
PRE-DELIRIC
    van den Boogaard et al., BMJ 2012;344:e420. Ten predictors collected
    within 24h of ICU admission.
E-PRE-DELIRIC
    Wassenaar et al., Intensive Care Med 2015;41:1048–1056. Predictors
    available at ICU admission.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from delirium_watch.metrics import sigmoid
from delirium_watch.model import StreamFeatures, extract_features
from delirium_watch.schemas import Patient, Prescription, TimedEvent

# van den Boogaard et al. BMJ 2012;344:e420 — commonly reproduced coefficients.
# Admission group: surgical=0 (reference), medical=0.24, trauma=1.05, neuro=0.29.
PRE_DELIRIC_INTERCEPT = -6.31
PRE_DELIRIC = {
    "age": 0.04,
    "apache": 0.06,
    "admission_medical": 0.24,
    "admission_trauma": 1.05,
    "admission_neuro": 0.29,
    "coma": 0.55,
    "infection": 1.05,
    "acidosis": 0.29,
    "sedatives": 0.65,
    "urea": 0.02,
    "urgent": 0.40,
    "morphine": 0.41,
}

# Wassenaar et al. Intensive Care Med 2015;41:1048–1056.
E_PRE_DELIRIC_INTERCEPT = -3.92
E_PRE_DELIRIC = {
    "age": 0.02,
    "cognitive": 0.91,
    "alcohol": 0.39,
    "admission_medical": 0.26,
    "admission_trauma": 0.75,
    "admission_neuro": 0.77,
    "urgent": 0.50,
    "map": -0.006,
    "steroids": 0.34,
    "respiratory_failure": 0.53,
    "urea": 0.015,
}

# Unmeasured labs on the synthetic cohort. Documented stand-ins, not imputations
# presented as measured values.
UREA_STANDIN_MMOL = 7.0
MAP_STANDIN = 80.0


def _apache_standin(patient: Patient, features: StreamFeatures) -> float:
    """Crude APACHE-II-like severity from synthetic vitals. Not a real APACHE."""

    hr = features.values["hr_last"]
    temp = features.values["temp_c"]
    score = 5.0
    score += max(0.0, (hr - 110.0) / 10.0) * 2.0
    score += max(0.0, temp - 38.0) * 3.0
    score += 4.0 if patient.ventilated else 0.0
    score += max(0.0, (patient.age - 45) / 10.0) * 2.0
    return min(40.0, score)


def _infection(features: StreamFeatures) -> float:
    return 1.0 if features.values["temp_c"] >= 38.3 else 0.0


def _coma(features: StreamFeatures) -> float:
    return 1.0 if features.values["rass_last"] <= -4 else 0.0


def _morphine(meds: Sequence[Prescription], cutoff: datetime) -> float:
    for rx in meds:
        if rx.starttime <= cutoff and "morphine" in rx.drug.lower():
            return 1.0
    return 0.0


def _sedative(meds: Sequence[Prescription], cutoff: datetime) -> float:
    names = ("midazolam", "lorazepam", "propofol", "dexmedetomidine")
    for rx in meds:
        if rx.starttime <= cutoff and any(n in rx.drug.lower() for n in names):
            return 1.0
    return 0.0


def pre_deliric_probability(
    patient: Patient,
    events: Sequence[TimedEvent],
    *,
    cutoff: datetime,
    meds: Sequence[Prescription] = (),
) -> dict[str, Any]:
    """PRE-DELIRIC stand-in. Publication formula on synthetic features."""

    features = extract_features(patient, events, cutoff)
    apache = _apache_standin(patient, features)
    logit = (
        PRE_DELIRIC_INTERCEPT
        + PRE_DELIRIC["age"] * patient.age
        + PRE_DELIRIC["apache"] * apache
        + PRE_DELIRIC["admission_medical"] * 1.0  # all synthetic stays coded medical
        + PRE_DELIRIC["coma"] * _coma(features)
        + PRE_DELIRIC["infection"] * _infection(features)
        + PRE_DELIRIC["acidosis"] * 0.0  # unmeasured
        + PRE_DELIRIC["sedatives"] * _sedative(meds, cutoff)
        + PRE_DELIRIC["urea"] * UREA_STANDIN_MMOL
        + PRE_DELIRIC["urgent"] * 1.0
        + PRE_DELIRIC["morphine"] * _morphine(meds, cutoff)
    )
    return {
        "name": "PRE-DELIRIC",
        "citation": "van den Boogaard et al., BMJ 2012;344:e420 (formula stand-in)",
        "probability": sigmoid(logit),
        "logit": logit,
        "standin_features": {
            "age": patient.age,
            "apache_standin": apache,
            "admission": "medical",
            "urea_mmol_unmeasured": UREA_STANDIN_MMOL,
            "infection_from_temp": _infection(features),
            "coma_from_rass": _coma(features),
        },
    }


def e_pre_deliric_probability(
    patient: Patient,
    events: Sequence[TimedEvent],
    *,
    cutoff: datetime,
) -> dict[str, Any]:
    """E-PRE-DELIRIC stand-in. Publication formula on synthetic features."""

    features = extract_features(patient, events, cutoff)
    map_value = _last_map(features)
    cognitive = 1.0 if (patient.age >= 80 or features.values["notes"] >= 1.0) else 0.0
    logit = (
        E_PRE_DELIRIC_INTERCEPT
        + E_PRE_DELIRIC["age"] * patient.age
        + E_PRE_DELIRIC["cognitive"] * cognitive
        + E_PRE_DELIRIC["alcohol"] * 0.0
        + E_PRE_DELIRIC["admission_medical"] * 1.0
        + E_PRE_DELIRIC["urgent"] * 1.0
        + E_PRE_DELIRIC["map"] * map_value
        + E_PRE_DELIRIC["steroids"] * 0.0
        + E_PRE_DELIRIC["respiratory_failure"] * (1.0 if patient.ventilated else 0.0)
        + E_PRE_DELIRIC["urea"] * UREA_STANDIN_MMOL
    )
    return {
        "name": "E-PRE-DELIRIC",
        "citation": "Wassenaar et al., Intensive Care Med 2015;41:1048–1056 (formula stand-in)",
        "probability": sigmoid(logit),
        "logit": logit,
        "standin_features": {
            "age": patient.age,
            "cognitive_standin": cognitive,
            "map_mmHg": map_value,
            "ventilated": patient.ventilated,
            "urea_mmol_unmeasured": UREA_STANDIN_MMOL,
        },
    }


def _last_map(features: StreamFeatures) -> float:
    matches = [e for e in features.used_events if e.name == "map" and e.value is not None]
    if not matches:
        return MAP_STANDIN
    last = max(matches, key=lambda e: e.timestamp)
    return float(last.value)  # type: ignore[arg-type]
