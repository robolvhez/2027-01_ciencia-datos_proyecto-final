"""Genomic ID linkage between MCPS clinical PATID (MCPSDS*) and Regeneron Genotype IID/FID."""

from __future__ import annotations

import csv
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

RGC_IID_PATTERN = re.compile(r"(?:MCPS_)?(MCPSRGN\d+)_(MEXB\d+)")


def parse_regeneron_iid(genotype_iid: str | None) -> tuple[str | None, str | None]:
    """Extract (rgc_id, mexb_id) from a Regeneron IID like 'MCPS_MCPSRGN000001_MEXB000300'."""
    if not genotype_iid:
        return None, None
    match = RGC_IID_PATTERN.search(str(genotype_iid).strip())
    if not match:
        return None, None
    return match.group(1), match.group(2)


def read_id_bridge(path: str | Path) -> dict[str, tuple[str, str]]:
    """Read a PATID -> (IID, FID) crosswalk file (CSV or TSV)."""
    file_path = Path(path)
    sep = "\t" if file_path.suffix.lower() in {".txt", ".tsv"} else ","
    bridge: dict[str, tuple[str, str]] = {}
    with file_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=sep)
        for row in reader:
            patid = (row.get("PATID") or "").strip()
            iid = (row.get("IID") or "").strip()
            fid = (row.get("FID") or iid).strip()
            if patid and iid:
                bridge[patid] = (iid, fid)
    return bridge


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
) -> list[dict[str, Any]]:
    """Build the OMOP `genomic_id_map` records linking `person_id`, `patid`, and `genotype_iid`."""
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows, start=1):
        person_id = int(row.get("person_id") or idx)
        patid = _clean_str(row.get("PATID"))
        iid = _clean_str(row.get("IID"))
        fid = _clean_str(row.get("FID")) or iid

        if not iid and patid and id_bridge and patid in id_bridge:
            iid, fid = id_bridge[patid]

        rgc_id, mexb_id = parse_regeneron_iid(iid)
        is_genotyped = 1 if iid is not None else 0

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
    return out
