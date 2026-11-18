-- OMOP Common Data Model v5.4 DDL (Core Clinical, Vocabulary & MCPS Genomic ID Bridge Tables)
-- Compatible with PostgreSQL 16 and SQLite 3

CREATE TABLE IF NOT EXISTS vocabulary (
    vocabulary_id         VARCHAR(20)  PRIMARY KEY,
    vocabulary_name       VARCHAR(255) NOT NULL,
    vocabulary_reference  VARCHAR(255),
    vocabulary_version    VARCHAR(255),
    vocabulary_concept_id INTEGER      NOT NULL
);

CREATE TABLE IF NOT EXISTS concept (
    concept_id       INTEGER      PRIMARY KEY,
    concept_name     VARCHAR(255) NOT NULL,
    domain_id        VARCHAR(20)  NOT NULL,
    vocabulary_id    VARCHAR(20)  NOT NULL,
    concept_class_id VARCHAR(20)  NOT NULL,
    standard_concept VARCHAR(1),
    concept_code     VARCHAR(50)  NOT NULL,
    valid_start_date DATE         NOT NULL,
    valid_end_date   DATE         NOT NULL,
    invalid_reason   VARCHAR(1)
);

CREATE TABLE IF NOT EXISTS concept_relationship (
    concept_id_1     INTEGER     NOT NULL,
    concept_id_2     INTEGER     NOT NULL,
    relationship_id  VARCHAR(20) NOT NULL,
    valid_start_date DATE        NOT NULL,
    valid_end_date   DATE        NOT NULL,
    invalid_reason   VARCHAR(1),
    PRIMARY KEY (concept_id_1, concept_id_2, relationship_id)
);

CREATE TABLE IF NOT EXISTS source_to_concept_map (
    source_code             VARCHAR(50)  NOT NULL,
    source_concept_id       INTEGER      NOT NULL,
    source_vocabulary_id    VARCHAR(20)  NOT NULL,
    source_code_description VARCHAR(255),
    target_concept_id       INTEGER      NOT NULL,
    target_vocabulary_id    VARCHAR(20)  NOT NULL,
    valid_start_date        DATE         NOT NULL,
    valid_end_date          DATE         NOT NULL,
    invalid_reason          VARCHAR(1),
    PRIMARY KEY (source_vocabulary_id, source_code, target_concept_id)
);

CREATE TABLE IF NOT EXISTS location (
    location_id           INTEGER     PRIMARY KEY,
    address_1             VARCHAR(50),
    address_2             VARCHAR(50),
    city                  VARCHAR(50),
    state                 VARCHAR(2),
    zip                   VARCHAR(9),
    county                VARCHAR(20),
    location_source_value VARCHAR(50),
    country_concept_id    INTEGER,
    country_source_value  VARCHAR(80),
    latitude              NUMERIC,
    longitude             NUMERIC
);

CREATE TABLE IF NOT EXISTS person (
    person_id                   INTEGER     PRIMARY KEY,
    gender_concept_id           INTEGER     NOT NULL,
    year_of_birth               INTEGER     NOT NULL,
    month_of_birth              INTEGER,
    day_of_birth                INTEGER,
    birth_datetime              TIMESTAMP,
    race_concept_id             INTEGER     NOT NULL,
    ethnicity_concept_id        INTEGER     NOT NULL,
    location_id                 INTEGER     REFERENCES location(location_id),
    provider_id                 INTEGER,
    care_site_id                INTEGER,
    person_source_value         VARCHAR(100),
    gender_source_value         VARCHAR(50),
    gender_source_concept_id    INTEGER,
    race_source_value           VARCHAR(50),
    race_source_concept_id      INTEGER,
    ethnicity_source_value      VARCHAR(50),
    ethnicity_source_concept_id INTEGER
);

-- MCPS Phenotype (PATID) <-> Regeneron Genotype (IID/FID) Bridge Table
CREATE TABLE IF NOT EXISTS genomic_id_map (
    person_id    INTEGER      PRIMARY KEY REFERENCES person(person_id),
    patid        VARCHAR(50)  UNIQUE,
    genotype_iid VARCHAR(100) UNIQUE,
    genotype_fid VARCHAR(100),
    rgc_id       VARCHAR(30),
    mexb_id      VARCHAR(30),
    is_genotyped INTEGER      NOT NULL DEFAULT 0,
    pc1          NUMERIC,
    pc2          NUMERIC,
    pc3          NUMERIC,
    pc4          NUMERIC,
    pc5          NUMERIC,
    pc6          NUMERIC,
    pc7          NUMERIC
);

