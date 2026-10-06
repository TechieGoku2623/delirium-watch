from __future__ import annotations

from delirium_watch.cohort import load_cohort
from delirium_watch.exclusions import excluded_patients, included_patients, is_excluded
from delirium_watch.labels import (
    all_labels,
    antipsychotic_label,
    cam_icu_label,
    cohen_kappa,
    label_by_name,
    percent_agreement,
    restraint_label,
)


def test_p001_all_three_labels_fire() -> None:
    cohort = load_cohort()
    patient = cohort.patient("P001")
    calls = all_labels(
        patient,
        assessments=cohort.chartevents,
        meds=cohort.prescriptions,
        procedures=cohort.procedureevents,
    )
    assert calls["cam_icu"].positive
    assert calls["antipsychotic"].positive
    assert calls["restraint"].positive


def test_p002_all_labels_negative() -> None:
    cohort = load_cohort()
    patient = cohort.patient("P002")
    assert not cam_icu_label(patient, cohort.chartevents).positive
    assert not antipsychotic_label(patient, cohort.prescriptions).positive
    assert not restraint_label(patient, cohort.procedureevents).positive


def test_p003_structured_labels_negative() -> None:
    cohort = load_cohort()
    patient = cohort.patient("P003")
    calls = all_labels(
        patient,
        assessments=cohort.chartevents,
        meds=cohort.prescriptions,
        procedures=cohort.procedureevents,
    )
    assert not any(call.positive for call in calls.values())


def test_p004_is_excluded() -> None:
    cohort = load_cohort()
    patient = cohort.patient("P004")
    assert is_excluded(patient)
    assert patient in excluded_patients(cohort.patients)
    assert patient not in included_patients(cohort.patients)


def test_label_by_name_matches_direct() -> None:
    cohort = load_cohort()
    patient = cohort.patient("P001")
    kwargs = {
        "assessments": cohort.chartevents,
        "meds": cohort.prescriptions,
        "procedures": cohort.procedureevents,
    }
    assert label_by_name("cam_icu", patient, **kwargs).positive
    assert label_by_name("antipsychotic", patient, **kwargs).positive
    assert label_by_name("restraint", patient, **kwargs).positive


def test_cohen_kappa_perfect_and_empty() -> None:
    assert cohen_kappa([(True, True), (False, False)]) == 1.0
    assert cohen_kappa([]) == 0.0
    assert percent_agreement([]) == 0.0
    assert percent_agreement([(True, True), (True, False)]) == 0.5


def test_cohen_kappa_chance() -> None:
    pairs = [(True, True), (True, False), (False, True), (False, False)]
    assert abs(cohen_kappa(pairs) - 0.0) < 1e-9
