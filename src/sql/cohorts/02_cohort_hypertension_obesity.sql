-- Cohort Definition 2: Hypertension (MCPS Phenotype 17_02_01)
--   Condition: SNOMED 38341003 (OMOP 316866: Hypertensive disorder)
--   Measurement: LOINC 8480-6 (OMOP 3004249: SBP >= 140 mmHg) or LOINC 8462-4 (OMOP 3012888: DBP >= 90 mmHg)
-- Cohort Definition 3: Obesity (BMI >= 30 kg/m2)
--   Measurement: LOINC 39156-5 (OMOP 3038553: Body mass index >= 30.0 kg/m2)

INSERT OR REPLACE INTO cohort_definition (
    cohort_definition_id,
    cohort_definition_name,
    cohort_definition_description
) VALUES
(
    2,
    'Hypertension (17_02_01)',
    'Hypertension: SNOMED 38341003 (OMOP 316866) or LOINC SBP >= 140 mmHg (OMOP 3004249) or DBP >= 90 mmHg (OMOP 3012888)'
),
(
    3,
    'Obesity (BMI >= 30)',
    'Obesity: LOINC 39156-5 Body mass index >= 30.0 kg/m2 (OMOP 3038553)'
);

DELETE FROM cohort WHERE cohort_definition_id IN (2, 3);

-- Populate Hypertension Cohort (cohort_definition_id = 2)
INSERT INTO cohort (cohort_definition_id, subject_id, cohort_start_date, cohort_end_date)
SELECT
    2 AS cohort_definition_id,
    p.person_id AS subject_id,
    MIN(op.observation_period_start_date) AS cohort_start_date,
    MAX(op.observation_period_end_date) AS cohort_end_date
FROM person p
JOIN observation_period op ON p.person_id = op.person_id
LEFT JOIN condition_occurrence co
    ON p.person_id = co.person_id
   AND co.condition_concept_id = 316866
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
WHERE co.condition_occurrence_id IS NOT NULL
   OR m_sbp.measurement_id IS NOT NULL
   OR m_dbp.measurement_id IS NOT NULL
GROUP BY p.person_id;

-- Populate Obesity Cohort (cohort_definition_id = 3)
INSERT INTO cohort (cohort_definition_id, subject_id, cohort_start_date, cohort_end_date)
SELECT
    3 AS cohort_definition_id,
    p.person_id AS subject_id,
    MIN(op.observation_period_start_date) AS cohort_start_date,
    MAX(op.observation_period_end_date) AS cohort_end_date
FROM person p
JOIN observation_period op ON p.person_id = op.person_id
JOIN measurement m_bmi
    ON p.person_id = m_bmi.person_id
   AND m_bmi.measurement_concept_id = 3038553
   AND m_bmi.value_as_number >= 30.0
   AND (m_bmi.range_low IS NULL OR m_bmi.value_as_number >= m_bmi.range_low)
   AND (m_bmi.range_high IS NULL OR m_bmi.value_as_number <= m_bmi.range_high)
GROUP BY p.person_id;
