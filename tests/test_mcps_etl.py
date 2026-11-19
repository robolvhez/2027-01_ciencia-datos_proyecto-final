"""Automated tests for MCPS -> OMOP CDM v5.4 ETL, strict RegID linkage, drug exposures, and single-code SQL cohorts."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.python.mcps_etl.__main__ import main, run_cohorts_summary
from src.python.mcps_etl.id_linkage import (
    EXPECTED_GENOTYPED_INDIVIDUALS,
    build_genomic_id_map,
    parse_regeneron_iid,
    read_id_bridge,
    read_plink_fam,
    validate_regid_linkage,
)
from src.python.mcps_etl.load import run_stage1_etl
from src.python.mcps_etl.mapper import (
    MIN_MEDICATION_MENTION_COUNT,
    profile_medication_terms,
    suggest_mappings,
    verify_concepts_against_athena,
)
from src.python.mcps_etl.transform import compute_drug_exposure, normalize_medication_text

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_parse_regeneron_iid_and_strict_regid_linkage(tmp_path: Path) -> None:
    rgc_id, mexb_id = parse_regeneron_iid("MCPS_MCPSRGN000002_MEXB000301")
    assert rgc_id == "MCPSRGN000002"
    assert mexb_id == "MEXB000301"

    # Test PLINK .fam reader and duplicate detection
    fam_path = tmp_path / "cohort.fam"
    fam_path.write_text(
        "MCPS_MCPSRGN000001_MEXB000300 MCPS_MCPSRGN000001_MEXB000300 0 0 2 -9\n"
        "MCPS_MCPSRGN000002_MEXB000301 MCPS_MCPSRGN000002_MEXB000301 0 0 1 -9\n",
        encoding="utf-8",
    )
    fam_samples = read_plink_fam(fam_path)
    assert len(fam_samples) == 2

    dup_fam_path = tmp_path / "dup.fam"
    dup_fam_path.write_text(
        "FID1 MCPS_MCPSRGN000001_MEXB000300 0 0 2 -9\n"
        "FID2 MCPS_MCPSRGN000001_MEXB000300 0 0 2 -9\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate RegID"):
        read_plink_fam(dup_fam_path)

    # Test ID bridge reader and duplicate RegID detection
    bridge_path = tmp_path / "bridge.tsv"
    bridge_path.write_text(
        "PATID\tIID\tFID\n"
        "MCPSDS000007\tMCPS_MCPSRGN000001_MEXB000300\tMCPS_MCPSRGN000001_MEXB000300\n"
        "MCPSDS000073\tMCPS_MCPSRGN000002_MEXB000301\tMCPS_MCPSRGN000002_MEXB000301\n"
        "MCPSDS000088\tMCPS_MCPSRGN000999_MEXB000999\tMCPS_MCPSRGN000999_MEXB000999\n",
        encoding="utf-8",
    )
    id_bridge = read_id_bridge(bridge_path)

    dup_bridge_path = tmp_path / "dup_bridge.tsv"
    dup_bridge_path.write_text(
        "PATID\tIID\tFID\n"
        "MCPSDS000007\tMCPS_MCPSRGN000001_MEXB000300\tMCPS_MCPSRGN000001_MEXB000300\n"
        "MCPSDS000073\tMCPS_MCPSRGN000001_MEXB000300\tMCPS_MCPSRGN000001_MEXB000300\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate RegID"):
        read_id_bridge(dup_bridge_path)

    rows = [
        {"PATID": "MCPSDS000007", "PC1": 0.12},
        {"PATID": "MCPSDS000073", "PC1": -0.34},
        {"PATID": "MCPSDS000088", "PC1": 0.05},  # In bridge, but absent from .fam -> not genotyped
        {"PATID": "MCPSDS000099", "PC1": None},  # Unmapped PATID -> never computed, is_genotyped = 0
    ]

    gmap = build_genomic_id_map(rows, id_bridge=id_bridge, fam_samples=fam_samples)
    assert [r["is_genotyped"] for r in gmap] == [1, 1, 0, 0]
    assert [row["IS_GENOTYPED"] for row in rows] == [1, 1, 0, 0]
    assert gmap[0]["genotype_iid"] == "MCPS_MCPSRGN000001_MEXB000300"
    assert gmap[2]["genotype_iid"] is None
    assert gmap[3]["genotype_iid"] is None

    summary = validate_regid_linkage(gmap, expected_genotyped=2)
    assert summary["n_total"] == 4
    assert summary["n_genotyped"] == 2
    assert summary["matches_expected_140831"] is True
    assert EXPECTED_GENOTYPED_INDIVIDUALS == 140_831


def test_normalize_medication_text_and_compute_drug_exposure() -> None:
    assert normalize_medication_text("  drug:   captopril \n ") == "DRUG: CAPTOPRIL"
    assert normalize_medication_text("NA") is None
    assert normalize_medication_text(None) is None

    rows = [
        {
            "person_id": 1,
            "YEAR_RECRUITED": 2000,
            "MONTH_RECRUITED": 5,
            "DRUG_A2": 1,  # ACE inhibitors -> ATC C09AA (21601784)
            "DRUG_C3": 1,  # Aspirin -> RxNorm 1191 (1112807)
            "MEDICATION1": "  drug: captopril ",  # RxNorm 1998 (1340128)
            "MEDICATION2": "UNLISTED HERBAL TEA",
        },
        {
            "person_id": 2,
            "YEAR_RECRUITED": 1999,
            "MONTH_RECRUITED": 11,
            "DRUG_D1": 1,  # Metformin -> RxNorm 6809 (1503297)
            "DRUG_D2": 1,  # Sulphonylurea -> ATC A10BB (21600749)
            "MEDICATION1": "BRAND: GLIBENCLAMIDA",  # RxNorm 4815 (1559684)
            "MEDICATION2": "BRAND: BI-EUGLUCON M.",  # RxNorm 6809 (1503297)
        },
    ]

    exposures_strict = compute_drug_exposure(rows, include_unmapped_text=False)
    assert len(exposures_strict) == 7
    p1_cids = [r["drug_concept_id"] for r in exposures_strict if r["person_id"] == 1]
    p2_cids = [r["drug_concept_id"] for r in exposures_strict if r["person_id"] == 2]
    assert p1_cids == [21601784, 1112807, 1340128]
    assert p2_cids == [1503297, 21600749, 1559684, 1503297]
    assert all(r["days_supply"] == 30 for r in exposures_strict)
    assert all(r["drug_type_concept_id"] == 32865 for r in exposures_strict)

    exposures_with_unmapped = compute_drug_exposure(rows, include_unmapped_text=True)
    assert len(exposures_with_unmapped) == 8
    unmapped_row = next(r for r in exposures_with_unmapped if r["drug_source_value"] == "UNLISTED HERBAL TEA")
    assert unmapped_row["drug_concept_id"] == 0


def test_profile_medication_terms_traceability() -> None:
    assert MIN_MEDICATION_MENTION_COUNT == 250
    rows = [
        {"MEDICATION1": "DRUG: CAPTOPRIL", "MEDICATION2": "BRAND: GLIBENCLAMIDA", "MEDICATION3": ""},
        {"MEDICATION1": "drug: captopril", "MEDICATION2": "BRAND: GLIBENCLAMIDA", "MEDICATION3": "RARE_TYPO_1"},
        {"MEDICATION1": "DRUG: CAPTOPRIL", "MEDICATION2": None, "MEDICATION3": None},
    ]
    report = profile_medication_terms(rows, min_count=2)
    assert report["min_count_threshold"] == 2
    assert report["total_mentions"] == 6
    assert report["mapped_mentions"] == 5
    assert report["coverage_pct"] == 83.33
    assert report["distinct_terms_above_threshold"] == 2
    assert report["unmapped_terms_above_threshold"] == []
    assert [t["source_code"] for t in report["qualifying_terms"]] == ["DRUG: CAPTOPRIL", "BRAND: GLIBENCLAMIDA"]


def test_etl_and_all_ten_single_code_sql_cohorts(tmp_path: Path) -> None:
    db_path = tmp_path / "test_mcps_omop.db"
    db_url = f"sqlite:///{db_path}"

    sample_rows = [
        {
            # Person 1: Controlled hypertension on ACE inhibitor (SBP=128, BASE_HYPERTENSION=0, DRUG_A2=1),
            # Aspirin (DRUG_C3=1), Digoxin (DRUG_B2=1), Obesity (BMI=32.0), Genotyped
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
            "HRT_USE": 1,
            "CONTRACEPTIVE": 1,
            "BASE_HYPERTENSION": 0,
            "BASE_DIABETES": 0,
            "DRUG_A2": 1,
            "DRUG_B2": 1,
            "DRUG_C3": 1,
            "MEDICATION1": "DRUG: CAPTOPRIL",
            "HEIGHT": 150.0,
            "WEIGHT": 72.0,  # BMI = 32.0
            "WAISTC": 102.0,
            "HIPC": 108.0,
            "SBP1": 128.0,
            "DBP1": 80.0,
            "SBP2": 126.0,
            "DBP2": 78.0,
            "SBP3": 127.0,
            "DBP3": 79.0,
            "BLOOD": 1,
            "FASTING_DURATION": 8.0,
            "BASE_HBA1C": 5.6,
            "PC1": -0.18,
        },
        {
            # Person 2: Controlled T2D on Metformin + Sulphonylurea (BASE_DIABETES=0, HbA1c=5.9, DRUG_D1=1, DRUG_D2=1),
            # Statin (DRUG_E1=1), Bronchodilator (DRUG_H1=1), Genotyped
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
            "BASE_DIABETES": 0,
            "DRUG_D1": 1,
            "DRUG_D2": 1,
            "DRUG_E1": 1,
            "DRUG_H1": 1,
            "MEDICATION1": "BRAND: GLIBENCLAMIDA",
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
            "BASE_HBA1C": 5.9,
            "PC1": 1.25,
        },
        {
            # Person 3: Probable Type 1 Diabetes (Age 40 in 2000 -> YOB 1960; diagnosed in 1980s [DX=4 -> 1980, age 20 < 35]
            # and on insulin DRUG_D3=1) -> Included in 17_01_01 (Cohort 1), Excluded from 17_03_01 T2D (Cohort 2)!
            "PATID": "MCPSDS000099",
            "IID": None,
            "FID": None,
            "YEAR_RECRUITED": 2000,
            "MONTH_RECRUITED": 3,
            "MALE": 1,
            "AGE": 40,
            "COYOACAN": 1,
            "BASE_DIABETES": 1,
            "BASE_DIABETES_DX": 4,  # 1980-01-01 -> age at dx = 1980 - 1960 = 20 (< 35)
            "DRUG_D3": 1,  # Insulin
            "BASE_HBA1C": 8.4,
        },
    ]

    counts = run_stage1_etl(input_data=sample_rows, db_url=db_url)
    assert counts["person"] == 3
    assert counts["genomic_id_map"] == 3
    assert counts["drug_exposure"] == 10

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        seeded_concepts = [dict(r) for r in conn.execute("SELECT * FROM concept").fetchall()]
        verification = verify_concepts_against_athena(seeded_concepts)
        assert all(r["id_matches"] for r in verification)
        assert all(r["is_valid_standard"] for r in verification)

        # Also test streaming verification from a tab-delimited Athena CONCEPT.csv file
        athena_tsv = tmp_path / "CONCEPT.csv"
        with athena_tsv.open("w", encoding="utf-8") as handle:
            cols = list(seeded_concepts[0].keys())
            handle.write("\t".join(cols) + "\n")
            for c in seeded_concepts:
                handle.write("\t".join("" if c[k] is None else str(c[k]) for k in cols) + "\n")
        file_verification = verify_concepts_against_athena(athena_tsv)
        assert all(r["id_matches"] for r in file_verification)
        assert all(r["is_valid_standard"] for r in file_verification)

        # Verify standard OMOP observation 45769413 (SNOMED 708060009: Genotype determination)
        geno_obs = [
            dict(r)
            for r in conn.execute(
                "SELECT person_id, value_as_number, value_as_string FROM observation WHERE observation_concept_id = 45769413 ORDER BY person_id"
            ).fetchall()
        ]
        assert geno_obs == [
            {"person_id": 1, "value_as_number": 1, "value_as_string": "Genotyped"},
            {"person_id": 2, "value_as_number": 1, "value_as_string": "Genotyped"},
            {"person_id": 3, "value_as_number": 0, "value_as_string": "Not genotyped"},
        ]

        terms = [{"source_code": "HBA1C_TEST", "source_description": "Hemoglobin A1c in Blood"}]
        suggested = suggest_mappings(terms, seeded_concepts, domain_id="Measurement", top_k=1)
        assert len(suggested) == 1
        assert suggested[0]["target_concept_id"] in {3004410, 40762352}

    # Execute all 10 single-code SQL cohorts via run_cohorts_summary
    summary = run_cohorts_summary(db_url)
    assert len(summary) >= 10

    with sqlite3.connect(db_path) as conn:
        by_cohort: dict[int, list[int]] = {}
        for cid in range(1, 11):
            by_cohort[cid] = [
                r[0]
                for r in conn.execute(
                    "SELECT subject_id FROM cohort WHERE cohort_definition_id = ? ORDER BY subject_id",
                    (cid,),
                ).fetchall()
            ]

    assert by_cohort[1] == [2, 3]  # 17_01_01 Broad Diabetes: Person 2 (on meds) + Person 3 (early-onset insulin)
    assert by_cohort[2] == [2]  # 17_03_01 T2D QC-filtered: Person 2 included, Person 3 excluded (age_dx=20 < 35 & insulin)
    assert by_cohort[3] == [1]  # 17_02_01 Hypertension: Person 1 (controlled on DRUG_A2 / Captopril)
    assert by_cohort[4] == [2, 3]  # 09_01_01 Antidiabetic Meds: Person 2 (D1, D2) + Person 3 (D3)
    assert by_cohort[5] == [1]  # 09_02_01 Antihypertensive Meds: Person 1 (A2)
    assert by_cohort[6] == [1]  # 09_03_01 Antithrombotic Meds: Person 1 (C3 Aspirin)
    assert by_cohort[7] == [2]  # 09_04_01 Lipid-Lowering Meds: Person 2 (E1 Statin)
    assert by_cohort[8] == [1]  # 09_05_01 Other CVD Meds: Person 1 (B2 Digoxin)
    assert by_cohort[9] == [2]  # 09_06_01 Respiratory Meds: Person 2 (H1 Bronchodilator)
    assert by_cohort[10] == [1]  # 11_11_01 Obesity (BMI >= 30): Person 1 (BMI = 32.0)


def test_cli_run_with_fam_and_profile_medications(tmp_path: Path) -> None:
    csv_path = tmp_path / "baseline_sample.csv"
    csv_path.write_text(
        "PATID,YEAR_RECRUITED,MONTH_RECRUITED,AGE,MALE,COYOACAN,HEIGHT,WEIGHT,DRUG_A2,MEDICATION1\n"
        "MCPSDS000007,2000,6,58,0,1,151.5,83.0,1,DRUG: CAPTOPRIL\n"
        "MCPSDS000073,2001,4,46,1,0,170.0,70.0,0,\n",
        encoding="utf-8",
    )
    bridge_path = tmp_path / "bridge.tsv"
    bridge_path.write_text(
        "PATID\tIID\tFID\n"
        "MCPSDS000007\tMCPS_MCPSRGN000001_MEXB000300\tMCPS_MCPSRGN000001_MEXB000300\n"
        "MCPSDS000073\tMCPS_MCPSRGN000002_MEXB000301\tMCPS_MCPSRGN000002_MEXB000301\n",
        encoding="utf-8",
    )
    fam_path = tmp_path / "sample.fam"
    fam_path.write_text(
        "MCPS_MCPSRGN000001_MEXB000300 MCPS_MCPSRGN000001_MEXB000300 0 0 2 -9\n",
        encoding="utf-8",
    )

    db_path = tmp_path / "cli_omop.db"
    main(
        [
            "run",
            "--input",
            str(csv_path),
            "--id-bridge",
            str(bridge_path),
            "--fam",
            str(fam_path),
            "--db-url",
            f"sqlite:///{db_path}",
        ]
    )
    main(["profile-medications", "--input", str(csv_path), "--min-count", "1"])
    main(["cohorts", "--db-url", f"sqlite:///{db_path}"])

    with sqlite3.connect(db_path) as conn:
        gmap = conn.execute("SELECT person_id, genotype_iid, is_genotyped FROM genomic_id_map ORDER BY person_id").fetchall()
        assert gmap == [
            (1, "MCPS_MCPSRGN000001_MEXB000300", 1),
            (2, None, 0),
        ]
