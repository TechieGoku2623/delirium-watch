from __future__ import annotations

from delirium_watch.cohort import (
    N_PATIENTS,
    SEED,
    build_cohort,
    designed_samples,
    generate_and_write,
    load_cohort,
)
from delirium_watch.warehouse import connect_sample


def test_generator_is_deterministic() -> None:
    a = build_cohort(seed=SEED)
    b = build_cohort(seed=SEED)
    assert [p.subject_id for p in a.patients] == [p.subject_id for p in b.patients]
    assert len(a.patients) == N_PATIENTS
    assert a.patients[0].subject_id == "P001"
    assert a.patients[-1].subject_id == "P050"


def test_designed_roles() -> None:
    cohort = load_cohort()
    assert cohort.patient("P001").role == "prodrome_positive"
    assert cohort.patient("P002").role == "high_acb_negative"
    assert cohort.patient("P003").role == "notes_only"
    assert cohort.patient("P004").role == "comfort_care"
    assert cohort.patient("P005").role == "leakage_probe"
    assert len(designed_samples(cohort.patients)) == 5


def test_patient_lookup_missing() -> None:
    cohort = load_cohort()
    try:
        cohort.patient("P999")
    except KeyError:
        return
    raise AssertionError("expected KeyError")


def test_duckdb_views_match_json() -> None:
    cohort = load_cohort()
    con = connect_sample()
    n = int(con.execute("SELECT COUNT(*) FROM patients").fetchone()[0])
    assert n == len(cohort.patients)
    comfort = int(con.execute("SELECT COUNT(*) FROM patients WHERE comfort_care").fetchone()[0])
    assert comfort == 1


def test_generate_and_write_roundtrip(tmp_path: object) -> None:
    from pathlib import Path

    dest = Path(str(tmp_path))
    written = generate_and_write(sample_dir=dest, seed=SEED)
    loaded = load_cohort(sample_dir=dest)
    assert len(loaded.patients) == len(written.patients)
    assert loaded.patient("P005").role == "leakage_probe"
