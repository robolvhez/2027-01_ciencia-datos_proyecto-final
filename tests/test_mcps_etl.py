"""Automated tests for Stage 1 MCPS -> OMOP CDM v5.4 ETL, Genomic ID linkage, and SQL cohorts."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from src.python.mcps_etl.id_linkage import build_genomic_id_map, parse_regeneron_iid
from src.python.mcps_etl.load import execute_sql_script, run_stage1_etl
from src.python.mcps_etl.mapper import suggest_mappings, verify_concepts_against_athena

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_parse_regeneron_iid_and_genomic_id_map() -> None:
    rgc_id, mexb_id = parse_regeneron_iid("MCPS_MCPSRGN000002_MEXB000301")
    assert rgc_id == "MCPSRGN000002"
    assert mexb_id == "MEXB000301"

    rows = [
        {
            "PATID": "MCPSDS000007",
            "IID": "MCPS_MCPSRGN000002_MEXB000301",
            "FID": "MCPS_MCPSRGN000002_MEXB000301",
            "PC1": 0.12,
        },
        {
            "PATID": "MCPSDS000073",
            "IID": "MCPS_MCPSRGN000003_MEXB000302",
            "FID": "MCPS_MCPSRGN000003_MEXB000302",
            "PC1": -0.34,
        },
        {
            "PATID": "MCPSDS000099",
            "IID": None,
            "FID": None,
            "PC1": None,
        },
    ]

    gmap = build_genomic_id_map(rows)
    assert [r["is_genotyped"] for r in gmap] == [1, 1, 0]
    assert gmap[0]["rgc_id"] == "MCPSRGN000002"
    assert gmap[0]["mexb_id"] == "MEXB000301"


def test_stage1_etl_and_sql_cohorts(tmp_path: Path) -> None:
    db_path = tmp_path / "test_mcps_omop.db"
    db_url = f"sqlite:///{db_path}"

    sample_rows = [
        {
            "PATID": "MCPSDS000007",
            "IID": "MCPS_MCPSRGN000001_MEXB000300",
            "FID": "MCPS_MCPSRGN000001_MEXB000300",
            "YEAR_RECRUITED": 2000,
            "MONTH_RECRUITED": 12,
            "MALE": 0,
            "AGE": 67,
            "COYOACAN": 1,
            "MARITAL_STATUS": 6,
            "EDUGP": 4,
            "OCCUPATION": 12,
            "INCOME": 700,
            "EVER_SMOK": 0,
            "FREQ_ALC": 7,
            "EVER_PHYS": 0,
            "BASE_HYPERTENSION": 1,
            "BASE_HYPERTENSION_DX": 3,  # 1970s -> 1970-01-01
            "BASE_DIABETES": 0,
            "BASE_DIABETES_DX": None,
            "HEIGHT": 150.0,
            "WEIGHT": 72.0,  # BMI = 32.0 (Obesity)
            "WAISTC": 102.0,
            "HIPC": 108.0,
            "SBP1": 144.0,
            "DBP1": 92.0,
            "SBP2": 142.0,
            "DBP2": 90.0,
            "SBP3": 140.0,
            "DBP3": 88.0,
            "BLOOD": 1,
            "FASTING_DURATION": 8.0,
            "BASE_HBA1C": 5.6,
            "PC1": -0.18,
        },
        {
            "PATID": "MCPSDS000073",
            "IID": "MCPS_MCPSRGN000002_MEXB000301",
            "FID": "MCPS_MCPSRGN000002_MEXB000301",
            "YEAR_RECRUITED": 1999,
            "MONTH_RECRUITED": 6,
            "MALE": 1,
            "AGE": 49,
            "COYOACAN": 0,
            "MARITAL_STATUS": 5,
            "EDUGP": 10,
            "OCCUPATION": 11,
            "INCOME": 1200,
            "EVER_SMOK": 1,
            "FREQ_ALC": 3,
            "EVER_PHYS": 1,
            "BASE_HYPERTENSION": 0,
            "BASE_HYPERTENSION_DX": None,
            "BASE_DIABETES": 1,
            "BASE_DIABETES_DX": None,  # Null DX -> recruitment date 1999-06-01
            "HEIGHT": 170.0,
            "WEIGHT": 75.0,  # BMI = 25.95
            "WAISTC": 92.0,
            "HIPC": 98.0,
            "SBP1": 120.0,
            "DBP1": 78.0,
            "SBP2": 118.0,
            "DBP2": 80.0,
            "SBP3": 122.0,
            "DBP3": 79.0,
            "BLOOD": 1,
            "FASTING_DURATION": 10.0,
            "BASE_HBA1C": 7.8,
            "PC1": 1.25,
        },
    ]

    counts = run_stage1_etl(input_data=sample_rows, db_url=db_url)
    assert counts["person"] == 2
    assert counts["genomic_id_map"] == 2
    assert counts["condition_occurrence"] == 2
    assert counts["measurement"] > 10

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        seeded_concepts = [dict(r) for r in conn.execute("SELECT * FROM concept").fetchall()]
        verification = verify_concepts_against_athena(seeded_concepts)
        assert all(r["id_matches"] for r in verification)
        assert all(r["is_valid_standard"] for r in verification)

        persons = [dict(r) for r in conn.execute("SELECT * FROM person ORDER BY person_id").fetchall()]
        assert persons[0]["person_source_value"] == "MCPS_MCPSRGN000001_MEXB000300"
        assert persons[0]["year_of_birth"] == 1933
        assert persons[0]["location_id"] == 1
        assert persons[1]["location_id"] == 2

        conds = [dict(r) for r in conn.execute("SELECT * FROM condition_occurrence ORDER BY person_id").fetchall()]
        assert conds[0]["condition_concept_id"] == 316866
        assert conds[0]["condition_start_date"] == "1970-01-01"
        assert conds[1]["condition_concept_id"] == 201820
        assert conds[1]["condition_start_date"] == "1999-06-01"

        execute_sql_script(conn, REPO_ROOT / "src" / "sql" / "cohorts" / "01_cohort_t2d.sql")
        execute_sql_script(conn, REPO_ROOT / "src" / "sql" / "cohorts" / "02_cohort_hypertension_obesity.sql")

        t2d_ids = [r[0] for r in conn.execute("SELECT subject_id FROM cohort WHERE cohort_definition_id = 1").fetchall()]
        htn_ids = [r[0] for r in conn.execute("SELECT subject_id FROM cohort WHERE cohort_definition_id = 2").fetchall()]
        obe_ids = [r[0] for r in conn.execute("SELECT subject_id FROM cohort WHERE cohort_definition_id = 3").fetchall()]

        assert t2d_ids == [2]
        assert htn_ids == [1]
        assert obe_ids == [1]

        terms = [{"source_code": "HBA1C_TEST", "source_description": "Hemoglobin A1c in Blood"}]
        suggested = suggest_mappings(terms, seeded_concepts, domain_id="Measurement", top_k=1)
        assert len(suggested) == 1
        assert suggested[0]["target_concept_id"] in {3004410, 40762352}


def test_genotyped_gwas_catalog_format_and_cli(tmp_path: Path) -> None:
    from src.python.mcps_etl.__main__ import main

    tsv_path = tmp_path / "genotyped_phenos.txt"
    tsv_path.write_text(
        "FID\tIID\tAGE\tMALE\t02_01_01\tPC1\t11_01_01\t11_02_01\t11_07_01\t11_11_01\t13_01_01\t17_02_01\t17_03_01\n"
        "MCPS_MCPSRGN000001_MEXB000300\tMCPS_MCPSRGN000001_MEXB000300\t58\t0\t1\t-0.18\t136.7\t90.7\t151.5\t36.16\t5.63\t1\t0\n"
        "MCPS_MCPSRGN000002_MEXB000301\tMCPS_MCPSRGN000002_MEXB000301\t46\t0\t1\t7.53\t138.7\t85.3\t147.6\t26.16\t9.10\t1\t1\n",
        encoding="utf-8",
    )

    db_path = tmp_path / "cli_omop.db"
    main(
        [
            "run",
            "--input",
            str(tsv_path),
            "--db-url",
            f"sqlite:///{db_path}",
        ]
    )

    with sqlite3.connect(db_path) as conn:
        execute_sql_script(conn, REPO_ROOT / "src" / "sql" / "cohorts" / "01_cohort_t2d.sql")
        execute_sql_script(conn, REPO_ROOT / "src" / "sql" / "cohorts" / "02_cohort_hypertension_obesity.sql")

        t2d_iids = [
            r[0]
            for r in conn.execute(
                "SELECT g.genotype_iid FROM cohort c JOIN genomic_id_map g ON c.subject_id = g.person_id WHERE c.cohort_definition_id = 1"
            ).fetchall()
        ]
        obe_iids = [
            r[0]
            for r in conn.execute(
                "SELECT g.genotype_iid FROM cohort c JOIN genomic_id_map g ON c.subject_id = g.person_id WHERE c.cohort_definition_id = 3"
            ).fetchall()
        ]
        assert t2d_iids == ["MCPS_MCPSRGN000002_MEXB000301"]
        assert obe_iids == ["MCPS_MCPSRGN000001_MEXB000300"]

    from src.python.mcps_etl.__main__ import run_cohorts_summary

    custom_cohorts_dir = tmp_path / "custom_cohorts"
    custom_cohorts_dir.mkdir()
    (custom_cohorts_dir / "99_custom.sql").write_text(
        """
        INSERT OR REPLACE INTO cohort_definition (cohort_definition_id, cohort_definition_name)
        VALUES (99, 'Custom Tall Cohort (Height >= 150)');
        DELETE FROM cohort WHERE cohort_definition_id = 99;
        INSERT INTO cohort (cohort_definition_id, subject_id, cohort_start_date, cohort_end_date)
        SELECT 99, m.person_id, m.measurement_date, m.measurement_date
        FROM measurement m
        WHERE m.measurement_concept_id = 3036277 AND m.value_as_number >= 150.0;
        """,
        encoding="utf-8",
    )

    summary = run_cohorts_summary(f"sqlite:///{db_path}", cohorts_dir=custom_cohorts_dir)
    custom_entry = next(r for r in summary if r["cohort_definition_id"] == 99)
    assert custom_entry["phenotype"] == "Custom Tall Cohort (Height >= 150)"
    assert custom_entry["n_cases"] == 1
