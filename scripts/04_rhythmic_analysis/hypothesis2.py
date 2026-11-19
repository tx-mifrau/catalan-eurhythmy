#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Purpose:
    Calculate the proportions of stress clashes (adjacent stresses) and
    stress lapses (inter-stress intervals of four or more syllables).
    Compare human and machine Catalan translations by text.
Input:
    Paired UTF-8 tab-separated stress-position tables (.txt or .tsv).
    Matching filenames end in _CA for human and _TA for machine translation.
    Each table contains id, sw_pattern, and strong_positions.

Output:
    UTF-8 tab-separated files (.tsv) containing a paired metrics table and a
    summary per text, plus a combined summary (H2_summary_all_texts.tsv).
"""

# Details:
#
# Compute Hypothesis 2 metrics for paired (_CA, _TA) files, aggregating at the text level.
# NEW version:
# - Clash: proportion of consecutive inter-stress intervals == 1
# - Initial line stress is not counted as a clash
# - Lapse (long): proportion of inter-stress intervals >= 4
#
# INPUT files (TSV):
#   id<TAB>sw_pattern<TAB>strong_positions
# Example:
#   1    SwSwwS    0,2,5
#
# Lines where either side has [NO POSITIONS] or [NO PATTERN] are skipped.

import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# -------------------------
# Parsing
# -------------------------

def parse_positions(s: str) -> Optional[List[int]]:
    s = (s or "").strip()
    if not s:
        return []
    if s.casefold() == "[no positions]":
        return None
    return [int(x) for x in s.split(",") if x.strip() != ""]

def parse_sw_pattern(s: str) -> Optional[str]:
    s = (s or "").strip()
    if not s:
        return None
    if s.casefold() == "[no pattern]":
        return None
    return s

def read_tsv(path: Path) -> Dict[int, Tuple[Optional[List[int]], Optional[str]]]:
    """
    Returns: {id: (positions, sw_pattern)}
    """
    out: Dict[int, Tuple[Optional[List[int]], Optional[str]]] = {}
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        required = {"id", "sw_pattern", "strong_positions"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                f"{path.name}: header must include columns {sorted(required)}; got {reader.fieldnames}"
            )

        for row in reader:
            line_id = int(row["id"])
            pos = parse_positions(row.get("strong_positions", ""))
            pos = None if pos is None else sorted(pos)
            sw = parse_sw_pattern(row.get("sw_pattern", ""))
            out[line_id] = (pos, sw)
    return out


# -------------------------
# Metrics
# -------------------------

def boundary_intervals(pos: List[int]) -> List[int]:
    if len(pos) < 2:
        return []
    return [curr - prev for prev, curr in zip(pos, pos[1:])]

def fmt_num(x: Optional[float]) -> str:
    if x is None:
        return ""
    return f"{x:.6f}".replace(".", ",")

def support_label(diff: Optional[float]) -> str:
    if diff is None:
        return ""
    if diff > 0:
        return "CA>TA"
    if diff < 0:
        return "TA>CA"
    return "TIE"


# -------------------------
# Pairing logic
# -------------------------

def find_pairs(folder: Path) -> List[Tuple[str, Path, Path]]:
    files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {".txt", ".tsv"}]

    ca_map: Dict[str, Path] = {}
    ta_map: Dict[str, Path] = {}

    for p in files:
        stem = p.stem
        if stem.endswith("_CA"):
            base = stem[:-3]
            ca_map[base] = p
        elif stem.endswith("_TA"):
            base = stem[:-3]
            ta_map[base] = p

    bases = sorted(set(ca_map) & set(ta_map))
    return [(b, ca_map[b], ta_map[b]) for b in bases]


# -------------------------
# Output writers
# -------------------------

def write_paired_h2(base: str, ca_path: Path, ta_path: Path, out_dir: Path) -> Dict[str, str]:
    CA = read_tsv(ca_path)
    TA = read_tsv(ta_path)

    valid_ids = sorted(
        line_id for line_id in (set(CA) & set(TA))
        if CA.get(line_id)[0] is not None and CA.get(line_id)[1] is not None
        and TA.get(line_id)[0] is not None and TA.get(line_id)[1] is not None
    )

    ca_total_K = 0
    ta_total_K = 0
    ca_total_n1 = 0
    ta_total_n1 = 0
    ca_total_n4 = 0
    ta_total_n4 = 0

    for line_id in valid_ids:
        ca_pos, _ = CA[line_id]
        ta_pos, _ = TA[line_id]
        ca_pos = ca_pos if ca_pos is not None else []
        ta_pos = ta_pos if ta_pos is not None else []

        ca_d = boundary_intervals(ca_pos)
        ta_d = boundary_intervals(ta_pos)

        ca_total_K += len(ca_d)
        ta_total_K += len(ta_d)

        ca_total_n1 += sum(1 for di in ca_d if di == 1)
        ta_total_n1 += sum(1 for di in ta_d if di == 1)
        ca_total_n4 += sum(1 for di in ca_d if di >= 4)
        ta_total_n4 += sum(1 for di in ta_d if di >= 4)

    ca_prop_1 = (ca_total_n1 / ca_total_K) if ca_total_K else None
    ta_prop_1 = (ta_total_n1 / ta_total_K) if ta_total_K else None
    ca_prop_4 = (ca_total_n4 / ca_total_K) if ca_total_K else None
    ta_prop_4 = (ta_total_n4 / ta_total_K) if ta_total_K else None

    diff_prop_1 = None if (ca_prop_1 is None or ta_prop_1 is None) else (ca_prop_1 - ta_prop_1)
    diff_prop_4 = None if (ca_prop_4 is None or ta_prop_4 is None) else (ca_prop_4 - ta_prop_4)

    paired_row = {
        "base_name": base,
        "CA_file": ca_path.name,
        "TA_file": ta_path.name,
        "CA_total_intervals_all": str(ca_total_K),
        "CA_total_intervals_eq_1": str(ca_total_n1),
        "CA_total_intervals_ge_4": str(ca_total_n4),
        "CA_prop_intervals_eq_1": fmt_num(ca_prop_1),
        "CA_prop_intervals_ge_4": fmt_num(ca_prop_4),
        "TA_total_intervals_all": str(ta_total_K),
        "TA_total_intervals_eq_1": str(ta_total_n1),
        "TA_total_intervals_ge_4": str(ta_total_n4),
        "TA_prop_intervals_eq_1": fmt_num(ta_prop_1),
        "TA_prop_intervals_ge_4": fmt_num(ta_prop_4),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{base}_H2NEW_paired.tsv"
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(paired_row.keys()), delimiter="\t")
        writer.writeheader()
        writer.writerow(paired_row)

    summary_row = dict(paired_row)
    summary_row.update({
        "diff_prop_eq_1_CA_minus_TA": fmt_num(diff_prop_1),
        "diff_prop_ge_4_CA_minus_TA": fmt_num(diff_prop_4),
        "support_prop_eq_1_CA_vs_TA": support_label(diff_prop_1),
        "support_prop_ge_4_CA_vs_TA": support_label(diff_prop_4),
    })

    summary_path = out_dir / f"{base}_H2NEW_summary.tsv"
    with summary_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_row.keys()), delimiter="\t")
        writer.writeheader()
        writer.writerow(summary_row)

    return summary_row


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input-dir", "--folder",
        type=Path,
        required=True,
        help="Folder containing paired _CA and _TA stress-position tables (.txt or .tsv).",
    )
    ap.add_argument(
        "--output-dir", "--out-folder",
        type=Path,
        required=True,
        help="Folder for the paired H2 tables and summaries.",
    )
    args = ap.parse_args()

    folder = args.input_dir
    if not folder.is_dir():
        ap.error(f"Input directory does not exist: {folder}")

    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    pairs = find_pairs(folder)
    if not pairs:
        raise SystemExit(
            "No pairs found. Expected filenames like:\n"
            "  Something_CA.txt  and  Something_TA.txt\n"
            "in the specified folder."
        )

    summary_rows: List[Dict[str, str]] = []
    for base, ca_path, ta_path in pairs:
        summary = write_paired_h2(base, ca_path, ta_path, out_dir)
        summary_rows.append(summary)
        print(f"Processed: {base}")

    summary_path = out_dir / "H2_summary_all_texts.tsv"
    with summary_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\nWrote global summary to: {summary_path}")


if __name__ == "__main__":
    main()
