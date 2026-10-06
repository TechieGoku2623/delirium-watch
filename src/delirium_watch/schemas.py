"""Data contracts for the synthetic MIMIC-like cohort and feature windows."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from delirium_watch import HORIZONS_HOURS

LabelName = Literal["cam_icu", "antipsychotic", "restraint"]
Sex = Literal["F", "M"]
HorizonHours = Literal[6, 12, 24]


class Patient(BaseModel):
    """One synthetic ICU stay. IDs are designed probes, not MIMIC subjects."""

    subject_id: str
    hadm_id: str
    stay_id: str
    age: int = Field(ge=18, le=100)
    sex: Sex
    icu_intime: datetime
    icu_outtime: datetime
    los_hours: float = Field(gt=0)
    comfort_care: bool
    ventilated: bool = False
    role: str
    path_exercised: str
    why_present: str
    expected_behavior: str
    gold_onset_hours: float | None = None
    prediction_cutoff_hours: float = 24.0


class ChartEvent(BaseModel):
    subject_id: str
    stay_id: str
    charttime: datetime
    item: str
    value: str


class Prescription(BaseModel):
    subject_id: str
    stay_id: str
    starttime: datetime
    drug: str
    drug_class: str
    acb_score: int = Field(ge=0, le=3)
    route: str = "IV"


class ProcedureEvent(BaseModel):
    subject_id: str
    stay_id: str
    starttime: datetime
    item: str


class NoteEvent(BaseModel):
    subject_id: str
    stay_id: str
    charttime: datetime
    note_type: str
    text: str


class VitalSign(BaseModel):
    subject_id: str
    stay_id: str
    charttime: datetime
    name: str
    value: float


class TimedEvent(BaseModel):
    """Flattened event used by the leakage-safe feature window."""

    subject_id: str
    stay_id: str
    name: str
    timestamp: datetime
    value: str | float | None = None


class LeakageFinding(BaseModel):
    subject_id: str
    stay_id: str
    feature: str
    timestamp: datetime
    cutoff: datetime


class WindowResult(BaseModel):
    used: list[TimedEvent]
    rejected: list[LeakageFinding]
    cutoff: datetime
    lookback_hours: float | None = None


class PredictionConfig(BaseModel):
    horizon_hours: HorizonHours = 12
    lookback_hours: float = 24.0
    reject_leakage: bool = True

    def model_post_init(self, __context: object) -> None:
        if self.horizon_hours not in HORIZONS_HOURS:
            raise ValueError(f"horizon_hours must be one of {HORIZONS_HOURS}")


class LabelCall(BaseModel):
    subject_id: str
    stay_id: str
    label: LabelName
    positive: bool
    first_event_hours: float | None = None


class SamplePatient(BaseModel):
    """One of the five designed demo patients."""

    subject_id: str
    role: str
    path_exercised: str
    why_present: str
    expected_behavior: str
