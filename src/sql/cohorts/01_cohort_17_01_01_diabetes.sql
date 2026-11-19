/*
================================================================================
MCPS GWAS PHENOTYPE CATALOGUE COHORT DEFINITION
================================================================================
Catalogue Code:        17_01_01
Cohort Definition ID:  1
Clinical Phenotype:    Broad Diabetes Mellitus at Baseline
Data Showcase Fields:  34 (BASE_DIABETES), 49 (DRUG_D1..D4 / MEDICATION1..3),
                       69 (BASE_HBA1C_DCCT), 1142 (BASE_HBA1C_IFCC)

CLINICAL RATIONALE (For Clinicians & Non-OMOP Reviewers):
  Identifies all MCPS participants with evidence of diabetes at baseline recruitment,
  combining three complementary clinical criteria:
    1. Self-reported prior physician diagnosis of diabetes (BASE_DIABETES = 1).
    2. Regular use (>1 month) of any antidiabetic medication at baseline:
       - Biguanides / Metformin (DRUG_D1, Bi-Euglucon M, Metformina)
       - Sulphonylureas (DRUG_D2, Glibenclamide/Glyburide, Tolbutamide, Chlorpropamide)
       - Human Insulin (DRUG_D3, Insulina Humana)
       - Other blood glucose lowering agents (DRUG_D4)
    3. Undiagnosed/uncontrolled baseline hyperglycaemia measured in venous blood:
       - Glycated haemoglobin HbA1c >= 6.5% (DCCT units) OR >= 48.0 mmol/mol (IFCC units).

OMOP CDM v5.4 MAPPING TRANSLATION:
  • `condition_occurrence`:
      - 201820 -> SNOMED CT 73211009 ("Diabetes mellitus")
      - 201826 -> SNOMED CT 44054006 ("Type 2 diabetes mellitus")
  • `drug_exposure`:
      - 1503297  -> RxNorm 6809   ("metformin" / DRUG_D1)
      - 21600749 -> ATC A10BB     ("Sulfonylureas" / DRUG_D2)
      - 1596977  -> RxNorm 253182 ("insulin, regular, human" / DRUG_D3)
      - 21600788 -> ATC A10BX     ("Other blood glucose lowering drugs, excl. insulins" / DRUG_D4)
      - 1559684  -> RxNorm 4815   ("glyburide" / Glibenclamide)
      - 1502855  -> RxNorm 10635  ("tolbutamide")
      - 1594973  -> RxNorm 2404   ("chlorpropamide" / Insogen)
  • `measurement`:
      - 3004410  -> LOINC 4548-4  ("Hemoglobin A1c/Hemoglobin.total in Blood", DCCT % >= 6.5)
      - 40762352 -> LOINC 59261-8 ("Hemoglobin A1c/Hemoglobin.total in Blood by IFCC protocol", mmol/mol >= 48.0)
================================================================================
*/

INSERT OR REPLACE INTO cohort_definition (
    cohort_definition_id,
    cohort_definition_name,
    cohort_definition_description
) VALUES (
    1,
    'Diabetes (17_01_01)',
    'Broad Diabetes (17_01_01): Self-reported diabetes (SNOMED 201820) OR antidiabetic medication (DRUG_D1..D4 / RxNorm / ATC) OR HbA1c >= 6.5% (LOINC 3004410) / >= 48 mmol/mol (LOINC 40762352)'
);

DELETE FROM cohort WHERE cohort_definition_id = 1;

INSERT INTO cohort (cohort_definition_id, subject_id, cohort_start_date, cohort_end_date)
SELECT
    1 AS cohort_definition_id,
    p.person_id AS subject_id,
    MIN(op.observation_period_start_date) AS cohort_start_date,
    MAX(op.observation_period_end_date) AS cohort_end_date
FROM person p
JOIN observation_period op
    ON p.person_id = op.person_id
-- Criterion 1: Self-reported diabetes diagnosis in `condition_occurrence`
LEFT JOIN condition_occurrence co
    ON p.person_id = co.person_id
   AND co.condition_concept_id IN (201820, 201826)
-- Criterion 2: Regular use (>1 month) of antidiabetic medication in `drug_exposure`
LEFT JOIN drug_exposure de_dm
    ON p.person_id = de_dm.person_id
   AND de_dm.drug_concept_id IN (
       1503297,  -- RxNorm 6809: Metformin (DRUG_D1 / Bi-Euglucon M / Metformina)
       21600749, -- ATC A10BB: Sulfonylureas (DRUG_D2)
       1596977,  -- RxNorm 253182: Human Insulin (DRUG_D3 / Insulina Humana)
       21600788, -- ATC A10BX: Other blood glucose lowering drugs (DRUG_D4)
       1559684,  -- RxNorm 4815: Glyburide / Glibenclamide (Euglucon / Mellitron)
       1502855,  -- RxNorm 10635: Tolbutamide
       1594973   -- RxNorm 2404: Chlorpropamide (Insogen)
   )
-- Criterion 3a: Baseline HbA1c >= 6.5% (DCCT units) in `measurement`
LEFT JOIN measurement m_dcct
    ON p.person_id = m_dcct.person_id
   AND m_dcct.measurement_concept_id = 3004410
   AND m_dcct.value_as_number >= 6.5
   AND (m_dcct.range_low IS NULL OR m_dcct.value_as_number >= m_dcct.range_low)
   AND (m_dcct.range_high IS NULL OR m_dcct.value_as_number <= m_dcct.range_high)
-- Criterion 3b: Baseline HbA1c >= 48.0 mmol/mol (IFCC units) in `measurement`
LEFT JOIN measurement m_ifcc
    ON p.person_id = m_ifcc.person_id
   AND m_ifcc.measurement_concept_id = 40762352
   AND m_ifcc.value_as_number >= 48.0
   AND (m_ifcc.range_low IS NULL OR m_ifcc.value_as_number >= m_ifcc.range_low)
   AND (m_ifcc.range_high IS NULL OR m_ifcc.value_as_number <= m_ifcc.range_high)
WHERE co.condition_occurrence_id IS NOT NULL
   OR de_dm.drug_exposure_id IS NOT NULL
   OR m_dcct.measurement_id IS NOT NULL
   OR m_ifcc.measurement_id IS NOT NULL
GROUP BY p.person_id;
