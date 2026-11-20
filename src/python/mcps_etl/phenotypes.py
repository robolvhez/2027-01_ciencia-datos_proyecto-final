"""Two-layer GWAS Phenotype Mart over OMOP CDM v5.4 (`phenotype_definition`, `phenotype_value`, `gwas_phenotypes`)."""

from __future__ import annotations

import csv
import re
import sqlite3
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .load import resolve_sqlite_path

PHENOTYPES_DIR = Path(__file__).resolve().parents[2] / "sql" / "phenotypes"
VALID_VARIABLE_TYPES: frozenset[str] = frozenset({"binary", "continuous", "categorical"})
PHENOTYPE_CODE_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")

BASE_GWAS_COLUMNS: tuple[str, ...] = (
    "person_id",
    "FID",
    "IID",
    "PATID",
    "is_genotyped",
    "AGE",
    "age_square",
    "MALE",
    "PC1",
    "PC2",
    "PC3",
    "PC4",
    "PC5",
    "PC6",
    "PC7",
)
RESERVED_BASE_COLUMNS_LOWER: frozenset[str] = frozenset(c.lower() for c in BASE_GWAS_COLUMNS)

_HEADER_FIELD_MAP: dict[str, str] = {
    "catalogue code": "code",
    "phenotype code": "code",
    "clinical phenotype": "name",
    "phenotype name": "name",
    "variable type": "variable_type",
    "units": "units",
    "description": "description",
}

_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_LINE_COMMENT_RE = re.compile(r"--[^\n]*")
_FORBIDDEN_SQL_PREFIX_RE = re.compile(
    r"^\s*(?:INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|ATTACH|DETACH|PRAGMA|VACUUM)\b",
    re.IGNORECASE,
)


def validate_phenotype_code(code: str) -> str:
    """Validate that a phenotype column code is a safe SQL identifier and does not collide with base columns."""
    cleaned = str(code or "").strip()
    if not cleaned:
        raise ValueError("Phenotype code cannot be empty")
    if not PHENOTYPE_CODE_PATTERN.match(cleaned):
        raise ValueError(
            f"Invalid phenotype code '{cleaned}': only ASCII letters, digits, and underscores are allowed"
        )
    if cleaned.lower() in RESERVED_BASE_COLUMNS_LOWER:
        raise ValueError(f"Phenotype code '{cleaned}' collides with a reserved base column in gwas_phenotypes")
    return cleaned


def validate_variable_type(variable_type: str) -> str:
    """Validate that variable_type is one of 'binary', 'continuous', or 'categorical'."""
    cleaned = str(variable_type or "").strip().lower()
    if cleaned not in VALID_VARIABLE_TYPES:
        allowed = ", ".join(sorted(VALID_VARIABLE_TYPES))
        raise ValueError(f"Invalid variable_type '{variable_type}': expected one of {allowed}")
    return cleaned


def strip_sql_comments(sql: str) -> str:
    """Strip SQL block (`/* ... */`) and line (`-- ...`) comments and trailing whitespace/semicolons."""
    no_blocks = _BLOCK_COMMENT_RE.sub("", sql)
    no_lines = _LINE_COMMENT_RE.sub("", no_blocks)
    return no_lines.strip().rstrip(";").strip()


def validate_readonly_select_sql(sql: str) -> str:
    """Ensure a phenotype SQL query is a single read-only SELECT (or WITH ... SELECT) statement."""
    cleaned = strip_sql_comments(sql)
    if not cleaned:
        raise ValueError("Phenotype SQL query is empty")
    if ";" in cleaned:
        raise ValueError("Phenotype SQL query must be a single SELECT statement (multiple statements rejected)")
    if _FORBIDDEN_SQL_PREFIX_RE.match(cleaned):
        raise ValueError("Phenotype SQL query must be a read-only SELECT/WITH statement")
    if not re.match(r"^(?:SELECT|WITH)\b", cleaned, re.IGNORECASE):
        raise ValueError("Phenotype SQL query must start with SELECT or WITH")
    return cleaned


