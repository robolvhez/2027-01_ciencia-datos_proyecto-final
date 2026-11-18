-- Cohort Definition 1: Type 2 Diabetes (MCPS Phenotype 17_03_01 / 17_01_01)
-- Standard Concepts:
--   Condition: SNOMED 73211009 (OMOP 201820: Diabetes mellitus) or 44054006 (OMOP 201826: Type 2 diabetes mellitus)
--   Measurement: LOINC 4548-4 (OMOP 3004410: HbA1c >= 6.5%) or 59261-8 (OMOP 40762352: HbA1c >= 48 mmol/mol)

DELETE FROM cohort WHERE cohort_definition_id = 1;

INSERT INTO cohort (cohort_definition_id, subject_id, cohort_start_date, cohort_end_date)
SELECT
    1 AS cohort_definition_id,
    p.person_id AS subject_id,
    MIN(op.observation_period_start_date) AS cohort_start_date,
    MAX(op.observation_period_end_date) AS cohort_end_date
FROM person p
JOIN observation_period op ON p.person_id = op.person_id
LEFT JOIN condition_occurrence co
    ON p.person_id = co.person_id
   AND co.condition_concept_id IN (201820, 201826)
LEFT JOIN measurement m_dcct
    ON p.person_id = m_dcct.person_id
   AND m_dcct.measurement_concept_id = 3004410
   AND m_dcct.value_as_number >= 6.5
   AND (m_dcct.range_low IS NULL OR m_dcct.value_as_number >= m_dcct.range_low)
   AND (m_dcct.range_high IS NULL OR m_dcct.value_as_number <= m_dcct.range_high)
LEFT JOIN measurement m_ifcc
    ON p.person_id = m_ifcc.person_id
   AND m_ifcc.measurement_concept_id = 40762352
   AND m_ifcc.value_as_number >= 48.0
   AND (m_ifcc.range_low IS NULL OR m_ifcc.value_as_number >= m_ifcc.range_low)
   AND (m_ifcc.range_high IS NULL OR m_ifcc.value_as_number <= m_ifcc.range_high)
WHERE co.condition_occurrence_id IS NOT NULL
   OR m_dcct.measurement_id IS NOT NULL
   OR m_ifcc.measurement_id IS NOT NULL
GROUP BY p.person_id;

-- Analysis View keyed by Regeneron Genotype ID (FID, IID)
SELECT
    g.genotype_fid AS FID,
    COALESCE(g.genotype_iid, g.patid) AS IID,
    g.patid AS PATID,
    g.is_genotyped AS IS_GENOTYPED,
    (CAST(SUBSTR(op.observation_period_start_date, 1, 4) AS INTEGER) - p.year_of_birth) AS AGE,
    CASE WHEN p.gender_concept_id = 8507 THEN 1 ELSE 0 END AS MALE,
    CASE WHEN c.subject_id IS NOT NULL THEN 1 ELSE 0 END AS T2D_CASE,
    g.pc1, g.pc2, g.pc3, g.pc4, g.pc5, g.pc6, g.pc7
FROM person p
JOIN genomic_id_map g ON p.person_id = g.person_id
JOIN observation_period op ON p.person_id = op.person_id
LEFT JOIN cohort c
    ON p.person_id = c.subject_id
   AND c.cohort_definition_id = 1;
