"""Write and read the analysis cohort as Parquet. DuckDB only; no pyarrow."""

from __future__ import annotations

from pathlib import Path

import duckdb

from delirium_watch.cohort import Cohort
from delirium_watch.exclusions import is_excluded
from delirium_watch.labels import all_labels


def write_cohort_parquet(cohort: Cohort, path: Path) -> Path:
    """One row per stay: demographics, exclusion, three competing labels."""

    path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    for patient in cohort.patients:
        calls = all_labels(
            patient,
            assessments=cohort.chartevents,
            meds=cohort.prescriptions,
            procedures=cohort.procedureevents,
        )
        rows.append(
            {
                "subject_id": patient.subject_id,
                "stay_id": patient.stay_id,
                "age": patient.age,
                "sex": patient.sex,
                "icu_intime": patient.icu_intime.isoformat(),
                "los_hours": patient.los_hours,
                "comfort_care": patient.comfort_care,
                "ventilated": patient.ventilated,
                "excluded": is_excluded(patient),
                "role": patient.role,
                "prediction_cutoff_hours": patient.prediction_cutoff_hours,
                "gold_onset_hours": patient.gold_onset_hours,
                "cam_icu": calls["cam_icu"].positive,
                "cam_icu_hours": calls["cam_icu"].first_event_hours,
                "antipsychotic": calls["antipsychotic"].positive,
                "antipsychotic_hours": calls["antipsychotic"].first_event_hours,
                "restraint": calls["restraint"].positive,
                "restraint_hours": calls["restraint"].first_event_hours,
            }
        )
    con = duckdb.connect(":memory:")
    con.execute(
        """
        CREATE TABLE cohort (
          subject_id VARCHAR,
          stay_id VARCHAR,
          age INTEGER,
          sex VARCHAR,
          icu_intime VARCHAR,
          los_hours DOUBLE,
          comfort_care BOOLEAN,
          ventilated BOOLEAN,
          excluded BOOLEAN,
          role VARCHAR,
          prediction_cutoff_hours DOUBLE,
          gold_onset_hours DOUBLE,
          cam_icu BOOLEAN,
          cam_icu_hours DOUBLE,
          antipsychotic BOOLEAN,
          antipsychotic_hours DOUBLE,
          restraint BOOLEAN,
          restraint_hours DOUBLE
        )
        """
    )
    for row in rows:
        con.execute(
            """
            INSERT INTO cohort VALUES (
              ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            list(row.values()),
        )
    dest = path.as_posix()
    con.execute(f"COPY cohort TO '{dest}' (FORMAT PARQUET)")
    return path


def read_cohort_parquet(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        raise FileNotFoundError(f"cohort parquet not found: {path}")
    con = duckdb.connect(":memory:")
    dest = path.as_posix()
    result = con.execute(f"SELECT * FROM read_parquet('{dest}')")
    columns = [d[0] for d in result.description]
    return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]


def label_table_from_parquet(path: Path) -> list[dict[str, object]]:
    """Rows used by `labels compare`. Excluded stays stay in the file, flagged."""

    return read_cohort_parquet(path)
