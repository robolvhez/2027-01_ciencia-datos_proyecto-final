"""Stage 1 transformations from MCPS Baseline & Genotyped records to OMOP CDM v5.4 rows."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .catalogs import (
    CATEGORY_CATALOGS,
    DECADE_DX_TO_DATE,
    STAGE1_CONDITIONS,
    STAGE1_OBSERVATIONS,
    STAGE1_RAW_MEASUREMENTS,
)
from .id_linkage import _clean_float, _clean_str
from .mapper import ConceptMapEntry, load_concept_map

GWAS_CATALOG_MEASUREMENTS: tuple[str, ...] = (
    "11_01_01",
    "11_02_01",
    "11_07_01",
    "11_11_01",
    "13_01_01",
    "15_01_01",
    "15_04_01",
    "15_04_02",
    "15_10_01",
    "15_16_18",
    "15_17_17",
)

GWAS_CATALOG_CONDITIONS: tuple[str, ...] = (
    "17_01_01",
    "17_02_01",
    "17_03_01",
)


def _clean_int(val: Any) -> int | None:
    f = _clean_float(val)
    return int(f) if f is not None else None


def visit_date_for_row(row: Mapping[str, Any]) -> str:
    """Return YYYY-MM-01 baseline recruitment date from YEAR_RECRUITED and MONTH_RECRUITED."""
    year = _clean_int(row.get("YEAR_RECRUITED")) or 2001
    month = _clean_int(row.get("MONTH_RECRUITED")) or 1
    month = max(1, min(12, month))
    return f"{year:04d}-{month:02d}-01"


def transform_locations() -> list[dict[str, Any]]:
    """Return the two MCPS recruitment districts (Coyoacan and Iztapalapa) as OMOP `location` rows."""
    return [
        {
            "location_id": 1,
            "address_1": None,
            "address_2": None,
            "city": "Ciudad de Mexico",
            "state": "CM",
            "zip": None,
            "county": "Coyoacan",
            "location_source_value": "COYOACAN=1",
            "country_concept_id": 4330442,
            "country_source_value": "MX",
            "latitude": 19.3467,
            "longitude": -99.1617,
        },
        {
            "location_id": 2,
            "address_1": None,
            "address_2": None,
            "city": "Ciudad de Mexico",
            "state": "CM",
            "zip": None,
            "county": "Iztapalapa",
            "location_source_value": "COYOACAN=0",
            "country_concept_id": 4330442,
            "country_source_value": "MX",
            "latitude": 19.3553,
            "longitude": -99.0622,
        },
    ]


def transform_persons(
    rows: Iterable[Mapping[str, Any]],
    genomic_id_map: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Transform MCPS participants into OMOP `person` rows, prioritizing genotype_iid as source value."""
    persons: list[dict[str, Any]] = []
    for row, gmap in zip(rows, genomic_id_map, strict=True):
        person_id = int(gmap["person_id"])
        year_rec = _clean_int(row.get("YEAR_RECRUITED")) or 2001
        age = _clean_int(row.get("AGE")) or 50
        male = _clean_int(row.get("MALE"))
        gender_concept_id = 8507 if male == 1 else (8532 if male == 0 else 0)

        coyoacan = _clean_int(row.get("COYOACAN"))
        if coyoacan is None:
            coyoacan = _clean_int(row.get("02_01_01"))
        location_id = 1 if coyoacan == 1 else (2 if coyoacan == 0 else None)

        source_val = gmap.get("genotype_iid") or gmap.get("patid")
        persons.append(
            {
                "person_id": person_id,
                "gender_concept_id": gender_concept_id,
                "year_of_birth": year_rec - age,
                "month_of_birth": None,
                "day_of_birth": None,
                "birth_datetime": None,
                "race_concept_id": 0,
                "ethnicity_concept_id": 38003563,
                "location_id": location_id,
                "provider_id": None,
                "care_site_id": None,
                "person_source_value": source_val,
                "gender_source_value": str(male) if male is not None else None,
                "gender_source_concept_id": 0,
                "race_source_value": "Mexican Admixed (MCPS)",
                "race_source_concept_id": 0,
                "ethnicity_source_value": "Hispanic or Latino",
                "ethnicity_source_concept_id": 0,
            }
        )
    return persons


