/*
================================================================================
MCPS GWAS PHENOTYPE CATALOGUE COHORT DEFINITION
================================================================================
Catalogue Code:        09_01_01
Cohort Definition ID:  4
Clinical Phenotype:    Self-Reported Regular Antidiabetic Medication Use
                       (DRUG_ANTIDIABETIC: Antidiabetic medication vs. not)
Data Showcase Field:   49 (Clinician-coded DRUG_D1..DRUG_D4)
Oxford Benchmark N:    17,665 participants in full MCPS Baseline (N = 159,517)

CLINICAL RATIONALE (For Clinicians & Non-OMOP Reviewers):
  Identifies MCPS participants taking at least one antidiabetic medication
  regularly for more than a month at baseline recruitment, across four classes:
    • DRUG_D1: Biguanides (Metformin)
    • DRUG_D2: Sulphonylureas (Glibenclamide/Glyburide, Tolbutamide, Chlorpropamide)
    • DRUG_D3: Insulin
    • DRUG_D4: Other antidiabetic medications

OMOP CDM v5.4 MAPPING TRANSLATION:
  • `drug_exposure.drug_concept_id`:
      - 1503297  -> RxNorm 6809   ("metformin" / DRUG_D1)
      - 21600749 -> ATC A10BB     ("Sulfonylureas" / DRUG_D2)
      - 1596977  -> RxNorm 253182 ("insulin, regular, human" / DRUG_D3)
      - 21600788 -> ATC A10BX     ("Other blood glucose lowering drugs, excl. insulins" / DRUG_D4)
      - 1559684  -> RxNorm 4815   ("glyburide")
      - 1502855  -> RxNorm 10635  ("tolbutamide")
      - 1594973  -> RxNorm 2404   ("chlorpropamide")
================================================================================
*/

INSERT OR REPLACE INTO cohort_definition (
    cohort_definition_id,
    cohort_definition_name,
    cohort_definition_description
) VALUES (
    4,
    'Antidiabetic Medication (09_01_01)',
    'Antidiabetic medication vs not (09_01_01 / DRUG_ANTIDIABETIC): Regular use (>1 month) of biguanides (DRUG_D1), sulphonylureas (DRUG_D2), insulin (DRUG_D3), or other antidiabetics (DRUG_D4)'
);

DELETE FROM cohort WHERE cohort_definition_id = 4;

INSERT INTO cohort (cohort_definition_id, subject_id, cohort_start_date, cohort_end_date)
SELECT
    4 AS cohort_definition_id,
    de.person_id AS subject_id,
    MIN(de.drug_exposure_start_date) AS cohort_start_date,
    MAX(de.drug_exposure_end_date) AS cohort_end_date
FROM drug_exposure de
WHERE de.drug_source_value IN ('DRUG_D1', 'DRUG_D2', 'DRUG_D3', 'DRUG_D4')
   OR de.drug_concept_id IN (1503297, 21600749, 1596977, 21600788, 1559684, 1502855, 1594973)
GROUP BY de.person_id;
