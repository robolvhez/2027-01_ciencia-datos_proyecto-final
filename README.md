# ETL Pipeline for MCPS Metabolic and Anthropometric Phenotypes into OMOP CDM

## Final Project Proposal — Ciencia de Datos Aplicada en Biomedicina y en la Industria Farmacéutica/de la Salud: De la Academia a la Industria (2027-1)

**Author:** Roberto Olvera Hernández, B.Sc.  
**Affiliation:** Programa de Doctorado en Ciencias Biomédicas (PDCB), Universidad Nacional Autónoma de México (UNAM) — Centro de Ciencias Genómicas (CCG)  
**Track:** C — Cloud Data Pipeline  
**Date:** November 2026 (Updated: Pivot from DGIS/ENSANUT to MCPS on DNAnexus)

---

### Research Question

Can a reproducible, headless cloud ETL pipeline running on **DNAnexus** standardize metabolic and anthropometric phenotypes (BMI, HbA1c, blood pressure, type 2 diabetes, height) from the **Mexico City Prospective Study (MCPS)** directly into the **OMOP CDM v5.4** (using SNOMED and LOINC standard concepts) to enable cross-cohort family-based GWAS meta-analyses?

### Motivation

Mexico faces a cardiometabolic crisis: in 2022, ischemic heart disease, type 2 diabetes (T2D), and hypertension accounted for 41.4% of all registered deaths. Genomic cohorts such as the Mexico City Prospective Study (MCPS, ~140,000 genotyped individuals) and the Mexican Biobank (MXB, ~6,000 with WGS) offer an unprecedented opportunity to dissect the genetic architecture of these diseases in a recently admixed population (66% Indigenous, 31% European, 3% African). However, standard genome-wide association studies (PopGWAS) in recently admixed populations are particularly vulnerable to residual confounding from population stratification, indirect genetic effects, and assortative mating, yielding biased effect size estimates.

Family-based GWAS (FGWAS) address this problem by estimating direct genetic effects (DGEs) using exclusively within-family Mendelian variation. Their main limitation, however, is statistical power. The most direct solution is cross-cohort meta-analysis, which increases sample size without relaxing the design assumptions. For a meta-analysis to be valid, phenotype definitions must be comparable across studies — and currently, neither MCPS nor MXB standardize their phenotypes in an interoperable data model, hindering comparison both between them and with international cohorts (e.g., UK Biobank, China Kadoorie Biobank, gnomAD, GWAS Atlas).

This project builds an ETL pipeline that connects **MCPS clinical, anthropometric, laboratory, and mortality data** directly to the **OMOP CDM v5.4** schema using **SNOMED CT** and **LOINC** standard vocabularies, and defines clinical cohorts via SQL inside a secure **DNAnexus** cloud environment.

---

### Scope Adjustment & Architectural Pivot (DGIS / ENSANUT → MCPS)

> [!IMPORTANT]
> **Documented Project Pivot (November 2026):** The project originally proposed building a proxy ETL using open Mexican administrative or survey datasets (**DGIS** *Egresos Hospitalarios* or **ENSANUT**) before transferring the architecture to MCPS. After initial exploration on the `dev` branch, the project scope was restructured to work **directly on MCPS**.

#### Why pivot away from DGIS and ENSANUT?
1. **Excessive breadth and scope mismatch:** National open datasets such as **DGIS** (hospital discharges across thousands of CIE-10 and CIE-9-MC codes in 4 relational tables) or **ENSANUT** (multi-wave national health and nutrition surveys with changing questionnaire schemas across years) are massive, general-purpose administrative/survey databases. Harmonizing them properly into OMOP CDM requires a dedicated, large-scale institutional effort far beyond a single course project.
2. **Unfamiliar domain overhead vs. direct cohort familiarity:** Investing weeks into reverse-engineering unfamiliar administrative coding quirks in DGIS detracts from the core scientific goal. Conversely, the author already has authorized access to and deep working familiarity with **MCPS**, which is the primary dataset of his doctoral thesis.
3. **Direct scientific impact ("Conectar MCPS a OMOP/SNOMED"):** If the actual objective is to connect MCPS phenotypes to OMOP CDM / SNOMED / LOINC so they can interoperate with UK Biobank and other cohorts for FGWAS meta-analyses, building the pipeline directly on MCPS achieves the goal immediately without maintaining a throwaway proxy ETL.

