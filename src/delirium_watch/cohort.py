"""Seeded synthetic MIMIC-like cohort. No real MIMIC rows are produced."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime, timedelta
from pathlib import Path
from random import Random

from pydantic import BaseModel, Field

from delirium_watch import HORIZONS_HOURS, SAFETY_DISCLAIMER
from delirium_watch.config import get_settings
from delirium_watch.schemas import (
    ChartEvent,
    NoteEvent,
    Patient,
    Prescription,
    ProcedureEvent,
    TimedEvent,
    VitalSign,
)

SEED = 0
N_PATIENTS = 50
EPOCH = datetime(2024, 1, 1, 0, 0, 0)

# Filler label patterns. P001–P005 are designed separately.
# 10 cam-only, 8 ap-only, 7 restraint-only, 5 cam+ap, 4 cam+restraint,
# 3 ap+restraint, 3 all-three, 5 none = 45.
FILLER_PATTERNS: tuple[str, ...] = (
    *(("cam",) * 10),
    *(("ap",) * 8),
    *(("restraint",) * 7),
    *(("cam+ap",) * 5),
    *(("cam+restraint",) * 4),
    *(("ap+restraint",) * 3),
    *(("all",) * 3),
    *(("none",) * 5),
)


class Cohort(BaseModel):
    patients: list[Patient]
    chartevents: list[ChartEvent] = Field(default_factory=list)
    prescriptions: list[Prescription] = Field(default_factory=list)
    procedureevents: list[ProcedureEvent] = Field(default_factory=list)
    noteevents: list[NoteEvent] = Field(default_factory=list)
    vitalsigns: list[VitalSign] = Field(default_factory=list)

    def patient(self, subject_id: str) -> Patient:
        for row in self.patients:
            if row.subject_id == subject_id:
                return row
        raise KeyError(subject_id)

    def events_for(self, subject_id: str) -> list[TimedEvent]:
        out: list[TimedEvent] = []
        for ev in self.chartevents:
            if ev.subject_id == subject_id:
                out.append(
                    TimedEvent(
                        subject_id=ev.subject_id,
                        stay_id=ev.stay_id,
                        name=ev.item,
                        timestamp=ev.charttime,
                        value=ev.value,
                    )
                )
        for rx in self.prescriptions:
            if rx.subject_id == subject_id:
                out.append(
                    TimedEvent(
                        subject_id=rx.subject_id,
                        stay_id=rx.stay_id,
                        name="medication_acb",
                        timestamp=rx.starttime,
                        value=rx.acb_score,
                    )
                )
                out.append(
                    TimedEvent(
                        subject_id=rx.subject_id,
                        stay_id=rx.stay_id,
                        name=f"med:{rx.drug}",
                        timestamp=rx.starttime,
                        value=rx.drug,
                    )
                )
        for proc in self.procedureevents:
            if proc.subject_id == subject_id:
                out.append(
                    TimedEvent(
                        subject_id=proc.subject_id,
                        stay_id=proc.stay_id,
                        name=proc.item,
                        timestamp=proc.starttime,
                        value=proc.item,
                    )
                )
        for note in self.noteevents:
            if note.subject_id == subject_id:
                out.append(
                    TimedEvent(
                        subject_id=note.subject_id,
                        stay_id=note.stay_id,
                        name="nursing_note",
                        timestamp=note.charttime,
                        value=note.text,
                    )
                )
        for vital in self.vitalsigns:
            if vital.subject_id == subject_id:
                out.append(
                    TimedEvent(
                        subject_id=vital.subject_id,
                        stay_id=vital.stay_id,
                        name=vital.name,
                        timestamp=vital.charttime,
                        value=vital.value,
                    )
                )
        return out

    def cutoff_for(self, subject_id: str) -> datetime:
        patient = self.patient(subject_id)
        return patient.icu_intime + timedelta(hours=patient.prediction_cutoff_hours)


def _stay(
    index: int,
    *,
    role: str,
    path: str,
    why: str,
    expected: str,
    age: int,
    sex: str,
    los_hours: float,
    comfort_care: bool,
    ventilated: bool,
    gold_onset_hours: float | None,
    cutoff_hours: float,
) -> Patient:
    intime = EPOCH + timedelta(days=index)
    return Patient(
        subject_id=f"P{index:03d}",
        hadm_id=f"H{index:03d}",
        stay_id=f"S{index:03d}",
        age=age,
        sex=sex,  # type: ignore[arg-type]
        icu_intime=intime,
        icu_outtime=intime + timedelta(hours=los_hours),
        los_hours=los_hours,
        comfort_care=comfort_care,
        ventilated=ventilated,
        role=role,
        path_exercised=path,
        why_present=why,
        expected_behavior=expected,
        gold_onset_hours=gold_onset_hours,
        prediction_cutoff_hours=cutoff_hours,
    )


def _cam(patient: Patient, hour: float, value: str) -> ChartEvent:
    return ChartEvent(
        subject_id=patient.subject_id,
        stay_id=patient.stay_id,
        charttime=patient.icu_intime + timedelta(hours=hour),
        item="cam_icu",
        value=value,
    )


def _rass(patient: Patient, hour: float, value: str) -> ChartEvent:
    return ChartEvent(
        subject_id=patient.subject_id,
        stay_id=patient.stay_id,
        charttime=patient.icu_intime + timedelta(hours=hour),
        item="rass",
        value=value,
    )


def _med(patient: Patient, hour: float, drug: str, drug_class: str, acb: int) -> Prescription:
    return Prescription(
        subject_id=patient.subject_id,
        stay_id=patient.stay_id,
        starttime=patient.icu_intime + timedelta(hours=hour),
        drug=drug,
        drug_class=drug_class,
        acb_score=acb,
    )


def _proc(patient: Patient, hour: float, item: str) -> ProcedureEvent:
    return ProcedureEvent(
        subject_id=patient.subject_id,
        stay_id=patient.stay_id,
        starttime=patient.icu_intime + timedelta(hours=hour),
        item=item,
    )


def _note(patient: Patient, hour: float, text: str) -> NoteEvent:
    return NoteEvent(
        subject_id=patient.subject_id,
        stay_id=patient.stay_id,
        charttime=patient.icu_intime + timedelta(hours=hour),
        note_type="nursing",
        text=text,
    )


def _vital(patient: Patient, hour: float, name: str, value: float) -> VitalSign:
    return VitalSign(
        subject_id=patient.subject_id,
        stay_id=patient.stay_id,
        charttime=patient.icu_intime + timedelta(hours=hour),
        name=name,
        value=value,
    )


def _designed_p001() -> tuple[Patient, Cohort]:
    patient = _stay(
        1,
        role="prodrome_positive",
        path="clear physiological prodrome then CAM-ICU positive",
        why="Develops delirium after a rising heart-rate / RASS prodrome.",
        expected=(
            "CAM-ICU, antipsychotic, and restraint all fire. Vitals before "
            "cutoff show the prodrome. Gold onset at 36h."
        ),
        age=72,
        sex="F",
        los_hours=168,
        comfort_care=False,
        ventilated=False,
        gold_onset_hours=36.0,
        cutoff_hours=24.0,
    )
    charts = [
        _cam(patient, 8, "negative"),
        _cam(patient, 20, "negative"),
        _cam(patient, 36, "positive"),
        _rass(patient, 12, "0"),
        _rass(patient, 20, "+1"),
        _rass(patient, 32, "+2"),
    ]
    meds = [_med(patient, 38, "haloperidol", "antipsychotic", 1)]
    procs = [_proc(patient, 37, "restraint")]
    notes = [_note(patient, 18, "Restless overnight. Oriented x3. No pulling at lines.")]
    vitals = [
        _vital(patient, 8, "heart_rate", 88),
        _vital(patient, 16, "heart_rate", 102),
        _vital(patient, 22, "heart_rate", 118),
        _vital(patient, 22, "map", 68),
        _vital(patient, 22, "temp_c", 38.1),
    ]
    bundle = Cohort(
        patients=[patient],
        chartevents=charts,
        prescriptions=meds,
        procedureevents=procs,
        noteevents=notes,
        vitalsigns=vitals,
    )
    return patient, bundle


def _designed_p002() -> tuple[Patient, Cohort]:
    patient = _stay(
        2,
        role="high_acb_negative",
        path="high anticholinergic burden, no delirium event",
        why="False-positive pressure for any model that treats ACB as causal.",
        expected=(
            "All three labels negative. ACB sum is high before cutoff. "
            "No CAM-ICU, antipsychotic, or restraint events."
        ),
        age=64,
        sex="M",
        los_hours=96,
        comfort_care=False,
        ventilated=False,
        gold_onset_hours=None,
        cutoff_hours=24.0,
    )
    charts = [_cam(patient, 8, "negative"), _cam(patient, 20, "negative")]
    meds = [
        _med(patient, 4, "diphenhydramine", "antihistamine", 3),
        _med(patient, 6, "oxybutynin", "antimuscarinic", 3),
        _med(patient, 10, "amitriptyline", "antidepressant", 3),
        _med(patient, 14, "atropine", "antimuscarinic", 3),
    ]
    notes = [_note(patient, 12, "Sleeping in intervals. Oriented x3. Calm.")]
    vitals = [_vital(patient, 8, "heart_rate", 72), _vital(patient, 20, "heart_rate", 74)]
    bundle = Cohort(
        patients=[patient],
        chartevents=charts,
        prescriptions=meds,
        procedureevents=[],
        noteevents=notes,
        vitalsigns=vitals,
    )
    return patient, bundle


def _designed_p003() -> tuple[Patient, Cohort]:
    patient = _stay(
        3,
        role="notes_only",
        path="nursing-note signal only; structured labels negative",
        why="Ablating notes loses this patient. Structured labels miss the event.",
        expected=(
            "CAM-ICU, antipsychotic, and restraint are all negative. "
            "notes_signal() is true before cutoff. Gold onset at 20h from notes."
        ),
        age=81,
        sex="F",
        los_hours=120,
        comfort_care=False,
        ventilated=False,
        gold_onset_hours=20.0,
        cutoff_hours=24.0,
    )
    charts = [_cam(patient, 8, "negative"), _cam(patient, 22, "negative")]
    notes = [
        _note(
            patient,
            18,
            "Night shift: patient oriented x1 only, pulling at Foley, "
            "called for deceased spouse. Sundowning. CAM not documented this shift.",
        )
    ]
    vitals = [_vital(patient, 10, "heart_rate", 80), _vital(patient, 18, "heart_rate", 84)]
    bundle = Cohort(
        patients=[patient],
        chartevents=charts,
        prescriptions=[],
        procedureevents=[],
        noteevents=notes,
        vitalsigns=vitals,
    )
    return patient, bundle


def _designed_p004() -> tuple[Patient, Cohort]:
    patient = _stay(
        4,
        role="comfort_care",
        path="comfort care — must be excluded",
        why="CMO / comfort-care stays are not prediction targets.",
        expected="is_excluded() is true. Stay never enters label or base-rate numerators.",
        age=88,
        sex="M",
        los_hours=48,
        comfort_care=True,
        ventilated=True,
        gold_onset_hours=None,
        cutoff_hours=24.0,
    )
    charts = [_cam(patient, 6, "negative")]
    notes = [_note(patient, 2, "Comfort measures only. Family at bedside.")]
    bundle = Cohort(
        patients=[patient],
        chartevents=charts,
        prescriptions=[],
        procedureevents=[],
        noteevents=notes,
        vitalsigns=[_vital(patient, 4, "heart_rate", 60)],
    )
    return patient, bundle


def _designed_p005() -> tuple[Patient, Cohort]:
    patient = _stay(
        5,
        role="leakage_probe",
        path="post-cutoff heart_rate deliberately placed to trip leakage audit",
        why="The feature window must reject this row by name and timestamp.",
        expected=(
            "leakage_safe_window raises LeakageError naming heart_rate at "
            "icu_intime+30h. Non-zero exit if that event is ever used."
        ),
        age=59,
        sex="F",
        los_hours=80,
        comfort_care=False,
        ventilated=False,
        gold_onset_hours=40.0,
        cutoff_hours=24.0,
    )
    charts = [
        _cam(patient, 8, "negative"),
        _cam(patient, 40, "positive"),
    ]
    meds = [_med(patient, 42, "quetiapine", "antipsychotic", 1)]
    notes = [_note(patient, 12, "Calm. Oriented x3.")]
    vitals = [
        _vital(patient, 8, "heart_rate", 78),
        _vital(patient, 20, "heart_rate", 82),
        _vital(patient, 30, "heart_rate", 142),
    ]
    bundle = Cohort(
        patients=[patient],
        chartevents=charts,
        prescriptions=meds,
        procedureevents=[],
        noteevents=notes,
        vitalsigns=vitals,
    )
    return patient, bundle


def _apply_pattern(patient: Patient, pattern: str, rng: Random) -> Cohort:
    charts: list[ChartEvent] = [_cam(patient, 8, "negative")]
    meds: list[Prescription] = []
    procs: list[ProcedureEvent] = []
    notes = [_note(patient, 10, "Routine ICU care. Oriented x3.")]
    vitals = [_vital(patient, 6, "heart_rate", float(rng.randint(65, 95)))]
    onset = 4.0 + rng.random() * 40.0
    if "cam" in pattern or pattern == "all":
        charts.append(_cam(patient, onset, "positive"))
    if pattern in {"ap", "cam+ap", "ap+restraint", "all"}:
        meds.append(_med(patient, onset + 2, "olanzapine", "antipsychotic", 1))
    if pattern in {"restraint", "cam+restraint", "ap+restraint", "all"}:
        procs.append(_proc(patient, onset + 1, "restraint"))
    return Cohort(
        patients=[patient],
        chartevents=charts,
        prescriptions=meds,
        procedureevents=procs,
        noteevents=notes,
        vitalsigns=vitals,
    )


def build_cohort(seed: int = SEED) -> Cohort:
    if len(FILLER_PATTERNS) != N_PATIENTS - 5:
        raise RuntimeError("filler pattern count must be 45")
    rng = Random(seed)
    designed = [
        _designed_p001(),
        _designed_p002(),
        _designed_p003(),
        _designed_p004(),
        _designed_p005(),
    ]
    patients: list[Patient] = []
    merged = Cohort(patients=[])
    for patient, bundle in designed:
        patients.append(patient)
        _extend(merged, bundle)

    for offset, pattern in enumerate(FILLER_PATTERNS, start=6):
        has_event = pattern != "none"
        patient = _stay(
            offset,
            role=f"filler_{pattern}",
            path=f"filler stay with label pattern {pattern}",
            why="Fill pairwise label cells so agreement is measurable.",
            expected=f"Labels follow pattern {pattern}.",
            age=rng.randint(45, 90),
            sex=rng.choice(["F", "M"]),
            los_hours=float(rng.randint(48, 200)),
            comfort_care=False,
            ventilated=rng.random() < 0.25,
            gold_onset_hours=(32.0 if has_event else None),
            cutoff_hours=24.0,
        )
        patients.append(patient)
        _extend(merged, _apply_pattern(patient, pattern, rng))

    merged.patients = patients
    if len(merged.patients) != N_PATIENTS:
        raise RuntimeError("expected 50 patients")
    return merged


def _extend(target: Cohort, extra: Cohort) -> None:
    target.chartevents.extend(extra.chartevents)
    target.prescriptions.extend(extra.prescriptions)
    target.procedureevents.extend(extra.procedureevents)
    target.noteevents.extend(extra.noteevents)
    target.vitalsigns.extend(extra.vitalsigns)


def _dump(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def generate_and_write(sample_dir: Path | None = None, seed: int = SEED) -> Cohort:
    dest = sample_dir or get_settings().sample_dir
    dest.mkdir(parents=True, exist_ok=True)
    cohort = build_cohort(seed=seed)
    manifest = {
        "disclaimer": SAFETY_DISCLAIMER,
        "synthetic": True,
        "seed": seed,
        "n_patients": len(cohort.patients),
        "prediction_horizons_hours": list(HORIZONS_HOURS),
        "schema": "MIMIC-like tables; IDs are designed probes, not PhysioNet subjects.",
        "designed_ids": ["P001", "P002", "P003", "P004", "P005"],
    }
    _dump(dest / "manifest.json", manifest)
    _dump(dest / "patients.json", [p.model_dump(mode="json") for p in cohort.patients])
    _dump(dest / "chartevents.json", [e.model_dump(mode="json") for e in cohort.chartevents])
    _dump(
        dest / "prescriptions.json",
        [e.model_dump(mode="json") for e in cohort.prescriptions],
    )
    _dump(
        dest / "procedureevents.json",
        [e.model_dump(mode="json") for e in cohort.procedureevents],
    )
    _dump(dest / "noteevents.json", [e.model_dump(mode="json") for e in cohort.noteevents])
    _dump(dest / "vitalsigns.json", [e.model_dump(mode="json") for e in cohort.vitalsigns])
    from delirium_watch.parquet_io import write_cohort_parquet

    write_cohort_parquet(cohort, dest / "cohort.parquet")
    return cohort


def load_cohort(sample_dir: Path | None = None) -> Cohort:
    root = sample_dir or get_settings().sample_dir
    return Cohort(
        patients=[Patient.model_validate(r) for r in _load_json_list(root / "patients.json")],
        chartevents=[
            ChartEvent.model_validate(r) for r in _load_json_list(root / "chartevents.json")
        ],
        prescriptions=[
            Prescription.model_validate(r) for r in _load_json_list(root / "prescriptions.json")
        ],
        procedureevents=[
            ProcedureEvent.model_validate(r) for r in _load_json_list(root / "procedureevents.json")
        ],
        noteevents=[NoteEvent.model_validate(r) for r in _load_json_list(root / "noteevents.json")],
        vitalsigns=[VitalSign.model_validate(r) for r in _load_json_list(root / "vitalsigns.json")],
    )


def _load_json_list(path: Path) -> list[object]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise TypeError(f"{path} must contain a JSON list")
    return raw


def designed_samples(patients: Sequence[Patient]) -> list[Patient]:
    wanted = {"P001", "P002", "P003", "P004", "P005"}
    return [p for p in patients if p.subject_id in wanted]
