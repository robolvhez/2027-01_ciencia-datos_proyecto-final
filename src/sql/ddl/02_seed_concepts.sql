-- Seed Standard OMOP Concepts (SNOMED CT, LOINC, UCUM, Gender, Ethnicity, Visit, Type)
-- Verified against OHDSI Athena standard concept definitions

INSERT INTO vocabulary (vocabulary_id, vocabulary_name, vocabulary_reference, vocabulary_version, vocabulary_concept_id) VALUES
('SNOMED', 'Systematic Nomenclature of Medicine - Clinical Terms', 'http://www.snomed.org/', '2025-01', 44819097),
('LOINC', 'Logical Observation Identifiers Names and Codes', 'https://loinc.org/', '2.78', 44819102),
('UCUM', 'Unified Code for Units of Measure', 'https://ucum.org/', '2.1', 44819107),
('Gender', 'OMOP Gender', 'OHDSI', 'v5.4', 44819109),
('Ethnicity', 'OMOP Ethnicity', 'OHDSI', 'v5.4', 44819137),
('Visit', 'OMOP Visit', 'OHDSI', 'v5.4', 44819117),
('Type Concept', 'OMOP Type Concept', 'OHDSI', 'v5.4', 32808),
('MCPS_BASELINE', 'Mexico City Prospective Study Baseline Data Dictionary v1.1 (April 2025)', 'https://datashare.ndph.ox.ac.uk', 'v1.1-202504', 2000000001),
('MCPS_GWAS_CATALOG', 'Mexico City Prospective Study GWAS Phenotype Catalogue', 'https://datashare.ndph.ox.ac.uk', 'v1.0', 2000000002)
ON CONFLICT (vocabulary_id) DO NOTHING;

