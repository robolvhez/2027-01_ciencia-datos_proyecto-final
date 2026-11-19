# MCPS -> OMOP CDM v5.4 Project Rules

## 1. Data Governance & DNAnexus Constraints
- **Zero Protected Data in Git:** Never stage or commit raw MCPS files, symlinks (`data`), PLINK files (`.bim`, `.fam`, `.bed`, `.keep`), or populated SQLite databases (`*.db`). Only non-sensitive vocabulary mapping tables under `configs/*.csv` may be tracked.
- **Self-Contained on DNAnexus:** MCPS data cannot live on an external server outside DNAnexus. Keep the core ETL runnable with Python's standard library (`csv`, `sqlite3`, `difflib`) and portable file databases (`sqlite:///...`) so it executes cleanly inside headless DNAnexus workers without a GUI (no interactive `Usagi`) or external daemon dependencies.

## 2. Strict ETL Scope Boundaries
- **Database Build Only:** The ETL pipeline (`src/python/mcps_etl/`) is strictly responsible for building and populating the OMOP CDM v5.4 database.
- **Raw Data Only as ETL Input:** Ingest only raw MCPS variables (`MCPS BASELINE.csv`); treat `MCPS_GWAS_Phenotype_Catalogue.csv` strictly as the downstream target specification replicated by SQL cohort queries.
- **No Synthetic Data Generators:** Do not add synthetic data generation modules; use small in-memory row fixtures in `tests/` for unit tests and run smoke tests against real files outputting to `/tmp/`.
- **Leave `.keep` Subcohort Filtering Downstream:** Do not ingest PLINK `.keep` subcohort lists (`FGWAS` vs `PopGWAS`) into the OMOP ETL; subcohort subsetting is a downstream analysis step.
- **In-Memory `pytest` for Every New Function:** Every new computing or transforming function in `src/python/mcps_etl/` must have an in-memory `pytest` unit test in `tests/`.

## 3. MCPS Domain & OMOP Mapping Conventions
- **Strict `PATID` <-> `RegID` Linkage (`140,831` Genotyped Check):** Never compute or synthesize `RegID` (`genotype_iid`) from `PATID`. Assign `genotype_iid` strictly from explicit `--id-bridge` / `--fam` mappings, reject duplicate `PATID` or `RegID` values, mark unmapped `PATID`s as `is_genotyped = 0`, validate against `EXPECTED_GENOTYPED_INDIVIDUALS = 140_831`, and emit standard OMOP `observation` `45769413` (SNOMED `708060009` *Genotype determination*). Always prioritize `genotype_iid` in `person.person_source_value`.
- **Authoritative Athena Verification (No Circular Checks):** In `configs/source_to_concept_map.csv`, record both native `target_concept_code` (`SNOMED`, `LOINC`, `RxNorm`, `ATC`) and `target_concept_id`, and verify against the downloaded Athena `CONCEPT.csv` (`~/data/omop/CONCEPT.csv`) via `./mcps-omop-etl verify-concepts` (`standard_concept = 'S'`, or `'C'`/`'S'` for `ATC` drug classes). Keep `02_seed_concepts.sql` synced to those verified Athena rows.
- **Traceable Medication Text Thresholding (`min_count >= 250`):** Only curate verified pharmaceutical/brand names from `MEDICATION1..3` passing `MIN_MEDICATION_MENTION_COUNT = 250` (audited via `./mcps-omop-etl profile-medications`) into `configs/source_to_concept_map.csv`.
- **Baseline Diagnosis Decade (`BASE_*_DX`):** Impute `condition_start_date` as the first day of the reported decade (`1` -> `1950-01-01` .. `6` -> `2000-01-01`), falling back to the recruitment date (`YYYY-MM-01`) when `*_DX` is null.
- **Single-Code, Clinician-Documented SQL Cohorts:** Maintain one SQL file per GWAS Catalogue phenotype code in `src/sql/cohorts/`, with a clinician-friendly header docstring and inline comments translating every OMOP table and `concept_id` into plain clinical criteria.

## 4. CLI Ergonomics
- Maintain `# PYTHON_ARGCOMPLETE_OK` and `argcomplete.autocomplete(parser)` on `./mcps-omop-etl` and `src/python/mcps_etl/__main__.py`, with short flags (`-i`, `-d`, `-n`) and sensible defaults (`-d sqlite:////tmp/mcps_omop.db`).