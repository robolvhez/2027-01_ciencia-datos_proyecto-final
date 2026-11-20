/*
================================================================================
MCPS GWAS PHENOTYPE DEFINITION
================================================================================
Catalogue Code:      11_11_01
Clinical Phenotype:  Body Mass Index (Raw, Untransformed)
Variable Type:       continuous
Units:               kg/m2
Description:         Baseline BMI within physiologic bounds (12-80 kg/m2); apply RINT downstream

OMOP CDM v5.4 MAPPING TRANSLATION:
  • `measurement`:
      - `measurement_concept_id = 3038553` -> LOINC 39156-5 ("Body mass index (BMI) [Ratio]")
      - `unit_concept_id = 9531`           -> UCUM kg/m2
================================================================================
*/

SELECT
    p.person_id,
    AVG(m.value_as_number) AS phenotype_value
FROM person p
LEFT JOIN measurement m
    ON p.person_id = m.person_id
   AND m.measurement_concept_id = 3038553
   AND (m.range_low IS NULL OR m.value_as_number >= m.range_low)
   AND (m.range_high IS NULL OR m.value_as_number <= m.range_high)
GROUP BY p.person_id
ORDER BY p.person_id;
