"""Database initialization and MCPS -> OMOP CDM v5.4 loader (stdlib sqlite3 + csv)."""

from __future__ import annotations

import csv
import sqlite3
from collections.abc import Iterable, Mapping
from itertools import islice
from pathlib import Path
from typing import Any

from .id_linkage import build_genomic_id_map, read_id_bridge, read_plink_fam, validate_regid_linkage
from .mapper import DEFAULT_MAP_PATH, load_concept_map
from .transform import (
    compute_drug_exposure,
    transform_conditions,
    transform_locations,
    transform_measurements,
    transform_observations,
    transform_persons,
    transform_visits_and_periods,
)

DDL_DIR = Path(__file__).resolve().parents[2] / "sql" / "ddl"


def resolve_sqlite_path(db_url_or_path: str | Path) -> str:
    """Resolve a SQLite file path or `sqlite:///...` URL to a path accepted by `sqlite3.connect`."""
    raw = str(db_url_or_path)
    if raw.startswith("sqlite:////"):
        return "/" + raw.removeprefix("sqlite:////")
    if raw.startswith("sqlite:///"):
        return raw.removeprefix("sqlite:///")
    return raw


def execute_sql_script(conn: sqlite3.Connection, sql_path: str | Path) -> None:
    """Execute a multi-statement SQL script against a SQLite connection."""
    conn.executescript(Path(sql_path).read_text(encoding="utf-8"))
    conn.commit()


def _insert_records(conn: sqlite3.Connection, table_name: str, records: list[dict[str, Any]]) -> int:
    if not records:
        return 0
    cols = list(records[0].keys())
    placeholders = ", ".join(["?"] * len(cols))
    col_list = ", ".join(cols)
    sql = f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders})"
    values = [tuple(r[c] for c in cols) for r in records]
    conn.executemany(sql, values)
    return len(records)


def init_omop_db(conn: sqlite3.Connection, map_path: str | Path = DEFAULT_MAP_PATH) -> None:
    """Initialize OMOP CDM v5.4 schema, seed standard concepts, and load source_to_concept_map."""
    execute_sql_script(conn, DDL_DIR / "01_omop_cdm_v54_ddl.sql")
    execute_sql_script(conn, DDL_DIR / "02_seed_concepts.sql")

    cmap = load_concept_map(map_path)
    stcm_rows = [
        {
            "source_code": e.source_code,
            "source_concept_id": 0,
            "source_vocabulary_id": e.source_vocabulary_id,
            "source_code_description": e.source_code_description,
            "target_concept_id": e.target_concept_id,
            "target_vocabulary_id": e.target_vocabulary_id,
            "valid_start_date": e.valid_start_date,
            "valid_end_date": e.valid_end_date,
            "invalid_reason": e.invalid_reason,
        }
        for e in cmap.values()
    ]
    conn.execute("DELETE FROM source_to_concept_map")
    _insert_records(conn, "source_to_concept_map", stcm_rows)
    conn.commit()


def read_mcps_table(path: str | Path, nrows: int | None = None) -> list[dict[str, Any]]:
    """Read an MCPS CSV or tab-delimited phenotype table into a list of row dicts."""
    file_path = Path(path)
    sep = "\t" if file_path.suffix.lower() in {".txt", ".tsv"} else ","
    with file_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=sep)
        rows = list(islice(reader, nrows)) if nrows is not None else list(reader)
    return rows


def construct_db(
    input_data: str | Path | Iterable[Mapping[str, Any]],
    db_url: str | Path,
    id_bridge_path: str | Path | None = None,
    fam_path: str | Path | None = None,
    map_path: str | Path = DEFAULT_MAP_PATH,
    nrows: int | None = None,
) -> dict[str, int]:
    """Run the MCPS -> OMOP CDM v5.4 ETL pipeline and return loaded table row counts."""
    db_path = resolve_sqlite_path(db_url)
    raw_rows = (
        read_mcps_table(input_data, nrows=nrows)
        if isinstance(input_data, (str, Path))
        else [dict(r) for r in input_data]
    )
    for idx, row in enumerate(raw_rows, start=1):
        row["person_id"] = idx

    id_bridge = read_id_bridge(id_bridge_path) if id_bridge_path else None
    fam_samples = read_plink_fam(fam_path) if fam_path else None
    concept_map = load_concept_map(map_path)

    genomic_map_rows = build_genomic_id_map(raw_rows, id_bridge=id_bridge, fam_samples=fam_samples)
    validate_regid_linkage(genomic_map_rows)

    locations_rows = transform_locations()
    persons_rows = transform_persons(raw_rows, genomic_map_rows)
    visits_rows, periods_rows = transform_visits_and_periods(raw_rows)
    measurements_rows = transform_measurements(raw_rows, concept_map=concept_map)
    conditions_rows = transform_conditions(raw_rows, concept_map=concept_map)
    observations_rows = transform_observations(raw_rows, concept_map=concept_map)
    drug_exposures_rows = compute_drug_exposure(raw_rows, concept_map=concept_map)

    tables_to_load: list[tuple[str, list[dict[str, Any]]]] = [
        ("location", locations_rows),
        ("person", persons_rows),
        ("genomic_id_map", genomic_map_rows),
        ("visit_occurrence", visits_rows),
        ("observation_period", periods_rows),
        ("measurement", measurements_rows),
        ("condition_occurrence", conditions_rows),
        ("observation", observations_rows),
        ("drug_exposure", drug_exposures_rows),
    ]

    with sqlite3.connect(db_path) as conn:
        init_omop_db(conn, map_path=map_path)
        for table_name, _ in reversed(tables_to_load):
            conn.execute(f"DELETE FROM {table_name}")
        counts: dict[str, int] = {}
        for table_name, records in tables_to_load:
            counts[table_name] = _insert_records(conn, table_name, records)
        conn.commit()

    return counts
