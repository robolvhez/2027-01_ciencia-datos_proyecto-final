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

from .build_bridge import DEFAULT_BRIDGE_OUT, DEFAULT_IID_PATID_PATTERN, generate_bridge_file
from .load import construct_db, execute_sql_script, read_mcps_table, resolve_sqlite_path
from .mapper import (
    DEFAULT_MAP_PATH,
    MIN_MEDICATION_MENTION_COUNT,
    load_concept_map,
    profile_medication_terms,
    suggest_mappings,
    verify_concepts_against_athena,
)
from .phenotypes import (
    PHENOTYPES_DIR,
    add_phenotype_column,
    add_phenotype_directory,
    export_gwas_phenotypes,
    list_phenotypes,
    remove_phenotype_column,
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

    bridge_p = sub.add_parser(
        "build-bridge",
        help="Build a verified 1:1 PATID <-> genotype IID/FID bridge file for --id-bridge",
    )
    bridge_p.add_argument("--input", "-i", required=True, help="Path to MCPS baseline CSV/TSV containing PATID")
    bridge_p.add_argument("--fam", "-f", required=True, help="Path to PLINK .fam file listing genotyped FID/IIDs")
    bridge_p.add_argument(
        "--out",
        "-o",
        default=DEFAULT_BRIDGE_OUT,
        help=f"Output bridge path (.tsv, .txt, or .csv; default: {DEFAULT_BRIDGE_OUT})",
    )
    bridge_p.add_argument(
        "--pattern",
        default=DEFAULT_IID_PATID_PATTERN.pattern,
        help="Regex whose capture group 1 extracts PATID from .fam IID",
    )

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

    pheno_p = sub.add_parser(
        "phenotype",
        help="Manage the wide GWAS phenotype mart (`gwas_phenotypes`): add/remove/list/export SQL-defined columns",
    )
    pheno_sub = pheno_p.add_subparsers(dest="phenotype_command", required=True)

    p_add = pheno_sub.add_parser("add", help="Add or update one SQL-defined phenotype column (or a directory of *.sql)")
    p_add.add_argument(
        "--db-url",
        "-d",
        default=DEFAULT_DB_URL,
        help=f"SQLite DB path or URL (default: {DEFAULT_DB_URL})",
    )
    add_src = p_add.add_mutually_exclusive_group(required=True)
    add_src.add_argument("--sql-file", "-s", help="Path to a single-code phenotype .sql file")
    add_src.add_argument(
        "--dir",
        nargs="?",
        const=str(PHENOTYPES_DIR),
        help=f"Directory of *.sql phenotype files to batch-add (default when flag passed: {PHENOTYPES_DIR})",
    )
    add_src.add_argument("--sql", help="Inline read-only SELECT query returning (person_id, phenotype_value)")
    p_add.add_argument("--code", help="Phenotype column code (optional if declared in SQL file header)")
    p_add.add_argument(
        "--type",
        dest="variable_type",
        choices=["binary", "continuous", "categorical"],
        help="Variable type (optional if declared in SQL file header)",
    )
    p_add.add_argument("--name", help="Human-readable phenotype name (optional override)")
    p_add.add_argument("--units", help="Units for continuous traits (optional override)")
    p_add.add_argument("--description", help="Short clinical description (optional override)")

    p_rm = pheno_sub.add_parser("remove", help="Remove a phenotype column from the registry and gwas_phenotypes")
    p_rm.add_argument(
        "--db-url",
        "-d",
        default=DEFAULT_DB_URL,
        help=f"SQLite DB path or URL (default: {DEFAULT_DB_URL})",
    )
    p_rm.add_argument("--code", required=True, help="Phenotype column code to remove (e.g. 11_11_01)")

    p_ls = pheno_sub.add_parser("list", help="List all registered phenotype columns and coverage counts")
    p_ls.add_argument(
        "--db-url",
        "-d",
        default=DEFAULT_DB_URL,
        help=f"SQLite DB path or URL (default: {DEFAULT_DB_URL})",
    )

    p_exp = pheno_sub.add_parser("export", help="Export gwas_phenotypes to a REGENIE/snipar-ready TSV file")
    p_exp.add_argument(
        "--db-url",
        "-d",
        default=DEFAULT_DB_URL,
        help=f"SQLite DB path or URL (default: {DEFAULT_DB_URL})",
    )
    p_exp.add_argument("--out", "-o", required=True, help="Output TSV path (outside Git, e.g. /tmp/gwas_phenos.txt)")
    p_exp.add_argument(
        "--all-participants",
        action="store_true",
        help="Include ungenotyped participants (default exports genotyped participants only)",
    )
    p_exp.add_argument(
        "--include-patid",
        action="store_true",
        help="Include PATID column alongside FID/IID in exported TSV",
    )
    p_exp.add_argument("--codes", nargs="+", help="Optional subset of phenotype codes to export")
    p_exp.add_argument("--missing", default="NA", help="Missing value string (default: NA)")

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
        counts = construct_db(
            input_data=args.input,
            db_url=args.db_url,
            id_bridge_path=args.id_bridge,
            fam_path=args.fam,
            map_path=args.map_path,
            nrows=args.nrows,
        )
        print(json.dumps({"status": "ok", "db_url": args.db_url, "loaded_rows": counts}, indent=2))
    elif args.command == "build-bridge":
        report = generate_bridge_file(
            baseline_path=args.input,
            fam_path=args.fam,
            out_path=args.out,
            pattern=args.pattern,
        )
        print(json.dumps(report, indent=2))
    elif args.command == "cohorts":
        summary = run_cohorts_summary(args.db_url, cohorts_dir=args.cohorts_dir)
        print(json.dumps({"db_url": args.db_url, "cohort_counts": summary}, indent=2))
    elif args.command == "phenotype":
        if args.phenotype_command == "add":
            if args.dir is not None:
                report = add_phenotype_directory(args.db_url, phenotypes_dir=args.dir)
            else:
                report = add_phenotype_column(
                    args.db_url,
                    sql_path=args.sql_file,
                    sql_query=args.sql,
                    code=args.code,
                    name=args.name,
                    variable_type=args.variable_type,
                    units=args.units,
                    description=args.description,
                )
            print(json.dumps(report, indent=2))
        elif args.phenotype_command == "remove":
            report = remove_phenotype_column(args.db_url, code=args.code)
            print(json.dumps(report, indent=2))
        elif args.phenotype_command == "list":
            items = list_phenotypes(args.db_url)
            print(json.dumps({"db_url": args.db_url, "phenotypes": items}, indent=2))
        elif args.phenotype_command == "export":
            report = export_gwas_phenotypes(
                args.db_url,
                out_path=args.out,
                genotyped_only=not args.all_participants,
                codes=args.codes,
                missing_value=args.missing,
                include_patid=args.include_patid,
            )
            print(json.dumps(report, indent=2))
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
