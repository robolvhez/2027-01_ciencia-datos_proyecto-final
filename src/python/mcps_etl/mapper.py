"""Headless SNOMED CT / LOINC concept mapping and Athena verification (Usagi CLI replacement)."""

from __future__ import annotations

import csv
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

DEFAULT_MAP_PATH = Path(__file__).resolve().parents[3] / "configs" / "source_to_concept_map.csv"


@dataclass(frozen=True)
class ConceptMapEntry:
    """Single source-to-standard OMOP concept mapping entry."""

    source_code: str
    source_vocabulary_id: str
    source_code_description: str
    target_concept_id: int
    target_vocabulary_id: str
    target_concept_code: str
    omop_domain_id: str
    unit_concept_id: int | None
    range_low: float | None
    range_high: float | None
    valid_start_date: str
    valid_end_date: str
    invalid_reason: str | None


def _opt_int(val: Any) -> int | None:
    s = str(val).strip() if val is not None else ""
    return int(float(s)) if s else None


def _opt_float(val: Any) -> float | None:
    s = str(val).strip() if val is not None else ""
    return float(s) if s else None


def load_concept_map(path: str | Path = DEFAULT_MAP_PATH) -> dict[str, ConceptMapEntry]:
    """Load the curated MCPS source_to_concept_map CSV keyed by source_code."""
    entries: dict[str, ConceptMapEntry] = {}
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            code = row["source_code"].strip()
            inv = (row.get("invalid_reason") or "").strip() or None
            entries[code] = ConceptMapEntry(
                source_code=code,
                source_vocabulary_id=row["source_vocabulary_id"].strip(),
                source_code_description=row.get("source_code_description", "").strip(),
                target_concept_id=int(row["target_concept_id"]),
                target_vocabulary_id=row["target_vocabulary_id"].strip(),
                target_concept_code=row["target_concept_code"].strip(),
                omop_domain_id=row["omop_domain_id"].strip(),
                unit_concept_id=_opt_int(row.get("unit_concept_id")),
                range_low=_opt_float(row.get("range_low")),
                range_high=_opt_float(row.get("range_high")),
                valid_start_date=row.get("valid_start_date", "1970-01-01").strip(),
                valid_end_date=row.get("valid_end_date", "2099-12-31").strip(),
                invalid_reason=inv,
            )
    return entries


def verify_concepts_against_athena(
    athena_concepts: Iterable[Mapping[str, Any]],
    map_path: str | Path = DEFAULT_MAP_PATH,
) -> list[dict[str, Any]]:
    """Verify mapped `(target_vocabulary_id, target_concept_code)` against an Athena CONCEPT table.

    Checks that each native SNOMED CT / LOINC code resolves to the expected OMOP `concept_id`
    and is marked as an active Standard Concept (`standard_concept == 'S'`).
    """
    by_vocab_code: dict[tuple[str, str], Mapping[str, Any]] = {}
    for c in athena_concepts:
        key = (str(c["vocabulary_id"]).strip(), str(c["concept_code"]).strip())
        by_vocab_code[key] = c

    results: list[dict[str, Any]] = []
    for entry in load_concept_map(map_path).values():
        hit = by_vocab_code.get((entry.target_vocabulary_id, entry.target_concept_code))
        hit_id = int(hit["concept_id"]) if hit and hit.get("concept_id") is not None else None
        inv_reason = hit.get("invalid_reason") if hit else "MISSING"
        is_std = bool(hit and str(hit.get("standard_concept")) == "S" and not inv_reason)
        results.append(
            {
                "source_code": entry.source_code,
                "target_vocabulary_id": entry.target_vocabulary_id,
                "target_concept_code": entry.target_concept_code,
                "target_concept_id": entry.target_concept_id,
                "verified_concept_id": hit_id,
                "verified_concept_name": hit.get("concept_name") if hit else None,
                "verified_domain_id": hit.get("domain_id") if hit else None,
                "id_matches": hit_id == entry.target_concept_id,
                "is_valid_standard": is_std,
            }
        )
    return results


def _similarity(a: str, b: str) -> float:
    """Compute token/character similarity between two clinical descriptions."""
    a_low, b_low = a.lower(), b.lower()
    tokens_a = set(a_low.replace("/", " ").replace("-", " ").split())
    tokens_b = set(b_low.replace("/", " ").replace("-", " ").split())
    overlap = len(tokens_a & tokens_b) / max(len(tokens_a), 1)
    seq = SequenceMatcher(None, a_low, b_low).ratio()
    return 0.6 * overlap + 0.4 * seq


def suggest_mappings(
    source_terms: Iterable[Mapping[str, Any]],
    athena_concepts: Iterable[Mapping[str, Any]],
    domain_id: str | None = None,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """Headless Usagi replacement matching source descriptions against Athena standard concepts."""
    pool = [
        c
        for c in athena_concepts
        if str(c.get("standard_concept")) == "S"
        and (not domain_id or str(c.get("domain_id", "")).lower() == domain_id.lower())
    ]

    suggestions: list[dict[str, Any]] = []
    for row in source_terms:
        src_code = str(row["source_code"])
        src_desc = str(row.get("source_description") or src_code)
        scored = sorted(
            ((_similarity(src_desc, str(c["concept_name"])), c) for c in pool),
            key=lambda pair: pair[0],
            reverse=True,
        )[:top_k]
        for score, target in scored:
            suggestions.append(
                {
                    "source_code": src_code,
                    "source_description": src_desc,
                    "match_score": round(score, 4),
                    "target_concept_id": int(target["concept_id"]),
                    "target_concept_code": str(target["concept_code"]),
                    "target_concept_name": str(target["concept_name"]),
                    "target_vocabulary_id": str(target["vocabulary_id"]),
                    "target_domain_id": str(target["domain_id"]),
                }
            )
    return suggestions
