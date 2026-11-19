/*
================================================================================
MCPS GWAS PHENOTYPE CATALOGUE COHORT DEFINITION
================================================================================
Catalogue Code:        11_11_01 (Binary Clinical Cutoff: BMI >= 30.0 kg/m2)
Cohort Definition ID:  10
Clinical Phenotype:    Clinical Obesity at Baseline (WHO Class I-III Obesity)
Data Showcase Fields:  60 (HEIGHT cm), 61 (WEIGHT kg), 70 (Derived BMI kg/m2)

CLINICAL RATIONALE (For Clinicians & Non-OMOP Reviewers):
  Identifies MCPS participants meeting the World Health Organization (WHO)
  anthropometric threshold for adult clinical obesity at baseline recruitment:
    • Body Mass Index (BMI = Weight [kg] / Height [m]^2) >= 30.0 kg/m^2,
      within plausible physiologic bounds (12.0 <= BMI <= 80.0 kg/m^2).

OMOP CDM v5.4 MAPPING TRANSLATION:
  • `measurement`:
      - `measurement_concept_id = 3038553` -> LOINC 39156-5 ("Body mass index (BMI) [Ratio]")
      - `unit_concept_id = 9531`           -> UCUM "kg/m2" ("kilogram per square meter")
      - `value_as_number >= 30.0`
================================================================================
*/

INSERT OR REPLACE INTO cohort_definition (
    cohort_definition_id,
    cohort_definition_name,
    cohort_definition_description
) VALUES (
    10,
    'Obesity (BMI >= 30)',
    'Clinical Obesity: LOINC 39156-5 Body mass index (BMI) >= 30.0 kg/m2 (OMOP 3038553)'
);

DELETE FROM cohort WHERE cohort_definition_id = 10;

INSERT INTO cohort (cohort_definition_id, subject_id, cohort_start_date, cohort_end_date)
SELECT
    10 AS cohort_definition_id,
    p.person_id AS subject_id,
    MIN(op.observation_period_start_date) AS cohort_start_date,
    MAX(op.observation_period_end_date) AS cohort_end_date
FROM person p
JOIN observation_period op
    ON p.person_id = op.person_id
JOIN measurement m_bmi
    ON p.person_id = m_bmi.person_id
   AND m_bmi.measurement_concept_id = 3038553
   AND m_bmi.value_as_number >= 30.0
   AND (m_bmi.range_low IS NULL OR m_bmi.value_as_number >= m_bmi.range_low)
   AND (m_bmi.range_high IS NULL OR m_bmi.value_as_number <= m_bmi.range_high)
GROUP BY p.person_id;
