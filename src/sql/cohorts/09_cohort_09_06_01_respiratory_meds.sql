/*
================================================================================
MCPS GWAS PHENOTYPE CATALOGUE COHORT DEFINITION
================================================================================
Catalogue Code:        09_06_01
Cohort Definition ID:  9
Clinical Phenotype:    Self-Reported Regular Respiratory Medication Use
                       (DRUG_RESPIRATORY: Respiratory medication vs. not)
Data Showcase Field:   49 (Clinician-coded DRUG_H1..DRUG_H3)
Oxford Benchmark N:    3,103 participants in full MCPS Baseline (N = 159,517)

CLINICAL RATIONALE (For Clinicians & Non-OMOP Reviewers):
  Identifies MCPS participants taking respiratory medications for asthma or COPD
  regularly for more than a month at baseline recruitment:
    • DRUG_H1: Inhaled bronchodilators (e.g., Salbutamol / Albuterol)
    • DRUG_H2: Inhaled corticosteroids
    • DRUG_H3: Other systemic or inhaled respiratory medications

OMOP CDM v5.4 MAPPING TRANSLATION:
  • `drug_exposure.drug_concept_id`:
      - 21603249 -> ATC R03A   ("ADRENERGICS, INHALANTS" / DRUG_H1)
      - 21603283 -> ATC R03BA  ("Glucocorticoids" / DRUG_H2)
      - 21603358 -> ATC R03DX  ("Other systemic drugs for obstructive airway diseases" / DRUG_H3)
      - 1154343  -> RxNorm 435 ("albuterol" / Salbutamol)
================================================================================
*/

INSERT OR REPLACE INTO cohort_definition (
    cohort_definition_id,
    cohort_definition_name,
    cohort_definition_description
) VALUES (
    9,
    'Respiratory Medication (09_06_01)',
    'Respiratory medication vs not (09_06_01 / DRUG_RESPIRATORY): Regular use (>1 month) of inhaled bronchodilators (DRUG_H1), inhaled corticosteroids (DRUG_H2), or other respiratory drugs (DRUG_H3)'
);

DELETE FROM cohort WHERE cohort_definition_id = 9;

INSERT INTO cohort (cohort_definition_id, subject_id, cohort_start_date, cohort_end_date)
SELECT
    9 AS cohort_definition_id,
    de.person_id AS subject_id,
    MIN(de.drug_exposure_start_date) AS cohort_start_date,
    MAX(de.drug_exposure_end_date) AS cohort_end_date
FROM drug_exposure de
WHERE de.drug_source_value IN ('DRUG_H1', 'DRUG_H2', 'DRUG_H3')
   OR de.drug_concept_id IN (21603249, 21603283, 21603358, 1154343)
GROUP BY de.person_id;