def parse_phenotype_sql_file(sql_path: str | Path) -> dict[str, str | None]:
    """Parse clinician header metadata and validate the SELECT query from a phenotype `.sql` file."""
    path = Path(sql_path)
    raw_text = path.read_text(encoding="utf-8")
    meta: dict[str, str | None] = {
        "code": None,
        "name": None,
        "variable_type": None,
        "units": None,
        "description": None,
        "sql_source_path": str(path),
        "sql_query": None,
    }

    block_match = _BLOCK_COMMENT_RE.search(raw_text)
    if block_match:
        for line in block_match.group(0).splitlines():
            stripped = line.strip().lstrip("/*").rstrip("*/").strip()
            if ":" not in stripped:
                continue
            key_raw, val_raw = stripped.split(":", 1)
            mapped_key = _HEADER_FIELD_MAP.get(key_raw.strip().lower())
            if mapped_key and not meta[mapped_key]:
                val = val_raw.strip()
                if val and val.lower() not in {"none", "null", "n/a", "-"}:
                    meta[mapped_key] = val

    meta["sql_query"] = validate_readonly_select_sql(raw_text)
    return meta


def ensure_phenotype_tables(conn: sqlite3.Connection) -> None:
    """Create normalized phenotype registry tables (`phenotype_definition`, `phenotype_value`) if absent."""
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS phenotype_definition (
            phenotype_code  VARCHAR(64)  PRIMARY KEY,
            phenotype_name  VARCHAR(255) NOT NULL,
            variable_type   VARCHAR(20)  NOT NULL CHECK (variable_type IN ('binary', 'continuous', 'categorical')),
            units           VARCHAR(50),
            description     TEXT,
            sql_source_path VARCHAR(255),
            sql_query       TEXT         NOT NULL,
            updated_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS phenotype_value (
            phenotype_code VARCHAR(64) NOT NULL REFERENCES phenotype_definition(phenotype_code) ON DELETE CASCADE,
            person_id      INTEGER     NOT NULL REFERENCES person(person_id),
            value_numeric  REAL,
            PRIMARY KEY (phenotype_code, person_id)
        );

        CREATE INDEX IF NOT EXISTS idx_pheno_val_person ON phenotype_value (person_id, phenotype_code);
        """
    )


def rebuild_gwas_phenotypes_table(conn: sqlite3.Connection) -> dict[str, Any]:
    """Atomically materialize the wide `gwas_phenotypes` table from OMOP core tables + `phenotype_value`."""
    ensure_phenotype_tables(conn)
    codes = [
        validate_phenotype_code(row[0])
        for row in conn.execute(
            "SELECT phenotype_code FROM phenotype_definition ORDER BY phenotype_code"
        ).fetchall()
    ]

    pivot_exprs = [
        f"MAX(CASE WHEN pv.phenotype_code = '{code}' THEN pv.value_numeric END) AS \"{code}\""
        for code in codes
    ]
    select_parts = [
        "p.person_id",
        "g.genotype_fid AS FID",
        "g.genotype_iid AS IID",
        "g.patid AS PATID",
        "g.is_genotyped",
        "(CAST(SUBSTR(v.visit_start_date, 1, 4) AS INTEGER) - p.year_of_birth) AS AGE",
        "((CAST(SUBSTR(v.visit_start_date, 1, 4) AS INTEGER) - p.year_of_birth)"
        " * (CAST(SUBSTR(v.visit_start_date, 1, 4) AS INTEGER) - p.year_of_birth)) AS age_square",
        "CASE p.gender_concept_id WHEN 8507 THEN 1 WHEN 8532 THEN 0 ELSE NULL END AS MALE",
        "g.pc1 AS PC1",
        "g.pc2 AS PC2",
        "g.pc3 AS PC3",
        "g.pc4 AS PC4",
        "g.pc5 AS PC5",
        "g.pc6 AS PC6",
        "g.pc7 AS PC7",
        *pivot_exprs,
    ]
    select_clause = ",\n    ".join(select_parts)

    conn.execute("DROP TABLE IF EXISTS gwas_phenotypes")
    conn.execute(
        f"""
        CREATE TABLE gwas_phenotypes AS
        SELECT
            {select_clause}
        FROM person p
        JOIN genomic_id_map g
            ON p.person_id = g.person_id
        LEFT JOIN (
            SELECT person_id, MIN(visit_start_date) AS visit_start_date
            FROM visit_occurrence
            GROUP BY person_id
        ) v
            ON p.person_id = v.person_id
        LEFT JOIN phenotype_value pv
            ON p.person_id = pv.person_id
        GROUP BY p.person_id
        ORDER BY p.person_id
        """
    )
    conn.execute("CREATE UNIQUE INDEX idx_gwas_pheno_person ON gwas_phenotypes (person_id)")
    conn.execute("CREATE INDEX idx_gwas_pheno_geno_iid ON gwas_phenotypes (is_genotyped, IID)")

    n_rows = int(conn.execute("SELECT COUNT(*) FROM gwas_phenotypes").fetchone()[0])
    n_genotyped = int(conn.execute("SELECT COUNT(*) FROM gwas_phenotypes WHERE is_genotyped = 1").fetchone()[0])
    return {
        "table": "gwas_phenotypes",
        "n_rows": n_rows,
        "n_genotyped": n_genotyped,
        "phenotype_columns": codes,
        "n_phenotype_columns": len(codes),
    }


def _coerce_phenotype_value(raw_val: Any, variable_type: str, code: str) -> float | None:
    if raw_val is None:
        return None
    if isinstance(raw_val, str):
        cleaned = raw_val.strip()
        if cleaned == "" or cleaned.upper() in {"NA", "NAN", "NULL", "NONE"}:
            return None
        val = float(cleaned)
    else:
        val = float(raw_val)

    if variable_type == "binary" and val not in (0.0, 1.0):
        raise ValueError(
            f"Binary phenotype '{code}' returned invalid non-binary value {raw_val!r}; expected 0, 1, or NULL"
        )
    return val


def _summarize_values(
    code: str,
    name: str,
    variable_type: str,
    units: str | None,
    total_persons: int,
    values: list[float | None],
) -> dict[str, Any]:
    non_null = [v for v in values if v is not None]
    summary: dict[str, Any] = {
        "phenotype_code": code,
        "phenotype_name": name,
        "variable_type": variable_type,
        "units": units,
        "n_total_persons": total_persons,
        "n_non_null": len(non_null),
        "n_missing": total_persons - len(non_null),
    }
    if variable_type == "binary":
        summary["n_cases"] = sum(1 for v in non_null if v == 1.0)
        summary["n_controls"] = sum(1 for v in non_null if v == 0.0)
    elif variable_type == "continuous" and non_null:
        summary["min"] = round(min(non_null), 4)
        summary["mean"] = round(sum(non_null) / len(non_null), 4)
        summary["max"] = round(max(non_null), 4)
    elif variable_type == "categorical":
        summary["n_distinct_categories"] = len(set(non_null))
    return summary


def _register_phenotype_on_conn(
    conn: sqlite3.Connection,
    *,
    sql_path: str | Path | None = None,
    sql_query: str | None = None,
    code: str | None = None,
    name: str | None = None,
    variable_type: str | None = None,
    units: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    meta: dict[str, str | None] = {}
    if sql_path is not None:
        meta = parse_phenotype_sql_file(sql_path)

    resolved_code = validate_phenotype_code(code or meta.get("code") or "")
    resolved_type = validate_variable_type(variable_type or meta.get("variable_type") or "")
    resolved_name = (name or meta.get("name") or resolved_code).strip()
    resolved_units = units if units is not None else meta.get("units")
    resolved_desc = description if description is not None else meta.get("description")
    resolved_source = str(sql_path) if sql_path is not None else None

    if sql_query is not None:
        resolved_sql = validate_readonly_select_sql(sql_query)
    elif meta.get("sql_query"):
        resolved_sql = str(meta["sql_query"])
    else:
        raise ValueError("Provide either sql_path or sql_query")

    cursor = conn.execute(resolved_sql)
    col_names = [desc[0] for desc in (cursor.description or [])]
    if len(col_names) != 2:
        raise ValueError(
            f"Phenotype query for '{resolved_code}' must return exactly 2 columns "
            f"(person_id, phenotype_value); got {len(col_names)}: {col_names}"
        )
    if col_names[0].lower() != "person_id":
        raise ValueError(
            f"First column of phenotype query for '{resolved_code}' must be 'person_id'; got '{col_names[0]}'"
        )

    fetched = cursor.fetchall()
    seen_persons: set[int] = set()
    rows_to_insert: list[tuple[str, int, float | None]] = []
    coerced_vals: list[float | None] = []
    for raw_pid, raw_val in fetched:
        if raw_pid is None:
            raise ValueError(f"Phenotype query for '{resolved_code}' returned NULL person_id")
        pid = int(raw_pid)
        if pid in seen_persons:
            raise ValueError(f"Phenotype query for '{resolved_code}' returned duplicate person_id={pid}")
        seen_persons.add(pid)
        val = _coerce_phenotype_value(raw_val, resolved_type, resolved_code)
        rows_to_insert.append((resolved_code, pid, val))
        coerced_vals.append(val)

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute(
        """
        INSERT INTO phenotype_definition (
            phenotype_code, phenotype_name, variable_type, units,
            description, sql_source_path, sql_query, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(phenotype_code) DO UPDATE SET
            phenotype_name  = excluded.phenotype_name,
            variable_type   = excluded.variable_type,
            units           = excluded.units,
            description     = excluded.description,
            sql_source_path = excluded.sql_source_path,
            sql_query       = excluded.sql_query,
            updated_at      = excluded.updated_at
        """,
        (
            resolved_code,
            resolved_name,
            resolved_type,
            resolved_units,
            resolved_desc,
            resolved_source,
            resolved_sql,
            now_iso,
        ),
    )
    conn.execute("DELETE FROM phenotype_value WHERE phenotype_code = ?", (resolved_code,))
    conn.executemany(
        "INSERT INTO phenotype_value (phenotype_code, person_id, value_numeric) VALUES (?, ?, ?)",
        rows_to_insert,
    )

    total_persons = int(conn.execute("SELECT COUNT(*) FROM person").fetchone()[0])
    return _summarize_values(
        code=resolved_code,
        name=resolved_name,
        variable_type=resolved_type,
        units=resolved_units,
        total_persons=total_persons,
        values=coerced_vals,
    )


def add_phenotype_column(
    db_url: str | Path,
    *,
    sql_path: str | Path | None = None,
    sql_query: str | None = None,
    code: str | None = None,
    name: str | None = None,
    variable_type: str | None = None,
    units: str | None = None,
    description: str | None = None,
    rebuild: bool = True,
) -> dict[str, Any]:
    """Execute a phenotype SELECT query, persist it in the registry, and refresh `gwas_phenotypes`."""
    db_path = resolve_sqlite_path(db_url)
    with sqlite3.connect(db_path) as conn:
        ensure_phenotype_tables(conn)
        summary = _register_phenotype_on_conn(
            conn,
            sql_path=sql_path,
            sql_query=sql_query,
            code=code,
            name=name,
            variable_type=variable_type,
            units=units,
            description=description,
        )
        mart_info = rebuild_gwas_phenotypes_table(conn) if rebuild else None
        conn.commit()
    result: dict[str, Any] = {"status": "ok", "phenotype": summary}
    if mart_info is not None:
        result["gwas_phenotypes"] = mart_info
    return result


def add_phenotype_directory(
    db_url: str | Path,
    phenotypes_dir: str | Path = PHENOTYPES_DIR,
) -> dict[str, Any]:
    """Register all `*.sql` phenotype definitions in `phenotypes_dir` and materialize `gwas_phenotypes` once."""
    sql_files = sorted(Path(phenotypes_dir).glob("*.sql"))
    if not sql_files:
        raise ValueError(f"No *.sql phenotype files found in {phenotypes_dir}")

    db_path = resolve_sqlite_path(db_url)
    summaries: list[dict[str, Any]] = []
    with sqlite3.connect(db_path) as conn:
        ensure_phenotype_tables(conn)
        for sql_file in sql_files:
            summaries.append(_register_phenotype_on_conn(conn, sql_path=sql_file))
        mart_info = rebuild_gwas_phenotypes_table(conn)
        conn.commit()
    return {
        "status": "ok",
        "added": summaries,
        "gwas_phenotypes": mart_info,
    }


def remove_phenotype_column(
    db_url: str | Path,
    code: str,
    *,
    rebuild: bool = True,
) -> dict[str, Any]:
    """Remove a registered phenotype column from the registry and refresh `gwas_phenotypes`."""
    cleaned_code = validate_phenotype_code(code)
    db_path = resolve_sqlite_path(db_url)
    with sqlite3.connect(db_path) as conn:
        ensure_phenotype_tables(conn)
        cur = conn.execute(
            "DELETE FROM phenotype_definition WHERE phenotype_code = ?",
            (cleaned_code,),
        )
        if cur.rowcount == 0:
            raise ValueError(f"Phenotype code '{cleaned_code}' is not registered in phenotype_definition")
        mart_info = rebuild_gwas_phenotypes_table(conn) if rebuild else None
        conn.commit()
    result: dict[str, Any] = {"status": "ok", "removed_code": cleaned_code}
    if mart_info is not None:
        result["gwas_phenotypes"] = mart_info
    return result


def list_phenotypes(db_url: str | Path) -> list[dict[str, Any]]:
    """List all registered phenotypes in `phenotype_definition` with coverage counts."""
    db_path = resolve_sqlite_path(db_url)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        ensure_phenotype_tables(conn)
        total_persons = int(conn.execute("SELECT COUNT(*) FROM person").fetchone()[0])
        rows = conn.execute(
            """
            SELECT
                pd.phenotype_code,
                pd.phenotype_name,
                pd.variable_type,
                pd.units,
                pd.sql_source_path,
                pd.updated_at,
                COUNT(pv.value_numeric) AS n_non_null,
                SUM(CASE WHEN g.is_genotyped = 1 AND pv.value_numeric IS NOT NULL THEN 1 ELSE 0 END)
                    AS n_genotyped_non_null,
                SUM(CASE WHEN pd.variable_type = 'binary' AND pv.value_numeric = 1 THEN 1 ELSE 0 END) AS n_cases,
                SUM(CASE WHEN pd.variable_type = 'binary' AND pv.value_numeric = 0 THEN 1 ELSE 0 END) AS n_controls
            FROM phenotype_definition pd
            LEFT JOIN phenotype_value pv
                ON pd.phenotype_code = pv.phenotype_code
            LEFT JOIN genomic_id_map g
                ON pv.person_id = g.person_id
            GROUP BY pd.phenotype_code
            ORDER BY pd.phenotype_code
            """
        ).fetchall()

    out: list[dict[str, Any]] = []
    for r in rows:
        item = dict(r)
        item["n_missing"] = total_persons - int(item["n_non_null"] or 0)
        if item["variable_type"] != "binary":
            item.pop("n_cases", None)
            item.pop("n_controls", None)
        out.append(item)
    return out


def _format_export_cell(val: Any, *, integer_like: bool, missing_value: str) -> str:
    if val is None:
        return missing_value
    if integer_like:
        fval = float(val)
        if fval.is_integer():
            return str(int(fval))
    return str(val)


def export_gwas_phenotypes(
    db_url: str | Path,
    out_path: str | Path,
    *,
    genotyped_only: bool = True,
    codes: Sequence[str] | None = None,
    missing_value: str = "NA",
    include_patid: bool = False,
) -> dict[str, Any]:
    """Export `gwas_phenotypes` as a REGENIE/snipar/PLINK-ready TSV file (`NA` for missing values)."""
    db_path = resolve_sqlite_path(db_url)
    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        ensure_phenotype_tables(conn)
        has_mart = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'gwas_phenotypes'"
        ).fetchone()
        if not has_mart:
            rebuild_gwas_phenotypes_table(conn)

        type_by_code = {
            row["phenotype_code"]: row["variable_type"]
            for row in conn.execute("SELECT phenotype_code, variable_type FROM phenotype_definition").fetchall()
        }
        if codes:
            selected_codes = [validate_phenotype_code(c) for c in codes]
            missing_codes = [c for c in selected_codes if c not in type_by_code]
            if missing_codes:
                raise ValueError(f"Requested phenotype code(s) not registered: {', '.join(missing_codes)}")
        else:
            selected_codes = sorted(type_by_code.keys())

        export_base_cols = ["FID", "IID"]
        if include_patid:
            export_base_cols.append("PATID")
        export_base_cols.extend(["AGE", "age_square", "MALE", "PC1", "PC2", "PC3", "PC4", "PC5", "PC6", "PC7"])
        export_cols = [*export_base_cols, *selected_codes]

        int_cols = {"AGE", "age_square", "MALE"} | {
            c for c in selected_codes if type_by_code[c] in {"binary", "categorical"}
        }

        quoted_cols = ", ".join(f'"{c}"' for c in export_cols)
        where_clause = "WHERE is_genotyped = 1 AND IID IS NOT NULL" if genotyped_only else ""
        query = f"SELECT {quoted_cols} FROM gwas_phenotypes {where_clause} ORDER BY person_id"

        n_rows = 0
        with target.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            writer.writerow(export_cols)
            for row in conn.execute(query):
                writer.writerow(
                    [
                        _format_export_cell(
                            row[c],
                            integer_like=(c in int_cols),
                            missing_value=missing_value,
                        )
                        for c in export_cols
                    ]
                )
                n_rows += 1

    return {
        "status": "ok",
        "out_path": str(target),
        "n_rows": n_rows,
        "genotyped_only": genotyped_only,
        "columns": export_cols,
        "phenotype_columns": selected_codes,
    }
