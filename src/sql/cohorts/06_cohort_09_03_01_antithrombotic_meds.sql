/*
================================================================================
MCPS GWAS PHENOTYPE CATALOGUE COHORT DEFINITION
================================================================================
Catalogue Code:        09_03_01
Cohort Definition ID:  6
Clinical Phenotype:    Self-Reported Regular Antithrombotic Medication Use
                       (DRUG_ANTITHROMBOTIC: Antithrombotic medication vs. not)
Data Showcase Field:   49 (Clinician-coded DRUG_C1..DRUG_C4)
Oxford Benchmark N:    4,898 participants in full MCPS Baseline (N = 159,517)

CLINICAL RATIONALE (For Clinicians & Non-OMOP Reviewers):
  Identifies MCPS participants taking at least one antithrombotic (anticoagulant
  or antiplatelet) medication regularly for more than a month at baseline:
    • DRUG_C1: Oral anticoagulants (Vitamin K antagonists)
    • DRUG_C2: Other antithrombotic agents
    • DRUG_C3: Aspirin (Acetylsalicylic acid)
    • DRUG_C4: Other antiplatelet agents

OMOP CDM v5.4 MAPPING TRANSLATION:
  • `drug_exposure.drug_concept_id`:
      - 21600962 -> ATC B01AA   ("Vitamin K antagonists" / DRUG_C1)
      - 21601027 -> ATC B01AX   ("Other antithrombotic agents" / DRUG_C2)
      - 1112807  -> RxNorm 1191 ("aspirin" / DRUG_C3)
      - 21600985 -> ATC B01AC   ("Platelet aggregation inhibitors excl. heparin" / DRUG_C4)
================================================================================
*/

INSERT OR REPLACE INTO cohort_definition (
    cohort_definition_id,
    cohort_definition_name,
    cohort_definition_description
) VALUES (
    6,
    'Antithrombotic Medication (09_03_01)',
    'Antithrombotic medication vs not (09_03_01 / DRUG_ANTITHROMBOTIC): Regular use (>1 month) of oral anticoagulants (DRUG_C1), other antithrombotics (DRUG_C2), aspirin (DRUG_C3), or other antiplatelets (DRUG_C4)'
);

DELETE FROM cohort WHERE cohort_definition_id = 6;

INSERT INTO cohort (cohort_definition_id, subject_id, cohort_start_date, cohort_end_date)
SELECT
    6 AS cohort_definition_id,
    de.person_id AS subject_id,
    MIN(de.drug_exposure_start_date) AS cohort_start_date,
    MAX(de.drug_exposure_end_date) AS cohort_end_date
FROM drug_exposure de
WHERE de.drug_source_value IN ('DRUG_C1', 'DRUG_C2', 'DRUG_C3', 'DRUG_C4')
   OR de.drug_concept_id IN (21600962, 21601027, 1112807, 21600985)
GROUP BY de.person_id;
