/*
================================================================================
MCPS GWAS PHENOTYPE CATALOGUE COHORT DEFINITION
================================================================================
Catalogue Code:        09_04_01
Cohort Definition ID:  7
Clinical Phenotype:    Self-Reported Regular Lipid-Lowering Medication Use
                       (DRUG_LIPIDS: Lipid-lowering medication vs. not)
Data Showcase Field:   49 (Clinician-coded DRUG_E1..DRUG_E5)
Oxford Benchmark N:    887 participants in full MCPS Baseline (N = 159,517)

CLINICAL RATIONALE (For Clinicians & Non-OMOP Reviewers):
  Identifies MCPS participants taking at least one lipid-regulating medication
  regularly for more than a month at baseline recruitment:
    • DRUG_E1: Statins (HMG CoA reductase inhibitors)
    • DRUG_E2: Fibrates (e.g., Bezafibrate)
    • DRUG_E3: Bile acid sequestrant resins
    • DRUG_E4: Niacin (Nicotinic acid)
    • DRUG_E5: Other lipid regulators

OMOP CDM v5.4 MAPPING TRANSLATION:
  • `drug_exposure.drug_concept_id`:
      - 21601855 -> ATC C10AA   ("HMG CoA reductase inhibitors" / DRUG_E1)
      - 21601864 -> ATC C10AB   ("Fibrates" / DRUG_E2)
      - 21601875 -> ATC C10AC   ("Bile acid sequestrants" / DRUG_E3)
      - 1517824  -> RxNorm 7393 ("niacin" / DRUG_E4)
      - 21601888 -> ATC C10AX   ("Other lipid modifying agents" / DRUG_E5)
      - 19022956 -> RxNorm 1525 ("bezafibrate")
================================================================================
*/

INSERT OR REPLACE INTO cohort_definition (
    cohort_definition_id,
    cohort_definition_name,
    cohort_definition_description
) VALUES (
    7,
    'Lipid-Lowering Medication (09_04_01)',
    'Lipid-lowering medication vs not (09_04_01 / DRUG_LIPIDS): Regular use (>1 month) of statins (DRUG_E1), fibrates (DRUG_E2), resins (DRUG_E3), niacin (DRUG_E4), or other lipid regulators (DRUG_E5)'
);

DELETE FROM cohort WHERE cohort_definition_id = 7;

INSERT INTO cohort (cohort_definition_id, subject_id, cohort_start_date, cohort_end_date)
SELECT
    7 AS cohort_definition_id,
    de.person_id AS subject_id,
    MIN(de.drug_exposure_start_date) AS cohort_start_date,
    MAX(de.drug_exposure_end_date) AS cohort_end_date
FROM drug_exposure de
WHERE de.drug_source_value IN ('DRUG_E1', 'DRUG_E2', 'DRUG_E3', 'DRUG_E4', 'DRUG_E5')
   OR de.drug_concept_id IN (21601855, 21601864, 21601875, 1517824, 21601888, 19022956)
GROUP BY de.person_id;
