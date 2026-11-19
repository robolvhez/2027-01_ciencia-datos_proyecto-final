/*
================================================================================
MCPS GWAS PHENOTYPE CATALOGUE COHORT DEFINITION
================================================================================
Catalogue Code:        17_03_01
Cohort Definition ID:  2
Clinical Phenotype:    Type 2 Diabetes Mellitus (QC-Filtered)
Data Showcase Fields:  34 (BASE_DIABETES), 76 (BASE_DIABETES_DX), 49 (DRUG_D1..D4),
                       69 (BASE_HBA1C_DCCT), 1142 (BASE_HBA1C_IFCC)

CLINICAL RATIONALE (For Clinicians & Non-OMOP Reviewers):
  Identifies MCPS participants with Type 2 Diabetes Mellitus (T2D) at baseline using
  the Oxford MCPS GWAS Catalogue quality-control definition (`17_03_01`):
    • INCLUSION:
        1. Self-reported prior diagnosis of diabetes (BASE_DIABETES = 1), OR
        2. Regular use (>1 month) of any antidiabetic medication (DRUG_D1..D4 / RxNorm), OR
        3. Baseline blood HbA1c >= 6.5% (DCCT) / >= 48.0 mmol/mol (IFCC).
    • EXCLUSION (Probable Type 1 Diabetes Filter):
        Excludes participants whose imputed age at diabetes diagnosis was < 35 years
        (`condition_start_date` year minus `person.year_of_birth` < 35) AND who are
        treated with insulin at baseline (`DRUG_D3 = 1` / RxNorm `1596977`).

OMOP CDM v5.4 MAPPING TRANSLATION:
  • `condition_occurrence`:
      - 201820 -> SNOMED CT 73211009 ("Diabetes mellitus", with `condition_start_date`
                  imputed from decade of diagnosis `BASE_DIABETES_DX`)
      - 201826 -> SNOMED CT 44054006 ("Type 2 diabetes mellitus")
  • `drug_exposure`:
      - Antidiabetic drugs: 1503297 (Metformin), 21600749 (Sulfonylureas),
        1596977 (Human Insulin), 21600788 (Other antidiabetics), 1559684 (Glyburide),
        1502855 (Tolbutamide), 1594973 (Chlorpropamide)
  • `measurement`:
      - 3004410  -> LOINC 4548-4  (HbA1c DCCT >= 6.5%)
      - 40762352 -> LOINC 59261-8 (HbA1c IFCC >= 48.0 mmol/mol)
================================================================================
*/

INSERT OR REPLACE INTO cohort_definition (
    cohort_definition_id,
    cohort_definition_name,
    cohort_definition_description
) VALUES (
    2,
    'T2D (17_03_01)',
    'Type 2 Diabetes (17_03_01): Self-reported diabetes (SNOMED 201820/201826) OR antidiabetic medication OR HbA1c >= 6.5%, excluding probable T1D (age at diagnosis < 35 on insulin)'
);

DELETE FROM cohort WHERE cohort_definition_id = 2;

INSERT INTO cohort (cohort_definition_id, subject_id, cohort_start_date, cohort_end_date)
SELECT
    2 AS cohort_definition_id,
    p.person_id AS subject_id,
    MIN(op.observation_period_start_date) AS cohort_start_date,
    MAX(op.observation_period_end_date) AS cohort_end_date
FROM person p
JOIN observation_period op
    ON p.person_id = op.person_id
-- Inclusion 1: Self-reported diabetes diagnosis in `condition_occurrence`
LEFT JOIN condition_occurrence co
    ON p.person_id = co.person_id
   AND co.condition_concept_id IN (201820, 201826)
-- Inclusion 2: Regular use (>1 month) of any antidiabetic medication in `drug_exposure`
LEFT JOIN drug_exposure de_dm
    ON p.person_id = de_dm.person_id
   AND de_dm.drug_concept_id IN (
       1503297,  -- RxNorm 6809: Metformin (DRUG_D1)
       21600749, -- ATC A10BB: Sulfonylureas (DRUG_D2)
       1596977,  -- RxNorm 253182: Human Insulin (DRUG_D3)
       21600788, -- ATC A10BX: Other blood glucose lowering drugs (DRUG_D4)
       1559684,  -- RxNorm 4815: Glyburide / Glibenclamide
       1502855,  -- RxNorm 10635: Tolbutamide
       1594973   -- RxNorm 2404: Chlorpropamide
   )
-- Inclusion 3a: Baseline HbA1c >= 6.5% (DCCT)
LEFT JOIN measurement m_dcct
    ON p.person_id = m_dcct.person_id
   AND m_dcct.measurement_concept_id = 3004410
   AND m_dcct.value_as_number >= 6.5
   AND (m_dcct.range_low IS NULL OR m_dcct.value_as_number >= m_dcct.range_low)
   AND (m_dcct.range_high IS NULL OR m_dcct.value_as_number <= m_dcct.range_high)
-- Inclusion 3b: Baseline HbA1c >= 48.0 mmol/mol (IFCC)
LEFT JOIN measurement m_ifcc
    ON p.person_id = m_ifcc.person_id
   AND m_ifcc.measurement_concept_id = 40762352
   AND m_ifcc.value_as_number >= 48.0
   AND (m_ifcc.range_low IS NULL OR m_ifcc.value_as_number >= m_ifcc.range_low)
   AND (m_ifcc.range_high IS NULL OR m_ifcc.value_as_number <= m_ifcc.range_high)
WHERE (
    co.condition_occurrence_id IS NOT NULL
    OR de_dm.drug_exposure_id IS NOT NULL
    OR m_dcct.measurement_id IS NOT NULL
    OR m_ifcc.measurement_id IS NOT NULL
)
-- Exclusion: Probable Type 1 Diabetes (diagnosed before age 35 AND on insulin 1596977)
AND NOT EXISTS (
    SELECT 1
    FROM condition_occurrence co_early
    JOIN drug_exposure de_ins
        ON co_early.person_id = de_ins.person_id
    WHERE co_early.person_id = p.person_id
      AND co_early.condition_concept_id = 201820
      AND (CAST(SUBSTR(co_early.condition_start_date, 1, 4) AS INTEGER) - p.year_of_birth) < 35
      AND de_ins.drug_concept_id = 1596977
)
GROUP BY p.person_id;
