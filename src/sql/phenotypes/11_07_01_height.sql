/*
================================================================================
MCPS GWAS PHENOTYPE DEFINITION
================================================================================
Catalogue Code:      11_07_01
Clinical Phenotype:  Standing Height (Raw, Untransformed)
Variable Type:       continuous
Units:               cm
Description:         Baseline standing height within physiologic bounds (110-220 cm); apply RINT downstream

OMOP CDM v5.4 MAPPING TRANSLATION:
  • `measurement`:
      - `measurement_concept_id = 3036277` -> LOINC 8302-2 ("Body height")
      - `unit_concept_id = 8582`           -> UCUM cm
================================================================================
*/

SELECT
    p.person_id,
    AVG(m.value_as_number) AS phenotype_value
FROM person p
LEFT JOIN measurement m
    ON p.person_id = m.person_id
   AND m.measurement_concept_id = 3036277
   AND (m.range_low IS NULL OR m.value_as_number >= m.range_low)
   AND (m.range_high IS NULL OR m.value_as_number <= m.range_high)
GROUP BY p.person_id
ORDER BY p.person_id;
