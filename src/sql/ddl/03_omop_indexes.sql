-- Performance indexes for OMOP CDM v5.4 clinical & cohort tables (SQLite / PostgreSQL)
-- Prevents full-table scans during cohort queries filtering on *_concept_id and joining on person_id.

CREATE INDEX IF NOT EXISTS idx_cond_concept_person ON condition_occurrence (condition_concept_id, person_id);
CREATE INDEX IF NOT EXISTS idx_cond_person ON condition_occurrence (person_id);

CREATE INDEX IF NOT EXISTS idx_meas_concept_person ON measurement (measurement_concept_id, person_id);
CREATE INDEX IF NOT EXISTS idx_meas_person ON measurement (person_id);

CREATE INDEX IF NOT EXISTS idx_obs_concept_person ON observation (observation_concept_id, person_id);
CREATE INDEX IF NOT EXISTS idx_obs_person ON observation (person_id);

CREATE INDEX IF NOT EXISTS idx_drug_concept_person ON drug_exposure (drug_concept_id, person_id);
CREATE INDEX IF NOT EXISTS idx_drug_person ON drug_exposure (person_id);

CREATE INDEX IF NOT EXISTS idx_visit_person ON visit_occurrence (person_id);
CREATE INDEX IF NOT EXISTS idx_obs_period_person ON observation_period (person_id);
CREATE INDEX IF NOT EXISTS idx_genomic_is_genotyped ON genomic_id_map (is_genotyped, person_id);
CREATE INDEX IF NOT EXISTS idx_cohort_subject ON cohort (subject_id);
