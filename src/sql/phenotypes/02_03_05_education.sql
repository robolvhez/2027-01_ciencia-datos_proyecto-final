/*
================================================================================
MCPS GWAS PHENOTYPE DEFINITION
================================================================================
Catalogue Code:      02_03_05
Clinical Phenotype:  Highest Educational Level Attained (EDUGP 1-14)
Variable Type:       categorical
Units:               None
Description:         Ordered categorical educational attainment level (1=Illiterate .. 14=Post graduate)

OMOP CDM v5.4 MAPPING TRANSLATION:
  • `observation`:
      - `observation_concept_id = 42528763` -> LOINC 82589-3 ("Highest level of education")
      - `value_as_number` stores MCPS Field 6 code (1..14)
================================================================================
*/

SELECT
    p.person_id,
    MAX(o.value_as_number) AS phenotype_value
FROM person p
LEFT JOIN observation o
    ON p.person_id = o.person_id
   AND o.observation_concept_id = 42528763
GROUP BY p.person_id
ORDER BY p.person_id;
