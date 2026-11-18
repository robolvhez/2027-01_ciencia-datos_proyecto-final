"""MCPS Baseline Data Dictionary (v1.1 - April 2025 update) catalogs and lookup tables."""

from __future__ import annotations

# Decade of diagnosis (BASE_*_DX): start of decade date imputation
DECADE_DX_TO_DATE: dict[int, str] = {
    1: "1950-01-01",
    2: "1960-01-01",
    3: "1970-01-01",
    4: "1980-01-01",
    5: "1990-01-01",
    6: "2000-01-01",
}

# Field 5: Marital status
MARITAL_STATUS_LABELS: dict[int, str] = {
    1: "Single",
    2: "Divorced",
    3: "Living together",
    4: "Separated",
    5: "Married",
    6: "Widowed",
}

# Field 6: Highest educational level attained (April 2025 updated labels)
EDUGP_LABELS: dict[int, str] = {
    1: "Illiterate",
    2: "Knows how to read",
    3: "Knows how to read and write",
    4: "Incomplete elementary (ages 6 to 12 years)",
    5: "Complete elementary (ages 6 to 12 years)",
    6: "Technical studies with complete elementary (ages 6 to 12 years)",
    7: "Incomplete middle school (ages 13 to 15 years)",
    8: "Complete middle school (ages 13 to 15 years)",
    9: "Technical studies with complete middle school level (ages 13 to 15 years)",
    10: "High school (ages 16 to 18 years)",
    11: "Technical studies with complete high school level (ages 16 to 18 years)",
    12: "Incomplete university (ages >18 years)",
    13: "Complete university (ages >18 years)",
    14: "Post graduate degree (ages >18 years)",
}

# Field 7: Occupation at baseline
OCCUPATION_LABELS: dict[int, str] = {
    1: "Professional",
    2: "Labourer (e.g. factory worker) or Craftsman/Artisan",
    3: "Mason/bricklayer (albaniles)",
    4: "Technical worker (e.g. mechanic, equipment maintenance)",
    5: "Helper or similar (e.g. community nurse)",
    6: "Transport vehicle operator/driver",
    7: "Teacher or employed in the Education sector",
    8: "Public sector worker",
    9: "Student",
    10: "Employed in the Arts industries",
    11: "Private sector worker",
    12: "Housework",
    13: "Businessman/manager (in a position of authority)",
    14: "Labour (blue collar)",
    15: "Retired",
    16: "Merchant/shopkeeper",
    17: "Domestic worker",
    18: "Landlord",
    19: "Pedlar/street vendor",
    20: "Policeman/security guard",
    21: "Unemployed",
}

# Field 9: Health service provider
HEALTH_PROVIDER_LABELS: dict[int, str] = {
    1: "SSA",
    2: "IMSS",
    3: "ISSSTE",
    4: "SEDENA",
    5: "SECMAR",
    6: "PEMEX",
    7: "INI",
    8: "Private physician",
    9: "Dispensario medico",
    10: "Other service",
}

# Field 13: Frequency of current smoking
FREQ_SMOK_LABELS: dict[int, str] = {
    1: "daily",
    2: "weekly",
    3: "monthly",
    4: "occasionally",
}

# Field 22: Alcohol consumption frequency in previous 12 months
FREQ_ALC_LABELS: dict[int, str] = {
    1: "daily",
    2: "3-4 times weekly",
    3: "1-2 times weekly",
    4: "2-3 times monthly",
    5: "~once monthly",
    6: "6-11 times yearly",
    7: "1-5 times yearly",
    8: "not in last year but has before",
    9: "never has",
}

# Field 23: Drinks per single occasion
QUANT_ALC_LABELS: dict[int, str] = {
    1: "1 to 2",
    2: "3 to 4",
    3: "5 to 7",
    4: "8 to 11",
    5: "12 or more",
}

# Field 24: Most frequently consumed alcoholic beverage
TYPE_ALC_LABELS: dict[int, str] = {
    1: "beer",
    2: "wine",
    3: "brandy/whiskey/tequila/rum",
    4: "pulque",
    5: "cooler",
    6: "pure alcohol",
    7: "other",
}

# Field 26: Exercise frequency per week
FREQ_PHYS_LABELS: dict[int, str] = {
    1: "<weekly",
    2: "1-2 times weekly",
    3: "3+ times weekly",
}

# Field 27: Exercise duration per session
DUR_PHYS_LABELS: dict[int, str] = {
    1: "<30 minutes",
    2: "30-60 minutes",
    3: "more than 60 minutes",
}

CATEGORY_CATALOGS: dict[str, dict[int, str]] = {
    "MARITAL_STATUS": MARITAL_STATUS_LABELS,
    "EDUGP": EDUGP_LABELS,
    "OCCUPATION": OCCUPATION_LABELS,
    "HEALTH_PROVIDER": HEALTH_PROVIDER_LABELS,
    "FREQ_SMOK": FREQ_SMOK_LABELS,
    "FREQ_ALC": FREQ_ALC_LABELS,
    "QUANT_ALC": QUANT_ALC_LABELS,
    "TYPE_ALC": TYPE_ALC_LABELS,
    "FREQ_PHYS": FREQ_PHYS_LABELS,
    "DUR_PHYS": DUR_PHYS_LABELS,
}

# Stage 1 Cardiometabolic Baseline Condition Variables -> Diagnosis Decade Column
STAGE1_CONDITIONS: dict[str, str] = {
    "BASE_DIABETES": "BASE_DIABETES_DX",
    "BASE_HYPERTENSION": "BASE_HYPERTENSION_DX",
    "BASE_HEARTATTACK": "BASE_HEARTATTACK_DX",
    "BASE_ANGINA": "BASE_ANGINA_DX",
    "BASE_STROKE": "BASE_STROKE_DX",
    "BASE_CKD": "BASE_CKD_DX",
    "BASE_PAD": "BASE_PAD_DX",
    "BASE_CIRR": "BASE_CIRR_DX",
}

# Stage 1 Raw Quantitative Measurement Columns
STAGE1_RAW_MEASUREMENTS: tuple[str, ...] = (
    "HEIGHT",
    "WEIGHT",
    "WAISTC",
    "HIPC",
    "SBP1",
    "SBP2",
    "SBP3",
    "DBP1",
    "DBP2",
    "DBP3",
    "BASE_HBA1C",
    "BASE_HBA1C_DCCT",
    "BASE_HBA1C_IFCC",
)

# Stage 1 Core Covariate Observation Columns
STAGE1_OBSERVATIONS: tuple[str, ...] = (
    "MARITAL_STATUS",
    "EDUGP",
    "OCCUPATION",
    "INCOME",
    "HEALTH_PROVIDER",
    "EVER_SMOK",
    "AGE_STARTED_SMOKING",
    "CURR_SMOK",
    "FREQ_SMOK",
    "CIGS_PER_DAY",
    "QUIT_SMOK",
    "FREQ_ALC",
    "QUANT_ALC",
    "TYPE_ALC",
    "EVER_PHYS",
    "FREQ_PHYS",
    "DUR_PHYS",
    "BLOOD",
    "FASTING_DURATION",
)
