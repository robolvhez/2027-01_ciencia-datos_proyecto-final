/*
================================================================================
MCPS GWAS PHENOTYPE DEFINITION
================================================================================
Catalogue Code:      17_02_01
Clinical Phenotype:  Hypertension at Baseline (Binary 1/0)
Variable Type:       binary
Units:               None
Description:         1 = self-reported hypertension OR antihypertensive drug OR SBP >= 140 OR DBP >= 90; 0 = control

OMOP CDM v5.4 MAPPING TRANSLATION:
  • `condition_occurrence`: 316866 (SNOMED 38341003 Hypertensive disorder)
  • `drug_exposure`: Antihypertensive ATC classes (DRUG_A1..A11) and RxNorm ingredients
  • `measurement`: 3004249 (LOINC 8480-6 SBP >= 140), 3012888 (LOINC 8462-4 DBP >= 90)
================================================================================
*/

SELECT
    p.person_id,
    CASE
        WHEN MAX(co.condition_occurrence_id) IS NOT NULL
          OR MAX(de_htn.drug_exposure_id) IS NOT NULL
          OR MAX(m_sbp.measurement_id) IS NOT NULL
          OR MAX(m_dbp.measurement_id) IS NOT NULL
        THEN 1
        ELSE 0
    END AS phenotype_value
FROM person p
LEFT JOIN condition_occurrence co
    ON p.person_id = co.person_id
   AND co.condition_concept_id = 316866
LEFT JOIN drug_exposure de_htn
    ON p.person_id = de_htn.person_id
   AND de_htn.drug_concept_id IN (
       21600410, 21601784, 21601823, 21600424, 21601665,
       21601744, 21600382, 21601556, 21601462, 21601517,
       21601532, 1340128,  1341927,  1318853,  1332418,
       1307046,  1353766,  1307863,  1395058,  956874
   )
LEFT JOIN measurement m_sbp
    ON p.person_id = m_sbp.person_id
   AND m_sbp.measurement_concept_id = 3004249
   AND m_sbp.measurement_source_value IN ('SBP_MEAN', '11_01_01', 'SBP1')
   AND m_sbp.value_as_number >= 140.0
   AND (m_sbp.range_low IS NULL OR m_sbp.value_as_number >= m_sbp.range_low)
   AND (m_sbp.range_high IS NULL OR m_sbp.value_as_number <= m_sbp.range_high)
LEFT JOIN measurement m_dbp
    ON p.person_id = m_dbp.person_id
   AND m_dbp.measurement_concept_id = 3012888
   AND m_dbp.measurement_source_value IN ('DBP_MEAN', '11_02_01', 'DBP1')
   AND m_dbp.value_as_number >= 90.0
   AND (m_dbp.range_low IS NULL OR m_dbp.value_as_number >= m_dbp.range_low)
   AND (m_dbp.range_high IS NULL OR m_dbp.value_as_number <= m_dbp.range_high)
GROUP BY p.person_id
ORDER BY p.person_id;