CREATE TABLE IF NOT EXISTS observation_period (
    observation_period_id          INTEGER PRIMARY KEY,
    person_id                      INTEGER NOT NULL REFERENCES person(person_id),
    observation_period_start_date  DATE    NOT NULL,
    observation_period_end_date    DATE    NOT NULL,
    period_type_concept_id         INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS visit_occurrence (
    visit_occurrence_id           INTEGER     PRIMARY KEY,
    person_id                     INTEGER     NOT NULL REFERENCES person(person_id),
    visit_concept_id              INTEGER     NOT NULL,
    visit_start_date              DATE        NOT NULL,
    visit_start_datetime          TIMESTAMP,
    visit_end_date                DATE        NOT NULL,
    visit_end_datetime            TIMESTAMP,
    visit_type_concept_id         INTEGER     NOT NULL,
    provider_id                   INTEGER,
    care_site_id                  INTEGER,
    visit_source_value            VARCHAR(50),
    visit_source_concept_id       INTEGER,
    admitted_from_concept_id      INTEGER,
    admitted_from_source_value    VARCHAR(50),
    discharged_to_concept_id      INTEGER,
    discharged_to_source_value    VARCHAR(50),
    preceding_visit_occurrence_id INTEGER
);

CREATE TABLE IF NOT EXISTS condition_occurrence (
    condition_occurrence_id       INTEGER     PRIMARY KEY,
    person_id                     INTEGER     NOT NULL REFERENCES person(person_id),
    condition_concept_id          INTEGER     NOT NULL,
    condition_start_date          DATE        NOT NULL,
    condition_start_datetime      TIMESTAMP,
    condition_end_date            DATE,
    condition_end_datetime        TIMESTAMP,
    condition_type_concept_id     INTEGER     NOT NULL,
    condition_status_concept_id   INTEGER,
    stop_reason                   VARCHAR(20),
    provider_id                   INTEGER,
    visit_occurrence_id           INTEGER     REFERENCES visit_occurrence(visit_occurrence_id),
    visit_detail_id               INTEGER,
    condition_source_value        VARCHAR(50),
    condition_source_concept_id   INTEGER,
    condition_status_source_value VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS measurement (
    measurement_id                INTEGER     PRIMARY KEY,
    person_id                     INTEGER     NOT NULL REFERENCES person(person_id),
    measurement_concept_id        INTEGER     NOT NULL,
    measurement_date              DATE        NOT NULL,
    measurement_datetime          TIMESTAMP,
    measurement_time              VARCHAR(10),
    measurement_type_concept_id   INTEGER     NOT NULL,
    operator_concept_id           INTEGER,
    value_as_number               NUMERIC,
    value_as_concept_id           INTEGER,
    unit_concept_id               INTEGER,
    range_low                     NUMERIC,
    range_high                    NUMERIC,
    provider_id                   INTEGER,
    visit_occurrence_id           INTEGER     REFERENCES visit_occurrence(visit_occurrence_id),
    visit_detail_id               INTEGER,
    measurement_source_value      VARCHAR(50),
    measurement_source_concept_id INTEGER,
    unit_source_value             VARCHAR(50),
    unit_source_concept_id        INTEGER,
    value_source_value            VARCHAR(50),
    measurement_event_id          INTEGER,
    meas_event_field_concept_id   INTEGER
);

CREATE TABLE IF NOT EXISTS observation (
    observation_id                INTEGER      PRIMARY KEY,
    person_id                     INTEGER      NOT NULL REFERENCES person(person_id),
    observation_concept_id        INTEGER      NOT NULL,
    observation_date              DATE         NOT NULL,
    observation_datetime          TIMESTAMP,
    observation_type_concept_id   INTEGER      NOT NULL,
    value_as_number               NUMERIC,
    value_as_string               VARCHAR(255),
    value_as_concept_id           INTEGER,
    qualifier_concept_id          INTEGER,
    unit_concept_id               INTEGER,
    provider_id                   INTEGER,
    visit_occurrence_id           INTEGER      REFERENCES visit_occurrence(visit_occurrence_id),
    visit_detail_id               INTEGER,
    observation_source_value      VARCHAR(50),
    observation_source_concept_id INTEGER,
    unit_source_value             VARCHAR(50),
    qualifier_source_value        VARCHAR(50),
    value_source_value            VARCHAR(50),
    observation_event_id          INTEGER,
    obs_event_field_concept_id    INTEGER
);

CREATE TABLE IF NOT EXISTS drug_exposure (
    drug_exposure_id             INTEGER     PRIMARY KEY,
    person_id                    INTEGER     NOT NULL REFERENCES person(person_id),
    drug_concept_id              INTEGER     NOT NULL,
    drug_exposure_start_date     DATE        NOT NULL,
    drug_exposure_start_datetime TIMESTAMP,
    drug_exposure_end_date       DATE        NOT NULL,
    drug_exposure_end_datetime   TIMESTAMP,
    verbatim_end_date            DATE,
    drug_type_concept_id         INTEGER     NOT NULL,
    stop_reason                  VARCHAR(20),
    refills                      INTEGER,
    quantity                     NUMERIC,
    days_supply                  INTEGER,
    sig                          TEXT,
    route_concept_id             INTEGER,
    lot_number                   VARCHAR(50),
    provider_id                  INTEGER,
    visit_occurrence_id          INTEGER     REFERENCES visit_occurrence(visit_occurrence_id),
    visit_detail_id              INTEGER,
    drug_source_value            VARCHAR(100),
    drug_source_concept_id       INTEGER,
    route_source_value           VARCHAR(50),
    dose_unit_source_value       VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS death (
    person_id               INTEGER PRIMARY KEY REFERENCES person(person_id),
    death_date              DATE    NOT NULL,
    death_datetime          TIMESTAMP,
    death_type_concept_id   INTEGER,
    cause_concept_id        INTEGER,
    cause_source_value      VARCHAR(50),
    cause_source_concept_id INTEGER
);

CREATE TABLE IF NOT EXISTS cohort (
    cohort_definition_id INTEGER NOT NULL,
    subject_id           INTEGER NOT NULL REFERENCES person(person_id),
    cohort_start_date    DATE    NOT NULL,
    cohort_end_date      DATE    NOT NULL,
    PRIMARY KEY (cohort_definition_id, subject_id, cohort_start_date)
);
