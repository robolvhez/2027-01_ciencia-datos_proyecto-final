/*
================================================================================
MCPS GWAS PHENOTYPE DEFINITION
================================================================================
Catalogue Code:      11_01_01
Clinical Phenotype:  Mean Systolic Blood Pressure (Raw, Untransformed)
Variable Type:       continuous
Units:               mm[Hg]
Description:         Mean baseline seated SBP within physiologic bounds (60-260 mmHg); apply RINT downstream

OMOP CDM v5.4 MAPPING TRANSLATION:
  • `measurement`:
      - `measurement_concept_id = 3004249` -> LOINC 8480-6 ("Systolic blood pressure")
      - `unit_concept_id = 8876`           -> UCUM mm[Hg]
      - Prefers derived `SBP_MEAN` (measurement_type_concept_id = 32817) or `11_01_01`,
        falling back to the mean of raw readings (`SBP1..SBP3`).
================================================================================
*/

SELECT
    p.person_id,
    COALESCE(
        MAX(CASE WHEN m.measurement_source_value IN ('SBP_MEAN', '11_01_01') THEN m.value_as_number END),
        AVG(CASE WHEN m.measurement_source_value IN ('SBP1', 'SBP2', 'SBP3') THEN m.value_as_number END)
    ) AS phenotype_value
FROM person p
LEFT JOIN measurement m
    ON p.person_id = m.person_id
   AND m.measurement_concept_id = 3004249
   AND (m.range_low IS NULL OR m.value_as_number >= m.range_low)
   AND (m.range_high IS NULL OR m.value_as_number <= m.range_high)
GROUP BY p.person_id
ORDER BY p.person_id;
