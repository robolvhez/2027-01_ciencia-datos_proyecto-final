#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
"""Build a verified 1:1 PATID <-> Regeneron genotype IID/FID bridge file for `read_id_bridge()`."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

try:
    import argcomplete
except ImportError:  # pragma: no cover
    argcomplete = None  # type: ignore[assignment]

from .id_linkage import EXPECTED_GENOTYPED_INDIVIDUALS, read_plink_fam

DEFAULT_IID_PATID_PATTERN = re.compile(r"^(?:MCPS_)?(MCPSRGN\d+)_(MEXB\d+(?:-DUP)?)$")
DEFAULT_BRIDGE_OUT = "/tmp/mcps_patid_iid_bridge.tsv"
SUPPORTED_BRIDGE_SUFFIXES: frozenset[str] = frozenset({".tsv", ".txt", ".csv"})
BRIDGE_COLUMNS: tuple[str, str, str] = ("PATID", "IID", "FID")


def resolve_bridge_delimiter(path: str | Path) -> str:
    """Return the delimiter strictly matching `read_id_bridge()` supported formats (`.tsv`/`.txt` or `.csv`)."""
    suffix = Path(path).suffix.lower()
    if suffix not in SUPPORTED_BRIDGE_SUFFIXES:
        allowed = ", ".join(sorted(SUPPORTED_BRIDGE_SUFFIXES))
        raise ValueError(
            f"Unsupported bridge output format '{suffix or '<none>'}' for {path}; expected one of: {allowed}"
        )
    return "\t" if suffix in {".txt", ".tsv"} else ","


def read_baseline_patids(path: str | Path, patid_column: str = "PATID") -> list[str]:
    """Stream the `PATID` column from an MCPS baseline CSV/TSV file, enforcing completeness and uniqueness."""
    file_path = Path(path)
    sep = "\t" if file_path.suffix.lower() in {".txt", ".tsv"} else ","
    patids: list[str] = []
    seen: set[str] = set()

    with file_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=sep)
        if not reader.fieldnames or patid_column not in reader.fieldnames:
            raise ValueError(f"Column '{patid_column}' not found in baseline file: {file_path}")
        for line_no, row in enumerate(reader, start=2):
            patid = (row.get(patid_column) or "").strip()
            if not patid:
                raise ValueError(f"Empty {patid_column} detected in baseline file {file_path} at line {line_no}")
            if patid in seen:
                raise ValueError(f"Duplicate {patid_column} detected in baseline file {file_path}: {patid}")
            seen.add(patid)
            patids.append(patid)

    return patids


def extract_patid_from_iid(
    iid: str,
    pattern: str | re.Pattern[str] = DEFAULT_IID_PATID_PATTERN,
) -> str:
    """Extract the verbatim embedded `PATID` token (capture group 1) from a `.fam` `IID`."""
    regex = re.compile(pattern) if isinstance(pattern, str) else pattern
    cleaned = str(iid).strip()
    match = regex.search(cleaned)
    if not match or not match.groups():
        raise ValueError(f"Genotype IID '{cleaned}' did not match PATID extraction pattern '{regex.pattern}'")
    patid = match.group(1).strip()
    if not patid:
        raise ValueError(f"Extracted empty PATID from genotype IID '{cleaned}'")
    return patid


def build_patid_iid_bridge(
    baseline_patids: Iterable[str],
    fam_samples: Mapping[str, str],
    pattern: str | re.Pattern[str] = DEFAULT_IID_PATID_PATTERN,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Build complete `PATID -> (IID, FID)` bridge rows with strict 1:1 uniqueness and count guarantees.

    Invariants enforced:
    1. Zero empty or duplicate `PATID`s in `baseline_patids`.
    2. Every `.fam` `IID` matches `pattern` and maps to a unique `PATID` present in `baseline_patids`.
    3. Every baseline `PATID` is emitted in original order; ungenotyped `PATID`s have empty `IID` and `FID`.
    4. Non-empty `IID` values in the resulting bridge have zero duplicates and match `fam_samples` 1:1.
    """
    regex = re.compile(pattern) if isinstance(pattern, str) else pattern

    clean_baseline: list[str] = []
    baseline_set: set[str] = set()
    for raw_patid in baseline_patids:
        patid = str(raw_patid).strip() if raw_patid is not None else ""
        if not patid:
            raise ValueError("Empty PATID detected in baseline_patids")
        if patid in baseline_set:
            raise ValueError(f"Duplicate PATID detected in baseline_patids: {patid}")
        baseline_set.add(patid)
        clean_baseline.append(patid)

    patid_to_fam: dict[str, tuple[str, str]] = {}
    orphan_iids: list[str] = []
    for raw_iid, raw_fid in fam_samples.items():
        iid = str(raw_iid).strip()
        fid = str(raw_fid).strip() if raw_fid is not None and str(raw_fid).strip() else iid
        if not iid:
            raise ValueError("Empty IID detected in fam_samples")
        extracted_patid = extract_patid_from_iid(iid, pattern=regex)
        if extracted_patid in patid_to_fam:
            raise ValueError(
                f"Duplicate PATID '{extracted_patid}' extracted from multiple genotype IIDs: "
                f"'{patid_to_fam[extracted_patid][0]}' and '{iid}'"
            )
        if extracted_patid not in baseline_set:
            orphan_iids.append(iid)
            continue
        patid_to_fam[extracted_patid] = (iid, fid)

    if orphan_iids:
        raise ValueError(
            f"{len(orphan_iids)} genotype IID(s) from .fam could not be matched to any baseline PATID "
            f"(first unmatched: {orphan_iids[0]})"
        )

    bridge_rows: list[dict[str, str]] = []
    for patid in clean_baseline:
        if patid in patid_to_fam:
            iid, fid = patid_to_fam[patid]
        else:
            iid, fid = "", ""
        bridge_rows.append({"PATID": patid, "IID": iid, "FID": fid})

    # Post-build strict verification
    emitted_patids = [r["PATID"] for r in bridge_rows]
    non_empty_iids = [r["IID"] for r in bridge_rows if r["IID"]]
    expected_iids = {str(k).strip() for k in fam_samples}

    if len(emitted_patids) != len(clean_baseline) or len(set(emitted_patids)) != len(clean_baseline):
        raise ValueError("Post-build check failed: PATID completeness/uniqueness violated")
    if len(non_empty_iids) != len(set(non_empty_iids)):
        raise ValueError("Post-build check failed: duplicate non-empty IID detected in bridge")
    if len(non_empty_iids) != len(expected_iids) or set(non_empty_iids) != expected_iids:
        raise ValueError(
            f"Post-build check failed: bridge has {len(non_empty_iids)} non-empty IIDs "
            f"but .fam has {len(expected_iids)}"
        )

    n_matched = len(non_empty_iids)
    summary: dict[str, Any] = {
        "n_baseline_patids": len(clean_baseline),
        "n_fam_iids": len(expected_iids),
        "n_matched_genotyped": n_matched,
        "n_ungenotyped": len(clean_baseline) - n_matched,
        "expected_genotyped": EXPECTED_GENOTYPED_INDIVIDUALS,
        "matches_expected_140831": n_matched == EXPECTED_GENOTYPED_INDIVIDUALS,
    }
    return bridge_rows, summary


