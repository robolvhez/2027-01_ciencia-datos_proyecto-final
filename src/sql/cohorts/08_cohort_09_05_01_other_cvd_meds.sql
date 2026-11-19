/*
================================================================================
MCPS GWAS PHENOTYPE CATALOGUE COHORT DEFINITION
================================================================================
Catalogue Code:        09_05_01
Cohort Definition ID:  8
Clinical Phenotype:    Self-Reported Regular Other Cardiovascular Medication Use
                       (DRUG_OTHERCVD: Other CVD medication vs. not)
Data Showcase Field:   49 (Clinician-coded DRUG_B1..DRUG_B4)
Oxford Benchmark N:    3,138 participants in full MCPS Baseline (N = 159,517)

CLINICAL RATIONALE (For Clinicians & Non-OMOP Reviewers):
  Identifies MCPS participants taking other (non-antihypertensive) cardiovascular
  medications regularly for more than a month at baseline recruitment:
    • DRUG_B1: Anti-arrhythmic agents (Class I and III)
    • DRUG_B2: Digoxin (Cardiac glycoside)
    • DRUG_B3: Other unusual cardiovascular preparations
    • DRUG_B4: Organic nitrates (e.g., Isosorbide for angina)

OMOP CDM v5.4 MAPPING TRANSLATION:
  • `drug_exposure.drug_concept_id`:
      - 21600248 -> ATC C01B    ("ANTIARRHYTHMICS, CLASS I AND III" / DRUG_B1)
      - 1326303  -> RxNorm 3407 ("digoxin" / DRUG_B2)
      - 21600360 -> ATC C01E    ("OTHER CARDIAC PREPARATIONS" / DRUG_B3)
      - 21600316 -> ATC C01DA   ("Organic nitrates" / DRUG_B4)
      - 1383815  -> RxNorm 6057 ("isosorbide")
================================================================================
*/

INSERT OR REPLACE INTO cohort_definition (
    cohort_definition_id,
    cohort_definition_name,
    cohort_definition_description
) VALUES (
    8,
    'Other CVD Medication (09_05_01)',
    'Other CVD medication vs not (09_05_01 / DRUG_OTHERCVD): Regular use (>1 month) of anti-arrhythmics (DRUG_B1), digoxin (DRUG_B2), other unusual cardiovascular drugs (DRUG_B3), or nitrates (DRUG_B4)'
);

DELETE FROM cohort WHERE cohort_definition_id = 8;

INSERT INTO cohort (cohort_definition_id, subject_id, cohort_start_date, cohort_end_date)
SELECT
    8 AS cohort_definition_id,
    de.person_id AS subject_id,
    MIN(de.drug_exposure_start_date) AS cohort_start_date,
    MAX(de.drug_exposure_end_date) AS cohort_end_date
FROM drug_exposure de
WHERE de.drug_source_value IN ('DRUG_B1', 'DRUG_B2', 'DRUG_B3', 'DRUG_B4')
   OR de.drug_concept_id IN (21600248, 1326303, 21600360, 21600316, 1383815)
GROUP BY de.person_id;