INSERT INTO concept (concept_id, concept_name, domain_id, vocabulary_id, concept_class_id, standard_concept, concept_code, valid_start_date, valid_end_date, invalid_reason) VALUES
-- Gender & Ethnicity
(8507, 'MALE', 'Gender', 'Gender', 'Gender', 'S', 'M', '1970-01-01', '2099-12-31', NULL),
(8532, 'FEMALE', 'Gender', 'Gender', 'Gender', 'S', 'F', '1970-01-01', '2099-12-31', NULL),
(38003563, 'Hispanic or Latino', 'Ethnicity', 'Ethnicity', 'Ethnicity', 'S', 'Hispanic', '1970-01-01', '2099-12-31', NULL),
-- Visit & Provenance Type Concepts
(9202, 'Outpatient Visit', 'Visit', 'Visit', 'Visit', 'S', 'OP', '1970-01-01', '2099-12-31', NULL),
(32880, 'Standardized health system data', 'Type Concept', 'Type Concept', 'Type Concept', 'S', 'OMOP4976931', '1970-01-01', '2099-12-31', NULL),
(32865, 'Patient self-report', 'Type Concept', 'Type Concept', 'Type Concept', 'S', 'OMOP4976916', '1970-01-01', '2099-12-31', NULL),
(32817, 'EHR / Derived study measurement', 'Type Concept', 'Type Concept', 'Type Concept', 'S', 'OMOP4976890', '1970-01-01', '2099-12-31', NULL),
-- UCUM Units
(8582, 'centimeter', 'Unit', 'UCUM', 'Unit', 'S', 'cm', '1970-01-01', '2099-12-31', NULL),
(9529, 'kilogram', 'Unit', 'UCUM', 'Unit', 'S', 'kg', '1970-01-01', '2099-12-31', NULL),
(9531, 'kilogram per square meter', 'Unit', 'UCUM', 'Unit', 'S', 'kg/m2', '1970-01-01', '2099-12-31', NULL),
(8523, 'ratio', 'Unit', 'UCUM', 'Unit', 'S', '{ratio}', '1970-01-01', '2099-12-31', NULL),
(8876, 'millimeter mercury column', 'Unit', 'UCUM', 'Unit', 'S', 'mm[Hg]', '1970-01-01', '2099-12-31', NULL),
(8554, 'percent', 'Unit', 'UCUM', 'Unit', 'S', '%', '1970-01-01', '2099-12-31', NULL),
(9579, 'millimole per mole', 'Unit', 'UCUM', 'Unit', 'S', 'mmol/mol', '1970-01-01', '2099-12-31', NULL),
(8505, 'hour', 'Unit', 'UCUM', 'Unit', 'S', 'h', '1970-01-01', '2099-12-31', NULL),
(8753, 'millimole per liter', 'Unit', 'UCUM', 'Unit', 'S', 'mmol/L', '1970-01-01', '2099-12-31', NULL),
(8713, 'gram per liter', 'Unit', 'UCUM', 'Unit', 'S', 'g/L', '1970-01-01', '2099-12-31', NULL),
(8749, 'micromole per liter', 'Unit', 'UCUM', 'Unit', 'S', 'umol/L', '1970-01-01', '2099-12-31', NULL),
-- LOINC Standard Measurements
(3036277, 'Body height', 'Measurement', 'LOINC', 'Clinical Observation', 'S', '8302-2', '1970-01-01', '2099-12-31', NULL),
(3025315, 'Body weight', 'Measurement', 'LOINC', 'Clinical Observation', 'S', '29463-7', '1970-01-01', '2099-12-31', NULL),
(3038553, 'Body mass index (BMI) [Ratio]', 'Measurement', 'LOINC', 'Clinical Observation', 'S', '39156-5', '1970-01-01', '2099-12-31', NULL),
(40759207, 'Waist circumference', 'Measurement', 'LOINC', 'Clinical Observation', 'S', '8280-0', '1970-01-01', '2099-12-31', NULL),
(40765363, 'Hip circumference', 'Measurement', 'LOINC', 'Clinical Observation', 'S', '8281-8', '1970-01-01', '2099-12-31', NULL),
(40765364, 'Waist-to-hip ratio', 'Measurement', 'LOINC', 'Clinical Observation', 'S', '8282-6', '1970-01-01', '2099-12-31', NULL),
(3004249, 'Systolic blood pressure', 'Measurement', 'LOINC', 'Clinical Observation', 'S', '8480-6', '1970-01-01', '2099-12-31', NULL),
(3012888, 'Diastolic blood pressure', 'Measurement', 'LOINC', 'Clinical Observation', 'S', '8462-4', '1970-01-01', '2099-12-31', NULL),
(3004410, 'Hemoglobin A1c/Hemoglobin.total in Blood', 'Measurement', 'LOINC', 'Lab Test', 'S', '4548-4', '1970-01-01', '2099-12-31', NULL),
(40762352, 'Hemoglobin A1c/Hemoglobin.total in Blood by IFCC protocol', 'Measurement', 'LOINC', 'Lab Test', 'S', '59261-8', '1970-01-01', '2099-12-31', NULL),
(3028437, 'Cholesterol in LDL [Moles/volume] in Serum or Plasma', 'Measurement', 'LOINC', 'Lab Test', 'S', '13457-7', '1970-01-01', '2099-12-31', NULL),
(3007070, 'Cholesterol in HDL [Moles/volume] in Serum or Plasma', 'Measurement', 'LOINC', 'Lab Test', 'S', '14646-4', '1970-01-01', '2099-12-31', NULL),
(3033745, 'Apolipoprotein B [Mass/volume] in Serum or Plasma', 'Measurement', 'LOINC', 'Lab Test', 'S', '1884-6', '1970-01-01', '2099-12-31', NULL),
(3033688, 'Apolipoprotein A1 [Mass/volume] in Serum or Plasma', 'Measurement', 'LOINC', 'Lab Test', 'S', '1869-7', '1970-01-01', '2099-12-31', NULL),
(3016723, 'Creatinine [Moles/volume] in Serum or Plasma', 'Measurement', 'LOINC', 'Lab Test', 'S', '14682-9', '1970-01-01', '2099-12-31', NULL),
(3022192, 'Triglyceride [Moles/volume] in Serum or Plasma', 'Measurement', 'LOINC', 'Lab Test', 'S', '14927-8', '1970-01-01', '2099-12-31', NULL),
-- SNOMED CT Standard Conditions (Cardiometabolic Core)
(201820, 'Diabetes mellitus', 'Condition', 'SNOMED', 'Clinical Finding', 'S', '73211009', '1970-01-01', '2099-12-31', NULL),
(201826, 'Type 2 diabetes mellitus', 'Condition', 'SNOMED', 'Clinical Finding', 'S', '44054006', '1970-01-01', '2099-12-31', NULL),
(316866, 'Hypertensive disorder', 'Condition', 'SNOMED', 'Clinical Finding', 'S', '38341003', '1970-01-01', '2099-12-31', NULL),
(4329847, 'Myocardial infarction', 'Condition', 'SNOMED', 'Clinical Finding', 'S', '22298006', '1970-01-01', '2099-12-31', NULL),
(315286, 'Angina pectoris', 'Condition', 'SNOMED', 'Clinical Finding', 'S', '194828000', '1970-01-01', '2099-12-31', NULL),
(443454, 'Cerebrovascular accident', 'Condition', 'SNOMED', 'Clinical Finding', 'S', '230690007', '1970-01-01', '2099-12-31', NULL),
(46271022, 'Chronic kidney disease', 'Condition', 'SNOMED', 'Clinical Finding', 'S', '709044004', '1970-01-01', '2099-12-31', NULL),
(321052, 'Peripheral vascular disease', 'Condition', 'SNOMED', 'Clinical Finding', 'S', '400047006', '1970-01-01', '2099-12-31', NULL),
(4064161, 'Cirrhosis of liver', 'Condition', 'SNOMED', 'Clinical Finding', 'S', '19943007', '1970-01-01', '2099-12-31', NULL),
-- SNOMED / LOINC Standard Observations (Covariates)
(4053609, 'Marital status', 'Observation', 'SNOMED', 'Observable Entity', 'S', '125680007', '1970-01-01', '2099-12-31', NULL),
(42528763, 'Highest level of education', 'Observation', 'LOINC', 'Survey', 'S', '82589-3', '1970-01-01', '2099-12-31', NULL),
(4033543, 'Occupation', 'Observation', 'SNOMED', 'Observable Entity', 'S', '14679004', '1970-01-01', '2099-12-31', NULL),
(4076249, 'Income', 'Observation', 'SNOMED', 'Observable Entity', 'S', '224164007', '1970-01-01', '2099-12-31', NULL),
(4135376, 'Health care provider', 'Observation', 'SNOMED', 'Social Context', 'S', '308335008', '1970-01-01', '2099-12-31', NULL),
(4005823, 'Tobacco smoking behavior - finding', 'Observation', 'SNOMED', 'Clinical Finding', 'S', '365980008', '1970-01-01', '2099-12-31', NULL),
(4218917, 'Age at starting smoking', 'Observation', 'SNOMED', 'Observable Entity', 'S', '228494002', '1970-01-01', '2099-12-31', NULL),
(4298794, 'Smoker', 'Observation', 'SNOMED', 'Clinical Finding', 'S', '77176002', '1970-01-01', '2099-12-31', NULL),
(40766929, 'Cigarettes smoked per day', 'Observation', 'LOINC', 'Survey', 'S', '64218-1', '1970-01-01', '2099-12-31', NULL),
(4310250, 'Ex-smoker', 'Observation', 'SNOMED', 'Clinical Finding', 'S', '8517006', '1970-01-01', '2099-12-31', NULL),
(4038710, 'Alcohol intake', 'Observation', 'SNOMED', 'Observable Entity', 'S', '160573003', '1970-01-01', '2099-12-31', NULL),
(40766322, 'Drinks per occasion', 'Observation', 'LOINC', 'Survey', 'S', '64004-5', '1970-01-01', '2099-12-31', NULL),
(4215984, 'Type of alcohol consumed', 'Observation', 'SNOMED', 'Observable Entity', 'S', '228273003', '1970-01-01', '2099-12-31', NULL),
(4028922, 'Physical activity', 'Observation', 'SNOMED', 'Observable Entity', 'S', '109006', '1970-01-01', '2099-12-31', NULL),
(40765040, 'Exercise frequency per week', 'Observation', 'LOINC', 'Survey', 'S', '63986-4', '1970-01-01', '2099-12-31', NULL),
(40765041, 'Exercise duration per session', 'Observation', 'LOINC', 'Survey', 'S', '63987-2', '1970-01-01', '2099-12-31', NULL),
(4001225, 'Blood specimen', 'Observation', 'SNOMED', 'Specimen', 'S', '119297000', '1970-01-01', '2099-12-31', NULL),
(3022940, 'Fasting duration', 'Observation', 'LOINC', 'Clinical Observation', 'S', '49541-6', '1970-01-01', '2099-12-31', NULL)
ON CONFLICT (concept_id) DO NOTHING;