#### Protected Data & DNAnexus Execution Constraints
Working directly with MCPS introduces specific technical and governance constraints that shape the pipeline architecture:

- **Protected Individual-Level Data:** MCPS contains sensitive, individual-level clinical and genomic data governed by strict Data Access Agreements (DAA). **Zero individual-level data may be downloaded locally or committed to Git.**
- **Remote Execution on a DNAnexus Server:** All data inspection, vocabulary loading, ETL transformation, PostgreSQL / DuckDB / SQL execution, and cohort generation must take place strictly inside an authorized **DNAnexus** cloud server/workstation (headless Linux environment accessed via SSH, CLI, or JupyterLab).
- **Headless Vocabulary Mapping (No GUI for `Usagi`):** Because work is executed on a remote DNAnexus server without a desktop graphical environment (X11 / Java Swing), interactive OHDSI GUI tools such as **Usagi** and **WhiteRabbit** cannot be run directly on the server. Instead, this project implements a **headless concept mapping strategy**:
  1. **Direct Athena SQL/Python Crosswalks:** Mortality records and linked episodes in MCPS already coded in **ICD-10** are mapped programmatically to **SNOMED CT** via Athena's `CONCEPT` and `CONCEPT_RELATIONSHIP` (`relationship_id = 'Maps to'`) tables.
  2. **Curated Dictionary Mapping (`SOURCE_TO_CONCEPT_MAP`):** Core MCPS baseline variables (BMI, height, weight, waist/hip circumference, SBP, DBP, HbA1c, self-reported T2D, hypertension, medications, smoking/alcohol) come from a structured, well-defined cohort data dictionary and are mapped to standard **LOINC** (`Measurement`) and **SNOMED** (`Condition` / `Observation`) concepts via version-controlled CSV lookup tables.
  3. **Programmatic Text-Similarity CLI (`rapidfuzz` / SQL):** Where automated candidate generation is needed for unmapped dictionary variables on the headless DNAnexus node, a Python CLI script performs fuzzy/TF-IDF matching against Athena standard concepts—replicating Usagi's core matching logic without requiring a GUI. (Alternatively, because the blank MCPS variable dictionary contains only public column descriptions and zero participant data, Usagi can only ever be used locally on unpopulated metadata dictionaries, never on cohort data.)

---

### Data Sources

