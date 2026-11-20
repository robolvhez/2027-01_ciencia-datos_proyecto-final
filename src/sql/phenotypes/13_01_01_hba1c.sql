/*
================================================================================
MCPS GWAS PHENOTYPE DEFINITION
================================================================================
Catalogue Code:      13_01_01
Clinical Phenotype:  Baseline Glycated Hemoglobin HbA1c DCCT (Raw, Untransformed)
Variable Type:       continuous
Units:               %
Description:         Baseline blood HbA1c DCCT (%) within physiologic bounds (3-25%); apply RINT downstream

OMOP CDM v5.4 MAPPING TRANSLATION:
  • `measurement`:
      - `measurement_concept_id = 3004410` -> LOINC 4548-4 ("Hemoglobin A1c/Hemoglobin.total in Blood")
      - `unit_concept_id = 8554`           -> UCUM %
================================================================================
*/

SELECT
    p.person_id,
    AVG(m.value_as_number) AS phenotype_value
FROM person p
LEFT JOIN measurement m
    ON p.person_id = m.person_id
   AND m.measurement_concept_id = 3004410
   AND (m.range_low IS NULL OR m.value_as_number >= m.range_low)
   AND (m.range_high IS NULL OR m.value_as_number <= m.range_high)
GROUP BY p.person_id
ORDER BY p.person_id;
