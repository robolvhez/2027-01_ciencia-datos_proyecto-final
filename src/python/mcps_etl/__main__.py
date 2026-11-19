#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
"""CLI entry point for the MCPS -> OMOP CDM v5.4 headless ETL pipeline."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from pathlib import Path

try:
    import argcomplete
except ImportError:  # pragma: no cover
    argcomplete = None  # type: ignore[assignment]

from .load import execute_sql_script, read_mcps_table, resolve_sqlite_path, run_stage1_etl
from .mapper import (
    DEFAULT_MAP_PATH,
    MIN_MEDICATION_MENTION_COUNT,
    load_concept_map,
    profile_medication_terms,
    suggest_mappings,
    verify_concepts_against_athena,
)

COHORTS_DIR = Path(__file__).resolve().parents[2] / "sql" / "cohorts"
DEFAULT_DB_URL = "sqlite:////tmp/mcps_omop.db"


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser for `mcps-etl` with argcomplete support."""
    parser = argparse.ArgumentParser(
        prog="mcps-omop-etl",
        description="Headless ETL pipeline for Mexico City Prospective Study (MCPS) into OMOP CDM v5.4",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run MCPS -> OMOP CDM v5.4 database build")
    run_p.add_argument("--input", "-i", required=True, help="Path to MCPS baseline CSV or genotyped TSV/TXT")
    run_p.add_argument(
        "--db-url",
        "-d",
        default=DEFAULT_DB_URL,
        help=f"SQLite DB path or URL (default: {DEFAULT_DB_URL})",
    )
    run_p.add_argument("--id-bridge", help="Optional PATID <-> Regeneron RegID (IID/FID) crosswalk file")
    run_p.add_argument("--fam", "-f", help="Optional PLINK .fam file listing genotyped sample FID/IIDs")
    run_p.add_argument("--map-path", default=str(DEFAULT_MAP_PATH), help="Path to source_to_concept_map.csv")
    run_p.add_argument("--nrows", "-n", type=int, help="Optional row limit for quick validation runs")

    coh_p = sub.add_parser(
        "cohorts",
        help="Execute all SQL cohort scripts in --cohorts-dir (default: src/sql/cohorts/*.sql) and print summary counts",
    )
    coh_p.add_argument(
        "--db-url",
        "-d",
        default=DEFAULT_DB_URL,
        help=f"SQLite DB path or URL (default: {DEFAULT_DB_URL})",
    )
    coh_p.add_argument(
        "--cohorts-dir",
        "-c",
        default=str(COHORTS_DIR),
        help=f"Directory containing cohort *.sql scripts (default: {COHORTS_DIR})",
    )

    prof_p = sub.add_parser(
        "profile-medications",
        help="Traceably count MEDICATION1..3 strings, enforce --min-count threshold, and audit mapping coverage",
    )
    prof_p.add_argument("--input", "-i", required=True, help="Path to MCPS baseline CSV")
    prof_p.add_argument(
        "--min-count",
        type=int,
        default=MIN_MEDICATION_MENTION_COUNT,
        help=f"Minimum mention count threshold (default: {MIN_MEDICATION_MENTION_COUNT})",
    )
    prof_p.add_argument("--map-path", default=str(DEFAULT_MAP_PATH), help="Path to source_to_concept_map.csv")
    prof_p.add_argument("--nrows", "-n", type=int, help="Optional row limit")

    ver_p = sub.add_parser("verify-concepts", help="Verify mapped SNOMED/LOINC/RxNorm/ATC codes against Athena CONCEPT.csv")
    ver_p.add_argument("--athena-concept", required=True, help="Path to Athena CONCEPT.csv")
    ver_p.add_argument("--map-path", default=str(DEFAULT_MAP_PATH), help="Path to source_to_concept_map.csv")

    sug_p = sub.add_parser("suggest-mappings", help="Headless Usagi replacement matching terms against Athena")
    sug_p.add_argument("--terms", required=True, help="CSV with source_code and source_description columns")
    sug_p.add_argument("--athena-concept", required=True, help="Path to Athena CONCEPT.csv")
    sug_p.add_argument(
        "--domain",
        choices=["Condition", "Measurement", "Observation", "Drug"],
        help="Optional OMOP domain filter",
    )
    sug_p.add_argument("--top-k", type=int, default=3, help="Candidates per source term")
    sug_p.add_argument("--out", required=True, help="Output CSV path for suggested mappings")

    return parser


def run_cohorts_summary(
    db_url: str,
    cohorts_dir: str | Path = COHORTS_DIR,
) -> list[dict[str, object]]:
    """Execute all `*.sql` cohort definitions in `cohorts_dir` and return case counts per phenotype."""
    db_path = resolve_sqlite_path(db_url)
    sql_files = sorted(Path(cohorts_dir).glob("*.sql"))
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cohort_definition (
                cohort_definition_id          INTEGER      PRIMARY KEY,
                cohort_definition_name        VARCHAR(255) NOT NULL,
                cohort_definition_description TEXT,
                definition_type_concept_id    INTEGER      NOT NULL DEFAULT 32880,
                cohort_definition_syntax      TEXT,
                subject_concept_id            INTEGER      NOT NULL DEFAULT 1147314,
                cohort_initiation_date        DATE
            )
            """
        )
        for sql_file in sql_files:
            execute_sql_script(conn, sql_file)
        rows = conn.execute(
            """
            SELECT
                c.cohort_definition_id,
                COALESCE(cd.cohort_definition_name, 'Cohort ' || c.cohort_definition_id) AS phenotype,
                g.is_genotyped,
                COUNT(*) AS n_cases
            FROM cohort c
            JOIN genomic_id_map g ON c.subject_id = g.person_id
            LEFT JOIN cohort_definition cd ON c.cohort_definition_id = cd.cohort_definition_id
            GROUP BY c.cohort_definition_id, cd.cohort_definition_name, g.is_genotyped
            ORDER BY c.cohort_definition_id, g.is_genotyped DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def main(argv: list[str] | None = None) -> None:
    """Execute the `mcps-etl` CLI command."""
    parser = build_parser()
    if argcomplete is not None:
        argcomplete.autocomplete(parser)
    args = parser.parse_args(argv)

    if args.command == "run":
        counts = run_stage1_etl(
            input_data=args.input,
            db_url=args.db_url,
            id_bridge_path=args.id_bridge,
            fam_path=args.fam,
            map_path=args.map_path,
            nrows=args.nrows,
        )
        print(json.dumps({"status": "ok", "db_url": args.db_url, "loaded_rows": counts}, indent=2))
    elif args.command == "cohorts":
        summary = run_cohorts_summary(args.db_url, cohorts_dir=args.cohorts_dir)
        print(json.dumps({"db_url": args.db_url, "cohort_counts": summary}, indent=2))
    elif args.command == "profile-medications":
        raw_rows = read_mcps_table(args.input, nrows=args.nrows)
        cmap = load_concept_map(args.map_path)
        profile = profile_medication_terms(raw_rows, concept_map=cmap, min_count=args.min_count)
        print(json.dumps(profile, indent=2))
    elif args.command == "verify-concepts":
        report = verify_concepts_against_athena(args.athena_concept, map_path=args.map_path)
        print(json.dumps(report, indent=2))
    elif args.command == "suggest-mappings":
        terms_rows = read_mcps_table(args.terms)
        athena_rows = read_mcps_table(args.athena_concept)
        suggestions = suggest_mappings(terms_rows, athena_rows, domain_id=args.domain, top_k=args.top_k)
        out_path = Path(args.out)
        if suggestions:
            with out_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(suggestions[0].keys()))
                writer.writeheader()
                writer.writerows(suggestions)
        print(f"Saved {len(suggestions)} suggested mappings to {out_path}")


if __name__ == "__main__":
    main()