- **Mexico City Prospective Study (MCPS):** Cohort of ~140,000 adults aged 35+ recruited between 1998 and 2004 in Coyoacán and Iztapalapa (Mexico City), including baseline socioeconomic/clinical questionnaires, physical measurements, blood biochemistry (HbA1c, lipids, NMR metabolomics), and linked ICD-10 cause-specific mortality follow-up. Accessed exclusively within the secure **DNAnexus** platform.
  - Public metadata reference: [MCPS Data Showcase (Oxford / UNAM)](https://www.ctsu.ox.ac.uk/research/prospective-blood-based-study-of-150-000-individuals-in-mexico)
- **OMOP Vocabularies (Athena):** Standard concept definitions (**SNOMED CT**, **LOINC**, **RxNorm**) and **ICD-10 → SNOMED** crosswalks downloaded from [Athena (OHDSI)](https://athena.ohdsi.org/) and staged into the DNAnexus workspace.

---

### Expected Deliverables

A repository (code, SQL, mappings, and synthetic tests only — zero protected data) containing:

1. **Reproducible Database & Vocabulary Setup:** Containerized or server-ready PostgreSQL setup with the OMOP CDM v5.4 DDL and scripts to load Athena vocabularies (`SNOMED`, `LOINC`, `ICD10`, `RxNorm`) on a DNAnexus workstation.
2. **Headless Concept Mapping (`SOURCE_TO_CONCEPT_MAP`):** Versioned mapping tables and Python CLI utilities connecting MCPS baseline questionnaire/measurement variables and ICD-10 mortality codes to standard **SNOMED CT** and **LOINC** concepts without requiring the Usagi GUI.
3. **MCPS → OMOP ETL Package (`src/python/mcps_etl`):** Python pipeline transforming MCPS tabular datasets into core OMOP CDM v5.4 tables (`person`, `observation_period`, `measurement`, `condition_occurrence`, `death`, `observation`).
4. **SQL Cohort Definitions:** Validated SQL scripts defining at least two cardiometabolic phenotypes (e.g., Type 2 Diabetes combining baseline diagnosis, HbA1c $\ge 6.5\%$, or ICD-10 mortality; and Obesity via BMI $\ge 30\text{ kg/m}^2$), outputting an attrition table and phenotype matrix ready for FGWAS tools (`REGENIE` / `snipar`).
5. **Automated Quality & Integrity Report:** Scripts verifying primary/foreign key referential integrity, domain conformance, and standard concept mapping coverage.
6. **Synthetic Unit Tests & CI:** `pytest` suite running against synthetic mock data (mirroring MCPS column schemas with fake records) so CI (GitHub Actions) can validate the ETL without touching protected data.
7. **Complete Documentation:** Technical protocol (`docs/protocol.md`), headless mapping guide (`docs/usagi.md`), architectural pivot rationale, and limitations.

---

### Repository Structure

```text
2027-01_ciencia-datos_proyecto-final/
├── README.md
├── pyproject.toml
├── compose.yml
├── .gitignore
├── docker/
├── docs/
│   ├── img/
│   │   └── cdmDiagram.png
│   ├── protocol.md          # MCPS -> OMOP CDM v5.4 technical protocol & DNAnexus workflow
│   └── usagi.md             # OHDSI Usagi reference & headless CLI adaptation notes
├── log/
│   └── .gitkeep
├── src/
│   ├── python/
│   │   ├── mcps_etl/        # Core MCPS ETL package and headless concept mapper
│   │   │   ├── __init__.py
│   │   │   └── __main__.py
│   │   └── utils/
│   └── sql/                 # OMOP CDM DDL, vocabulary loaders, and cohort SQL queries
└── tests/                   # Synthetic unit tests (zero real patient data)
```

---

### Main Tools

| Tool | Purpose |
|---|---|
| **DNAnexus Platform (`dx-toolkit`)** | Secure cloud execution environment housing protected MCPS data |
| **Python (`pandas`, `sqlalchemy`, `psycopg`, `rapidfuzz`)** | ETL ingestion, transformation, and headless concept similarity matching |
| **PostgreSQL** | OMOP CDM v5.4 relational database instance |
| **Docker / Docker Compose** | Local testing with synthetic data and reproducible service definition |
| **Athena (OHDSI)** | Standard vocabularies (`SNOMED`, `LOINC`) and `ICD10` → `SNOMED` crosswalks |
| **`pytest` + `pandera` + GitHub Actions** | Schema validation and automated testing on synthetic fixtures |

---

### Anticipated Limitations

- **Cross-sectional baseline with mortality follow-up:** Unlike longitudinal hospital EHRs with continuous encounter histories, MCPS clinical measurements and questionnaires were primarily collected at baseline recruitment (1998–2004), with resurvey data in a subset (~10,000 participants) and longitudinal follow-up primarily through national mortality linkage (ICD-10 causes of death).
- **Headless server constraints on DNAnexus:** The absence of a graphical desktop interface on DNAnexus requires replacing interactive OHDSI GUI tools (Usagi, WhiteRabbit) with CLI scripts, SQL crosswalks, and CSV-based dictionary curation.
- **Targeted phenotype scope:** The initial ETL focuses on priority cardiometabolic and anthropometric phenotypes required for FGWAS (BMI, height, weight, waist/hip circumference, blood pressure, HbA1c, T2D, hypertension, and mortality) rather than all ~200+ questionnaire items at once.

---

### AI Assistant Usage Statement

This project uses AI assistants (Antigravity/Gemini, Claude) for documentation drafting, boilerplate code generation, and debugging. All design decisions, clinical definitions, and validations are the sole responsibility of the author.
