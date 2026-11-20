/*
================================================================================
MCPS GWAS PHENOTYPE DEFINITION
================================================================================
Catalogue Code:      17_03_01
Clinical Phenotype:  Type 2 Diabetes Mellitus QC-Filtered (3-State Binary: 1/0/NULL)
Variable Type:       binary
Units:               None
Description:         1 = T2D case; 0 = non-diabetic control; NULL = excluded probable T1D (dx age < 35 on insulin)

CLINICAL RATIONALE:
  Unlike a presence-only OMOP cohort table, this GWAS phenotype explicitly preserves
  3-state case/control/exclusion semantics:
    • NULL (Excluded -> NA in GWAS): Probable Type 1 Diabetes (diagnosed before age 35
      AND using insulin [RxNorm 1596977]) — excluded from BOTH cases and controls.
    • 1 (Case): Self-reported diabetes OR antidiabetic medication OR HbA1c >= 6.5% / 48 mmol/mol.
    • 0 (Control): No diabetes evidence and not excluded.

OMOP CDM v5.4 MAPPING TRANSLATION:
  • `condition_occurrence`: 201820 (SNOMED 73211009 Diabetes mellitus), 201826 (SNOMED 44054006 T2D)
  • `drug_exposure`: Antidiabetic drugs (1503297, 21600749, 1596977, 21600788, 1559684, 1502855, 1594973)
  • `measurement`: 3004410 (LOINC 4548-4 HbA1c >= 6.5%), 40762352 (LOINC 59261-8 HbA1c >= 48.0 mmol/mol)
================================================================================
*/

SELECT
    p.person_id,
    CASE
        -- Exclusion: Probable Type 1 Diabetes -> NULL (exported as NA, never a 0 control!)
        WHEN EXISTS (
            SELECT 1
            FROM condition_occurrence co_early
            JOIN drug_exposure de_ins
                ON co_early.person_id = de_ins.person_id
            WHERE co_early.person_id = p.person_id
              AND co_early.condition_concept_id = 201820
              AND (CAST(SUBSTR(co_early.condition_start_date, 1, 4) AS INTEGER) - p.year_of_birth) < 35
              AND de_ins.drug_concept_id = 1596977
        ) THEN NULL
        -- Case: Evidence of diabetes at baseline
        WHEN MAX(co.condition_occurrence_id) IS NOT NULL
          OR MAX(de_dm.drug_exposure_id) IS NOT NULL
          OR MAX(m_dcct.measurement_id) IS NOT NULL
          OR MAX(m_ifcc.measurement_id) IS NOT NULL
        THEN 1
        -- Control: Neither excluded nor diabetic
        ELSE 0
    END AS phenotype_value
FROM person p
LEFT JOIN condition_occurrence co
    ON p.person_id = co.person_id
   AND co.condition_concept_id IN (201820, 201826)
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
LEFT JOIN measurement m_dcct
    ON p.person_id = m_dcct.person_id
   AND m_dcct.measurement_concept_id = 3004410
   AND m_dcct.value_as_number >= 6.5
   AND (m_dcct.range_low IS NULL OR m_dcct.value_as_number >= m_dcct.range_low)
   AND (m_dcct.range_high IS NULL OR m_dcct.value_as_number <= m_dcct.range_high)
LEFT JOIN measurement m_ifcc
    ON p.person_id = m_ifcc.person_id
   AND m_ifcc.measurement_concept_id = 40762352
   AND m_ifcc.value_as_number >= 48.0
   AND (m_ifcc.range_low IS NULL OR m_ifcc.value_as_number >= m_ifcc.range_low)
   AND (m_ifcc.range_high IS NULL OR m_ifcc.value_as_number <= m_ifcc.range_high)
GROUP BY p.person_id
ORDER BY p.person_id;
