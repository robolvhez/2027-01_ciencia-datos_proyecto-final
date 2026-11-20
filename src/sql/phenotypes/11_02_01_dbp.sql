/*
================================================================================
MCPS GWAS PHENOTYPE DEFINITION
================================================================================
Catalogue Code:      11_02_01
Clinical Phenotype:  Mean Diastolic Blood Pressure (Raw, Untransformed)
Variable Type:       continuous
Units:               mm[Hg]
Description:         Mean baseline seated DBP within physiologic bounds (30-160 mmHg); apply RINT downstream

OMOP CDM v5.4 MAPPING TRANSLATION:
  • `measurement`:
      - `measurement_concept_id = 3012888` -> LOINC 8462-4 ("Diastolic blood pressure")
      - `unit_concept_id = 8876`           -> UCUM mm[Hg]
      - Prefers derived `DBP_MEAN` (measurement_type_concept_id = 32817) or `11_02_01`,
        falling back to the mean of raw readings (`DBP1..DBP3`).
================================================================================
*/

SELECT
    p.person_id,
    COALESCE(
        MAX(CASE WHEN m.measurement_source_value IN ('DBP_MEAN', '11_02_01') THEN m.value_as_number END),
        AVG(CASE WHEN m.measurement_source_value IN ('DBP1', 'DBP2', 'DBP3') THEN m.value_as_number END)
    ) AS phenotype_value
FROM person p
LEFT JOIN measurement m
    ON p.person_id = m.person_id
   AND m.measurement_concept_id = 3012888
   AND (m.range_low IS NULL OR m.value_as_number >= m.range_low)
   AND (m.range_high IS NULL OR m.value_as_number <= m.range_high)
GROUP BY p.person_id
ORDER BY p.person_id;
