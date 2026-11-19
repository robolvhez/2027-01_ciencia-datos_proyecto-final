/*
================================================================================
MCPS GWAS PHENOTYPE CATALOGUE COHORT DEFINITION
================================================================================
Catalogue Code:        09_02_01
Cohort Definition ID:  5
Clinical Phenotype:    Self-Reported Regular Antihypertensive Medication Use
                       (DRUG_ANTIHYPERTENSIVE: Antihypertensive medication vs. not)
Data Showcase Field:   49 (Clinician-coded DRUG_A1..DRUG_A11)
Oxford Benchmark N:    25,801 participants in full MCPS Baseline (N = 159,517)

CLINICAL RATIONALE (For Clinicians & Non-OMOP Reviewers):
  Identifies MCPS participants taking at least one blood-pressure-lowering
  (antihypertensive) medication regularly for more than a month at baseline,
  spanning 11 pharmacological classes:
    • DRUG_A1:  Alpha-blockers
    • DRUG_A2:  ACE inhibitors (e.g., Captopril, Enalapril)
    • DRUG_A3:  Angiotensin-II receptor blockers (ARBs)
    • DRUG_A4:  Other venodilators
    • DRUG_A5:  Beta-blockers (e.g., Metoprolol, Propranolol)
    • DRUG_A6:  Calcium channel blockers (e.g., Nifedipine, Amlodipine, Verapamil)
    • DRUG_A7:  Centrally acting antihypertensives
    • DRUG_A8:  Other diuretics
    • DRUG_A9:  Thiazide diuretics (e.g., Chlorthalidone)
    • DRUG_A10: Loop diuretics (e.g., Furosemide)
    • DRUG_A11: Potassium-sparing diuretics

OMOP CDM v5.4 MAPPING TRANSLATION:
  • `drug_exposure.drug_concept_id`:
      - ATC Classes: 21600410 (C02CA), 21601784 (C09AA), 21601823 (C09CA),
        21600424 (C02D), 21601665 (C07A), 21601744 (C08), 21600382 (C02A),
        21601556 (C03X), 21601462 (C03A), 21601517 (C03CA), 21601532 (C03D)
================================================================================
*/

INSERT OR REPLACE INTO cohort_definition (
    cohort_definition_id,
    cohort_definition_name,
    cohort_definition_description
) VALUES (
    5,
    'Antihypertensive Medication (09_02_01)',
    'Antihypertensive medication vs not (09_02_01 / DRUG_ANTIHYPERTENSIVE): Regular use (>1 month) of any antihypertensive class (DRUG_A1..DRUG_A11)'
);

DELETE FROM cohort WHERE cohort_definition_id = 5;

INSERT INTO cohort (cohort_definition_id, subject_id, cohort_start_date, cohort_end_date)
SELECT
    5 AS cohort_definition_id,
    de.person_id AS subject_id,
    MIN(de.drug_exposure_start_date) AS cohort_start_date,
    MAX(de.drug_exposure_end_date) AS cohort_end_date
FROM drug_exposure de
WHERE de.drug_source_value IN (
    'DRUG_A1', 'DRUG_A2', 'DRUG_A3', 'DRUG_A4', 'DRUG_A5', 'DRUG_A6',
    'DRUG_A7', 'DRUG_A8', 'DRUG_A9', 'DRUG_A10', 'DRUG_A11'
)
   OR de.drug_concept_id IN (
       21600410, 21601784, 21601823, 21600424, 21601665,
       21601744, 21600382, 21601556, 21601462, 21601517, 21601532
   )
GROUP BY de.person_id;
