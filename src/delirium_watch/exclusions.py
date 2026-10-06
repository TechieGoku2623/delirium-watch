"""Cohort exclusions. Comfort-care stays never enter the analysis set."""

from __future__ import annotations

from collections.abc import Sequence

from delirium_watch.schemas import Patient


def is_excluded(patient: Patient) -> bool:
    return patient.comfort_care


def included_patients(patients: Sequence[Patient]) -> list[Patient]:
    return [p for p in patients if not is_excluded(p)]


def excluded_patients(patients: Sequence[Patient]) -> list[Patient]:
    return [p for p in patients if is_excluded(p)]
