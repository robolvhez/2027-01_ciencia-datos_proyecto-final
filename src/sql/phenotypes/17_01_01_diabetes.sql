/*
================================================================================
MCPS GWAS PHENOTYPE DEFINITION
================================================================================
Catalogue Code:      17_01_01
Clinical Phenotype:  Broad Diabetes Mellitus at Baseline (Binary 1/0)
Variable Type:       binary
Units:               None
Description:         1 = self-reported diabetes OR antidiabetic medication OR HbA1c >= 6.5% / 48 mmol/mol; 0 = control

OMOP CDM v5.4 MAPPING TRANSLATION:
  • `condition_occurrence`: 201820 (SNOMED 73211009 Diabetes mellitus), 201826 (SNOMED 44054006 T2D)
  • `drug_exposure`: 1503297 (Metformin), 21600749 (Sulfonylureas), 1596977 (Human Insulin),
    21600788 (Other antidiabetics), 1559684 (Glyburide), 1502855 (Tolbutamide), 1594973 (Chlorpropamide)
  • `measurement`: 3004410 (LOINC 4548-4 HbA1c >= 6.5%), 40762352 (LOINC 59261-8 HbA1c >= 48.0 mmol/mol)
================================================================================
*/

SELECT
    p.person_id,
    CASE
        WHEN MAX(co.condition_occurrence_id) IS NOT NULL
          OR MAX(de_dm.drug_exposure_id) IS NOT NULL
          OR MAX(m_dcct.measurement_id) IS NOT NULL
          OR MAX(m_ifcc.measurement_id) IS NOT NULL
        THEN 1
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
