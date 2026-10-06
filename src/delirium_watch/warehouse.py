"""DuckDB load of the synthetic MIMIC-like tables for Phase 0 queries."""

from __future__ import annotations

from pathlib import Path

import duckdb

from delirium_watch.config import get_settings


def connect_sample(sample_dir: Path | None = None) -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB with one view per committed JSON table."""

    root = sample_dir or get_settings().sample_dir
    con = duckdb.connect(":memory:")
    tables = (
        "patients",
        "chartevents",
        "prescriptions",
        "procedureevents",
        "noteevents",
        "vitalsigns",
    )
    for table in tables:
        path = (root / f"{table}.json").as_posix().replace("'", "''")
        con.execute(f"CREATE VIEW {table} AS SELECT * FROM read_json_auto('{path}')")
    return con
