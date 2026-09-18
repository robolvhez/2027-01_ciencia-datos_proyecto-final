# ETL Pipeline for Metabolic and Anthropometric Phenotypes into OMOP CDM

## Final Project Proposal — Ciencia de Datos Aplicada en Biomedicina y en la Industria Farmacéutica/de la Salud: De la Academia a la Industria (2027-1)

**Author:** Roberto Olvera Hernández, B.Sc.  
**Affiliation:** Programa de Doctorado en Ciencias Biomédicas (PDCB), Universidad Nacional Autónoma de México (UNAM) — Centro de Ciencias Genómicas (CCG)  
**Track:** C — Cloud Data Pipeline  
**Date:** September 2026

---

### Research Question

Can a reproducible, containerized pipeline standardize metabolic and
anthropometric phenotypes (BMI, HbA1c, blood pressure, type 2 diabetes, height)
into the OMOP CDM from open Mexican clinical data, in a way that is directly
transferable to large-scale genomic cohorts such as MCPS?

### Motivation

Mexico faces a cardiometabolic crisis: in 2022, ischemic heart disease, type 2
diabetes (T2D), and hypertension accounted for 41.4% of all registered deaths.
Genomic cohorts such as the Mexico City Prospective Study (MCPS, ~140,000
genotyped individuals) and the Mexican Biobank (MXB, ~6,000 with WGS) offer an
unprecedented opportunity to dissect the genetic architecture of these diseases
in a recently admixed population (66% Indigenous, 31% European, 3% African).
However, standard genome-wide association studies (PopGWAS) in recently admixed
populations are particularly vulnerable to residual confounding from population
stratification, indirect genetic effects, and assortative mating, yielding
biased effect size estimates.

Family-based GWAS (FGWAS) address this problem by estimating direct genetic
effects (DGEs) using exclusively within-family Mendelian variation. Their main
limitation, however, is statistical power. The most direct solution is
cross-cohort meta-analysis, which increases sample size without relaxing the
design assumptions. For a meta-analysis to be valid, phenotype definitions must
be comparable across studies — and currently, neither MCPS nor MXB standardize
their phenotypes in an interoperable data model, hindering comparison both
between them and with international cohorts (e.g., UK Biobank, CK Biobank,
gnomAD, GWAS Atlas).

This project builds a prototype ETL pipeline that takes open Mexican clinical
data (DGIS hospital discharges), transforms it into the OMOP CDM v5.4 schema,
and defines clinical cohorts via SQL. Because DGIS data shares key structural
properties with MCPS — tabular CSVs, Mexican population, ICD-10 coded diagnoses,
and cardiometabolic phenotypes — the resulting pipeline is designed to be
directly transferable to MCPS and other Mexican cohorts.

### Data selection: Open Mexican clinical data (Course Route D)

My doctoral research uses the Mexico City Prospective Study (MCPS), a cohort of
~140,000 genotyped adults recruited between 1998 and 2004 in the Coyoacán and
Iztapalapa districts of Mexico City. MCPS phenotype data is stored as flat CSVs
with internal phenotype codes and demographic fields — a format that is not yet
standardized in any interoperable data model.

The DGIS hospital discharge database (Egresos Hospitalarios) provides an openly
available dataset delivered as flat CSVs with ICD-10 coded diagnoses. While MCPS
is a prospective cohort of adults aged 35+ from two districts of Mexico City,
DGIS captures inpatient episodes across the entire national public health
system — a different population with distinct sampling and ascertainment. This
difference is precisely what makes DGIS valuable: it enables future cross-level
comparisons between MCPS's localized urban cohort and national hospitalization
patterns for the same cardiometabolic conditions.

By building the ETL pipeline against DGIS data, the core infrastructure —
PostgreSQL with OMOP CDM, vocabulary loading, demographic harmonization, cohort
definition via SQL — is directly reusable for MCPS. The ICD-10 to SNOMED mapping
developed here also establishes the methodology for mapping MCPS's internal
phenotype codes to OMOP standard concepts in the future. Furthermore, the cloud
skills developed in this project (Docker, S3, infrastructure as code) are
directly aligned with my current PhD infrastructure: MCPS data is processed on
the DNAnexus platform (AWS/Azure), where containerized pipelines and cloud
storage are the standard workflow.

- [DGIS — Hospital discharges](http://www.dgis.salud.gob.mx/contenidos/basesdedatos/da_egresoshosp_gobmx.html)
  — open data from Mexico's Dirección General de Información en Salud. ICD-10
  coded diagnoses, demographics, and discharge outcomes.
- [OMOP Vocabularies (Athena)](https://athena.ohdsi.org/) — standard concept
  mapping (SNOMED, LOINC, RxNorm) and ICD-10 to SNOMED crosswalks.

No identifiable patient data enters the repository. DGIS records are
de-identified open data published by the Mexican federal government.

### Expected Deliverables

A repository containing:

1. **Docker Compose** stack running PostgreSQL with the OMOP CDM v5.4 schema and
   loaded vocabularies.
2. **ETL scripts** (Python) that transform DGIS hospital discharge CSVs and
   insert records into the corresponding OMOP tables, including ICD-10 to SNOMED
   concept mapping.
3. **Infrastructure as code** — `compose.yml` including an S3-compatible
   storage service (LocalStack or MinIO) for raw data and vocabularies, with
   documentation for EC2 deployment.
4. **SQL cohort definitions** for at least two clinical phenotypes (e.g., type 2
   diabetes and obesity), with a documented attrition table.
5. **Documented concept sets** for the phenotypes of interest, with explicit
   mapping from ICD-10 source codes to OMOP standard concepts.
6. **Automated quality report** verifying referential integrity and mapping
   coverage.
7. **Automated tests** with pytest and CI via GitHub Actions.
8. **Complete documentation:** protocol, data dictionary, limitations, and AI
   assistant usage statement.

### Repository Structure (Pre-project)

```
2027-01_ciencia-datos_proyecto-final/
├── README.md
├── .gitignore
├── docker/
│   └── synthea/
│       └── Dockerfile
├── docs/
│   └── protocol.md
├── log/
│   └── .gitkeep
├── src/
│   ├── python/
│   │   └── utils/
│   └── sql/
└── tests/
```

### Main Tools

| Tool | Purpose |
|---|---|
| Python (pandas, sqlalchemy, boto3) | Ingestion, transformation, S3 interaction |
| PostgreSQL | OMOP CDM database |
| Docker / Docker Compose | Environment reproducibility |
| LocalStack or MinIO | Local S3-compatible service for data and vocabularies |
| Athena (OHDSI) | Standard vocabularies and ICD-10 → SNOMED mapping |
| pytest + GitHub Actions | Testing and CI |

### Anticipated Limitations

- DGIS hospital discharge records capture only inpatient episodes; they do not
  include outpatient visits, laboratory measurements, or longitudinal follow-up,
  limiting the phenotype definitions that can be modeled in OMOP.
- The pipeline is designed for selected phenotypes, not for the ~200+ variables
  available in real genomic cohorts.
- ETL validation is limited to referential integrity and mapping coverage; it
  does not include external clinical validation.

### AI Assistant Usage Statement

This project uses AI assistants (Antigravity/Gemini, Claude) for documentation
drafting, boilerplate code generation, and debugging. All design decisions,
clinical definitions, and validations are the sole responsibility of the author.
