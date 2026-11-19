"""Strict Genomic ID linkage between MCPS clinical PATID (MCPSDS*) and Regeneron Genotype RegID (IID/FID)."""

from __future__ import annotations

import csv
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

RGC_IID_PATTERN = re.compile(r"(?:MCPS_)?(MCPSRGN\d+)_(MEXB\d+)")
EXPECTED_GENOTYPED_INDIVIDUALS: int = 140_831


def parse_regeneron_iid(genotype_iid: str | None) -> tuple[str | None, str | None]:
    """Extract (rgc_id, mexb_id) from a Regeneron IID like 'MCPS_MCPSRGN000001_MEXB000300'."""
    if not genotype_iid:
        return None, None
    match = RGC_IID_PATTERN.search(str(genotype_iid).strip())
    if not match:
        return None, None
    return match.group(1), match.group(2)


def read_id_bridge(path: str | Path) -> dict[str, tuple[str, str]]:
    """Read a PATID -> (IID, FID) crosswalk file (CSV or TSV), enforcing strict 1:1 uniqueness.

    Raises ValueError if any PATID or Regeneron IID (RegID) is duplicated.
    """
    file_path = Path(path)
    sep = "\t" if file_path.suffix.lower() in {".txt", ".tsv"} else ","
    bridge: dict[str, tuple[str, str]] = {}
    seen_iids: dict[str, str] = {}
    with file_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=sep)
        for row in reader:
            patid = (row.get("PATID") or "").strip()
            iid = (row.get("IID") or "").strip()
            fid = (row.get("FID") or iid).strip()
            if not patid or not iid:
                continue
            if patid in bridge and bridge[patid][0] != iid:
                raise ValueError(f"Duplicate PATID in ID bridge mapped to multiple RegIDs: {patid}")
            if iid in seen_iids and seen_iids[iid] != patid:
                raise ValueError(f"Duplicate RegID (IID) in ID bridge mapped to multiple PATIDs: {iid}")
            bridge[patid] = (iid, fid)
            seen_iids[iid] = patid
    return bridge


def read_plink_fam(path: str | Path) -> dict[str, str]:
    """Read a 6-column PLINK `.fam` file (`FID IID PAT MAT SEX PHENO`) into an `IID -> FID` mapping.

    Enforces strict uniqueness on `IID` (`RegID`), raising ValueError if any duplicate `RegID` exists.
    """
    file_path = Path(path)
    fam_samples: dict[str, str] = {}
    with file_path.open("r", encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            parts = raw_line.strip().split()
            if not parts:
                continue
            if len(parts) < 2:
                raise ValueError(f"Malformed PLINK .fam line {line_no} in {file_path}: expected >=2 columns")
            fid, iid = parts[0], parts[1]
            if iid in fam_samples:
                raise ValueError(f"Duplicate RegID (IID) detected in PLINK .fam file at line {line_no}: {iid}")
            fam_samples[iid] = fid
    return fam_samples


def validate_regid_linkage(
    genomic_id_map: Iterable[Mapping[str, Any]],
    expected_genotyped: int = EXPECTED_GENOTYPED_INDIVIDUALS,
) -> dict[str, Any]:
    """Validate that all mapped `patid` and `genotype_iid` (RegID) values have zero duplicates.

    Also compares the total number of genotyped individuals (`is_genotyped == 1`) against
    `EXPECTED_GENOTYPED_INDIVIDUALS` (140,831 in MCPS Freeze 150).
    """
    seen_patids: set[str] = set()
    seen_iids: set[str] = set()
    n_total = 0
    n_genotyped = 0

    for rec in genomic_id_map:
        n_total += 1
        patid = rec.get("patid")
        iid = rec.get("genotype_iid")
        is_geno = int(rec.get("is_genotyped") or 0)

        if patid:
            if patid in seen_patids:
                raise ValueError(f"Duplicate PATID detected in genomic_id_map: {patid}")
            seen_patids.add(str(patid))

        if iid:
            if iid in seen_iids:
                raise ValueError(f"Duplicate RegID (genotype_iid) detected in genomic_id_map: {iid}")
            seen_iids.add(str(iid))

        if is_geno == 1:
            if not iid:
                raise ValueError(f"Participant person_id={rec.get('person_id')} marked is_genotyped=1 without RegID")
            n_genotyped += 1

    return {
        "n_total": n_total,
        "n_genotyped": n_genotyped,
        "expected_genotyped": expected_genotyped,
        "matches_expected_140831": n_genotyped == expected_genotyped,
    }


def _clean_str(val: Any) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return None if s in {"", "NA", "NaN", "nan", "None"} else s


def _clean_float(val: Any) -> float | None:
    s = _clean_str(val)
    if s is None:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def build_genomic_id_map(
    rows: Iterable[Mapping[str, Any]],
    id_bridge: dict[str, tuple[str, str]] | None = None,
    fam_samples: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Build OMOP `genomic_id_map` records strictly linking `person_id`, `patid`, and verified `genotype_iid`.

    Never computes or synthesizes a `RegID` (`genotype_iid`) from a `PATID`. If a `PATID` cannot be mapped
    to a verified `RegID` (or if `fam_samples` is provided and the `RegID` is absent from `.fam`),
    `genotype_iid` is set to `None` and `is_genotyped` is set to `0`.
    """
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        person_id = int(row.get("person_id") or idx)
        patid = _clean_str(row.get("PATID"))
        iid = _clean_str(row.get("IID"))
        fid = _clean_str(row.get("FID")) or iid

        if not iid and patid and id_bridge and patid in id_bridge:
            iid, fid = id_bridge[patid]

        if fam_samples is not None:
            if iid and iid in fam_samples:
                fid = fid or fam_samples[iid]
            elif patid and patid in fam_samples:
                iid = patid
                fid = fam_samples[patid]
            else:
                iid = None
                fid = None

        rgc_id, mexb_id = parse_regeneron_iid(iid)
        is_genotyped = 1 if iid is not None else 0

        if isinstance(row, dict) and "IS_GENOTYPED" not in row:
            row["IS_GENOTYPED"] = is_genotyped

        rec: dict[str, Any] = {
            "person_id": person_id,
            "patid": patid,
            "genotype_iid": iid,
            "genotype_fid": fid,
            "rgc_id": rgc_id,
            "mexb_id": mexb_id,
            "is_genotyped": is_genotyped,
        }
        for k in range(1, 8):
            rec[f"pc{k}"] = _clean_float(row.get(f"PC{k}"))
        out.append(rec)

    validate_regid_linkage(out)
    return out