def transform_visits_and_periods(
    rows: Iterable[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build `visit_occurrence` and `observation_period` anchored on baseline recruitment date."""
    visits: list[dict[str, Any]] = []
    periods: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        person_id = int(row.get("person_id") or idx)
        vdate = visit_date_for_row(row)
        visits.append(
            {
                "visit_occurrence_id": person_id,
                "person_id": person_id,
                "visit_concept_id": 9202,
                "visit_start_date": vdate,
                "visit_start_datetime": None,
                "visit_end_date": vdate,
                "visit_end_datetime": None,
                "visit_type_concept_id": 32880,
                "provider_id": None,
                "care_site_id": None,
                "visit_source_value": "MCPS_BASELINE",
                "visit_source_concept_id": 0,
                "admitted_from_concept_id": 0,
                "admitted_from_source_value": None,
                "discharged_to_concept_id": 0,
                "discharged_to_source_value": None,
                "preceding_visit_occurrence_id": None,
            }
        )
        periods.append(
            {
                "observation_period_id": person_id,
                "person_id": person_id,
                "observation_period_start_date": vdate,
                "observation_period_end_date": vdate,
                "period_type_concept_id": 32880,
            }
        )
    return visits, periods


def transform_measurements(
    rows: Iterable[Mapping[str, Any]],
    concept_map: dict[str, ConceptMapEntry] | None = None,
    start_id: int = 1,
) -> list[dict[str, Any]]:
    """Transform raw and derived Stage 1 cardiometabolic measurements into OMOP `measurement` rows."""
    cmap = concept_map or load_concept_map()
    measurements: list[dict[str, Any]] = []
    meas_id = start_id

    for idx, row in enumerate(rows, start=1):
        person_id = int(row.get("person_id") or idx)
        vdate = visit_date_for_row(row)
        blood_time = _clean_str(row.get("BLOOD_TIME"))

        values: list[tuple[str, float, int]] = []
        for col in STAGE1_RAW_MEASUREMENTS:
            val = _clean_float(row.get(col))
            if val is not None and col in cmap:
                values.append((col, val, 32865))

        height_cm = _clean_float(row.get("HEIGHT"))
        weight_kg = _clean_float(row.get("WEIGHT"))
        if height_cm and height_cm > 0 and weight_kg and "BMI" not in row and "11_11_01" not in row:
            bmi = round(weight_kg / ((height_cm / 100.0) ** 2), 4)
            values.append(("BMI", bmi, 32817))

        waist = _clean_float(row.get("WAISTC"))
        hip = _clean_float(row.get("HIPC"))
        if waist and hip and hip > 0 and "WHRATIO" not in row:
            values.append(("WHRATIO", round(waist / hip, 4), 32817))

        sbps = [v for v in (_clean_float(row.get(c)) for c in ("SBP1", "SBP2", "SBP3")) if v is not None]
        if sbps:
            values.append(("SBP_MEAN", round(sum(sbps) / len(sbps), 2), 32817))

        dbps = [v for v in (_clean_float(row.get(c)) for c in ("DBP1", "DBP2", "DBP3")) if v is not None]
        if dbps:
            values.append(("DBP_MEAN", round(sum(dbps) / len(dbps), 2), 32817))

        for cat_col in GWAS_CATALOG_MEASUREMENTS:
            val = _clean_float(row.get(cat_col))
            if val is not None and cat_col in cmap:
                values.append((cat_col, val, 32880))

        for col_name, num_val, mtype_id in values:
            entry = cmap[col_name]
            measurements.append(
                {
                    "measurement_id": meas_id,
                    "person_id": person_id,
                    "measurement_concept_id": entry.target_concept_id,
                    "measurement_date": vdate,
                    "measurement_datetime": None,
                    "measurement_time": blood_time if "HBA1C" in col_name else None,
                    "measurement_type_concept_id": mtype_id,
                    "operator_concept_id": None,
                    "value_as_number": num_val,
                    "value_as_concept_id": None,
                    "unit_concept_id": entry.unit_concept_id,
                    "range_low": entry.range_low,
                    "range_high": entry.range_high,
                    "provider_id": None,
                    "visit_occurrence_id": person_id,
                    "visit_detail_id": None,
                    "measurement_source_value": col_name,
                    "measurement_source_concept_id": 0,
                    "unit_source_value": entry.target_concept_code,
                    "unit_source_concept_id": 0,
                    "value_source_value": str(num_val),
                    "measurement_event_id": None,
                    "meas_event_field_concept_id": None,
                }
            )
            meas_id += 1

    return measurements


def transform_conditions(
    rows: Iterable[Mapping[str, Any]],
    concept_map: dict[str, ConceptMapEntry] | None = None,
    start_id: int = 1,
) -> list[dict[str, Any]]:
    """Transform Stage 1 cardiometabolic baseline conditions into OMOP `condition_occurrence` rows."""
    cmap = concept_map or load_concept_map()
    conditions: list[dict[str, Any]] = []
    cond_id = start_id

    for idx, row in enumerate(rows, start=1):
        person_id = int(row.get("person_id") or idx)
        vdate = visit_date_for_row(row)

        for cond_col, dx_col in STAGE1_CONDITIONS.items():
            if _clean_int(row.get(cond_col)) == 1 and cond_col in cmap:
                entry = cmap[cond_col]
                dx_code = _clean_int(row.get(dx_col))
                start_date = DECADE_DX_TO_DATE.get(dx_code, vdate) if dx_code is not None else vdate
                conditions.append(
                    {
                        "condition_occurrence_id": cond_id,
                        "person_id": person_id,
                        "condition_concept_id": entry.target_concept_id,
                        "condition_start_date": start_date,
                        "condition_start_datetime": None,
                        "condition_end_date": None,
                        "condition_end_datetime": None,
                        "condition_type_concept_id": 32865,
                        "condition_status_concept_id": 0,
                        "stop_reason": None,
                        "provider_id": None,
                        "visit_occurrence_id": person_id,
                        "visit_detail_id": None,
                        "condition_source_value": cond_col,
                        "condition_source_concept_id": 0,
                        "condition_status_source_value": None,
                    }
                )
                cond_id += 1

        for cat_col in GWAS_CATALOG_CONDITIONS:
            if _clean_int(row.get(cat_col)) == 1 and cat_col in cmap:
                entry = cmap[cat_col]
                conditions.append(
                    {
                        "condition_occurrence_id": cond_id,
                        "person_id": person_id,
                        "condition_concept_id": entry.target_concept_id,
                        "condition_start_date": vdate,
                        "condition_start_datetime": None,
                        "condition_end_date": None,
                        "condition_end_datetime": None,
                        "condition_type_concept_id": 32880,
                        "condition_status_concept_id": 0,
                        "stop_reason": None,
                        "provider_id": None,
                        "visit_occurrence_id": person_id,
                        "visit_detail_id": None,
                        "condition_source_value": cat_col,
                        "condition_source_concept_id": 0,
                        "condition_status_source_value": None,
                    }
                )
                cond_id += 1

    return conditions


def transform_observations(
    rows: Iterable[Mapping[str, Any]],
    concept_map: dict[str, ConceptMapEntry] | None = None,
    start_id: int = 1,
) -> list[dict[str, Any]]:
    """Transform Stage 1 socioeconomic and lifestyle covariates into OMOP `observation` rows."""
    cmap = concept_map or load_concept_map()
    observations: list[dict[str, Any]] = []
    obs_id = start_id

    for idx, row in enumerate(rows, start=1):
        person_id = int(row.get("person_id") or idx)
        vdate = visit_date_for_row(row)

        for obs_col in STAGE1_OBSERVATIONS:
            num_val = _clean_float(row.get(obs_col))
            if num_val is None or obs_col not in cmap:
                continue
            entry = cmap[obs_col]
            catalog = CATEGORY_CATALOGS.get(obs_col)
            str_val = catalog.get(int(num_val), str(int(num_val))) if catalog else str(num_val)
            observations.append(
                {
                    "observation_id": obs_id,
                    "person_id": person_id,
                    "observation_concept_id": entry.target_concept_id,
                    "observation_date": vdate,
                    "observation_datetime": None,
                    "observation_type_concept_id": 32865,
                    "value_as_number": num_val,
                    "value_as_string": str_val,
                    "value_as_concept_id": 0,
                    "qualifier_concept_id": 0,
                    "unit_concept_id": entry.unit_concept_id,
                    "provider_id": None,
                    "visit_occurrence_id": person_id,
                    "visit_detail_id": None,
                    "observation_source_value": obs_col,
                    "observation_source_concept_id": 0,
                    "unit_source_value": None,
                    "qualifier_source_value": None,
                    "value_source_value": str(row.get(obs_col)),
                    "observation_event_id": None,
                    "obs_event_field_concept_id": None,
                }
            )
            obs_id += 1

    return observations
