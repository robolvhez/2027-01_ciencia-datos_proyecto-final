/*
================================================================================
MCPS GWAS PHENOTYPE DEFINITION
================================================================================
Catalogue Code:      02_01_01
Clinical Phenotype:  District of Residence (Coyoacan vs Iztapalapa)
Variable Type:       binary
Units:               None
Description:         1 = Coyoacan (location_id = 1), 0 = Iztapalapa (location_id = 2), NULL = unknown

OMOP CDM v5.4 MAPPING TRANSLATION:
  • `person.location_id`:
      - 1 -> Coyoacan (COYOACAN = 1)
      - 2 -> Iztapalapa (COYOACAN = 0)
================================================================================
*/

SELECT
    p.person_id,
    CASE p.location_id
        WHEN 1 THEN 1
        WHEN 2 THEN 0
        ELSE NULL
    END AS phenotype_value
FROM person p
ORDER BY p.person_id;
