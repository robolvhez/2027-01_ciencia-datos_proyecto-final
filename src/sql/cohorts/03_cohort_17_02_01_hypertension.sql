/*
================================================================================
MCPS GWAS PHENOTYPE CATALOGUE COHORT DEFINITION
================================================================================
Catalogue Code:        17_02_01
Cohort Definition ID:  3
Clinical Phenotype:    Hypertension at Baseline
Data Showcase Fields:  40 (BASE_HYPERTENSION), 49 (DRUG_A1..A11 / MEDICATION1..3),
                       64 (SBP1..3), 65 (DBP1..3)

CLINICAL RATIONALE (For Clinicians & Non-OMOP Reviewers):
  Identifies all MCPS participants with hypertension at baseline recruitment using
  the Oxford MCPS GWAS Catalogue composite definition (`17_02_01`):
    1. Self-reported prior physician diagnosis of hypertension (BASE_HYPERTENSION = 1), OR
    2. Regular use (>1 month) of any antihypertensive medication class (DRUG_A1..A11)
       or mapped antihypertensive agent (ACE inhibitors, ARBs, Beta-blockers,
       Calcium channel blockers, Thiazide/Loop/Potassium-sparing diuretics,
       Alpha-blockers, Centrally acting agents, Venodilators), OR
    3. Elevated baseline seated blood pressure:
       - Mean Systolic Blood Pressure (SBP) >= 140.0 mmHg, OR
       - Mean Diastolic Blood Pressure (DBP) >= 90.0 mmHg.

OMOP CDM v5.4 MAPPING TRANSLATION:
  • `condition_occurrence`:
      - 316866 -> SNOMED CT 38341003 ("Hypertensive disorder")
  • `drug_exposure`:
      - ATC Antihypertensive Classes (DRUG_A1..A11):
        21600410 (C02CA Alpha-blockers), 21601784 (C09AA ACE inhibitors),
        21601823 (C09CA ARBs), 21600424 (C02D Venodilators),
        21601665 (C07A Beta-blockers), 21601744 (C08 Calcium channel blockers),
        21600382 (C02A Centrally acting), 21601556 (C03X Other diuretics),
        21601462 (C03A Thiazides), 21601517 (C03CA Loop diuretics),
        21601532 (C03D Potassium-sparing diuretics)
      - RxNorm Antihypertensive Ingredients (from MEDICATION1..3):
        1340128 (Captopril), 1341927 (Enalapril), 1318853 (Nifedipine),
        1332418 (Amlodipine), 1307046 (Metoprolol), 1353766 (Propranolol),
        1307863 (Verapamil), 1395058 (Chlorthalidone), 956874 (Furosemide)
  • `measurement`:
      - 3004249 -> LOINC 8480-6 ("Systolic blood pressure", mmHg >= 140.0)
      - 3012888 -> LOINC 8462-4 ("Diastolic blood pressure", mmHg >= 90.0)
================================================================================
*/

INSERT OR REPLACE INTO cohort_definition (
    cohort_definition_id,
    cohort_definition_name,
    cohort_definition_description
) VALUES (
    3,
    'Hypertension (17_02_01)',
    'Hypertension (17_02_01): Self-reported hypertension (SNOMED 316866) OR antihypertensive medication (DRUG_A1..A11 / RxNorm / ATC) OR SBP >= 140 mmHg (LOINC 3004249) OR DBP >= 90 mmHg (LOINC 3012888)'
);

DELETE FROM cohort WHERE cohort_definition_id = 3;

INSERT INTO cohort (cohort_definition_id, subject_id, cohort_start_date, cohort_end_date)
SELECT
    3 AS cohort_definition_id,
    p.person_id AS subject_id,
    MIN(op.observation_period_start_date) AS cohort_start_date,
    MAX(op.observation_period_end_date) AS cohort_end_date
FROM person p
JOIN observation_period op
    ON p.person_id = op.person_id
-- Criterion 1: Self-reported hypertension diagnosis in `condition_occurrence`
LEFT JOIN condition_occurrence co
    ON p.person_id = co.person_id
   AND co.condition_concept_id = 316866
-- Criterion 2: Regular use (>1 month) of antihypertensive medication in `drug_exposure`
LEFT JOIN drug_exposure de_htn
    ON p.person_id = de_htn.person_id
   AND de_htn.drug_concept_id IN (
       21600410, -- ATC C02CA: Alpha-blockers (DRUG_A1)
       21601784, -- ATC C09AA: ACE inhibitors, plain (DRUG_A2)
       21601823, -- ATC C09CA: Angiotensin II receptor blockers (ARBs) (DRUG_A3)
       21600424, -- ATC C02D:  Other venodilators (DRUG_A4)
       21601665, -- ATC C07A:  Beta blocking agents (DRUG_A5)
       21601744, -- ATC C08:   Calcium channel blockers (DRUG_A6)
       21600382, -- ATC C02A:  Centrally acting antiadrenergics (DRUG_A7)
       21601556, -- ATC C03X:  Other diuretics (DRUG_A8)
       21601462, -- ATC C03A:  Thiazide diuretics (DRUG_A9)
       21601517, -- ATC C03CA: Loop diuretics (DRUG_A10)
       21601532, -- ATC C03D:  Potassium-sparing diuretics (DRUG_A11)
       1340128,  -- RxNorm 1998:  Captopril
       1341927,  -- RxNorm 3827:  Enalapril
       1318853,  -- RxNorm 7417:  Nifedipine (Adalat)
       1332418,  -- RxNorm 17767: Amlodipine (Norvas)
       1307046,  -- RxNorm 6918:  Metoprolol
       1353766,  -- RxNorm 8787:  Propranolol
       1307863,  -- RxNorm 11170: Verapamil
       1395058,  -- RxNorm 2409:  Chlorthalidone
       956874    -- RxNorm 4603:  Furosemide
   )
-- Criterion 3a: Mean Systolic Blood Pressure >= 140.0 mmHg
LEFT JOIN measurement m_sbp
    ON p.person_id = m_sbp.person_id
   AND m_sbp.measurement_concept_id = 3004249
   AND m_sbp.measurement_source_value IN ('SBP_MEAN', '11_01_01', 'SBP1')
   AND m_sbp.value_as_number >= 140.0
   AND (m_sbp.range_low IS NULL OR m_sbp.value_as_number >= m_sbp.range_low)
   AND (m_sbp.range_high IS NULL OR m_sbp.value_as_number <= m_sbp.range_high)
-- Criterion 3b: Mean Diastolic Blood Pressure >= 90.0 mmHg
LEFT JOIN measurement m_dbp
    ON p.person_id = m_dbp.person_id
   AND m_dbp.measurement_concept_id = 3012888
   AND m_dbp.measurement_source_value IN ('DBP_MEAN', '11_02_01', 'DBP1')
   AND m_dbp.value_as_number >= 90.0
   AND (m_dbp.range_low IS NULL OR m_dbp.value_as_number >= m_dbp.range_low)
   AND (m_dbp.range_high IS NULL OR m_dbp.value_as_number <= m_dbp.range_high)
WHERE co.condition_occurrence_id IS NOT NULL
   OR de_htn.drug_exposure_id IS NOT NULL
   OR m_sbp.measurement_id IS NOT NULL
   OR m_dbp.measurement_id IS NOT NULL
GROUP BY p.person_id;