def write_id_bridge(rows: Sequence[Mapping[str, str]], out_path: str | Path) -> Path:
    """Write validated bridge rows in the exact `PATID`/`IID`/`FID` CSV or TSV format read by `read_id_bridge()`."""
    target = Path(out_path)
    sep = resolve_bridge_delimiter(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(BRIDGE_COLUMNS), delimiter=sep)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "PATID": row["PATID"],
                    "IID": row["IID"],
                    "FID": row["FID"],
                }
            )
    return target


def generate_bridge_file(
    baseline_path: str | Path,
    fam_path: str | Path,
    out_path: str | Path = DEFAULT_BRIDGE_OUT,
    *,
    patid_column: str = "PATID",
    pattern: str | re.Pattern[str] = DEFAULT_IID_PATID_PATTERN,
) -> dict[str, Any]:
    """Read baseline `PATID`s and `.fam` `IID`/`FID`s, validate strict 1:1 mapping, and write bridge file."""
    resolve_bridge_delimiter(out_path)
    baseline_patids = read_baseline_patids(baseline_path, patid_column=patid_column)
    fam_samples = read_plink_fam(fam_path)
    bridge_rows, summary = build_patid_iid_bridge(baseline_patids, fam_samples, pattern=pattern)
    written_path = write_id_bridge(bridge_rows, out_path)
    return {
        "status": "ok",
        "out_path": str(written_path),
        **summary,
    }


def build_parser() -> argparse.ArgumentParser:
    """Create the standalone CLI argument parser for `build_bridge.py` with argcomplete support."""
    parser = argparse.ArgumentParser(
        prog="mcps-build-bridge",
        description="Build a strict 1:1 PATID <-> Regeneron IID/FID bridge file compatible with read_id_bridge().",
    )
    parser.add_argument("--input", "-i", required=True, help="Path to MCPS baseline CSV/TSV containing PATID")
    parser.add_argument("--fam", "-f", required=True, help="Path to PLINK .fam file listing genotyped FID/IIDs")
    parser.add_argument(
        "--out",
        "-o",
        default=DEFAULT_BRIDGE_OUT,
        help=f"Output bridge path (.tsv, .txt, or .csv; default: {DEFAULT_BRIDGE_OUT})",
    )
    parser.add_argument(
        "--pattern",
        default=DEFAULT_IID_PATID_PATTERN.pattern,
        help="Regex whose capture group 1 extracts PATID from .fam IID",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Execute standalone bridge generation CLI."""
    parser = build_parser()
    if argcomplete is not None:
        argcomplete.autocomplete(parser)
    args = parser.parse_args(argv)
    report = generate_bridge_file(
        baseline_path=args.input,
        fam_path=args.fam,
        out_path=args.out,
        pattern=args.pattern,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
