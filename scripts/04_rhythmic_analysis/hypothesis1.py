#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Purpose:
    Calculate the proportion of inter-stress intervals of two or three
    syllables, including the interval from the start of the line. Compare
    human and machine Catalan translations by text.
Input:
    Paired UTF-8 tab-separated stress-position tables (.txt or .tsv).
    Matching filenames end in _CA for human and _TA for machine translation.
    Each table contains id, sw_pattern, and strong_positions.

Output:
    UTF-8 tab-separated files (.tsv) containing a paired metrics table and a
    summary per text, plus a combined summary (H1_summary_all_texts.tsv).
"""

# Details:
#
# Compute Hypothesis 1 metrics (boundary-inclusive inter-stress intervals) for all
# (_CA, _TA) file pairs in a folder, aggregating at the text level.
#
# INPUT files (TSV, even if .txt):
#   id<TAB>sw_pattern<TAB>strong_positions
# Example:
#   1    SwSwwS    0,2,5
#
# DEFINITION:
# - Strong positions are given (0-based).
# - Start boundary is treated as position -1.
# - Inter-stress intervals (boundary-inclusive):
#     d1 = p1 - (-1) = p1 + 1
#     d2 = p2 - p1
#     ...
#     dK = pK - p(K-1)
#
# AGGREGATED COUNTS (per text):
#   total_eq_2, total_eq_3, total_2_or_3, total_all_intervals
#   plus proportions for {2,3}, 2, and 3.
#
# OUTPUT:
# - One paired TSV per text (base name), written to an output folder.
# - One summary TSV per text.
# - One global summary TSV for all texts.

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

def read_tsv(path: Path) -> Tuple[Dict[int, Optional[List[int]]], set]:
    """
    Returns: ({id: [strong_positions]}, set_of_no_pattern_ids)
    """
    out: Dict[int, Optional[List[int]]] = {}
    no_pattern_ids: set = set()
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        required = {"id", "sw_pattern", "strong_positions"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                f"{path.name}: header must include columns {sorted(required)}; got {reader.fieldnames}"
            )

        for row in reader:
            line_id = int(row["id"])
            sw_pattern = (row.get("sw_pattern", "") or "").strip()
            strong_positions_raw = (row.get("strong_positions", "") or "").strip()
            if sw_pattern.casefold() == "[no pattern]" and strong_positions_raw.casefold() == "[no positions]":
                no_pattern_ids.add(line_id)
                out[line_id] = None
                continue

            pos = parse_positions(strong_positions_raw)
            out[line_id] = None if pos is None else sorted(pos)
    return out, no_pattern_ids


# -------------------------
# H1 metrics (boundary-inclusive)
# -------------------------

def boundary_intervals(pos: List[int]) -> List[int]:
    """
    Boundary-inclusive inter-stress intervals with start boundary at -1.
    """
    if not pos:
        return []
    d: List[int] = []
    prev = -1
    for p in pos:
        d.append(p - prev)
        prev = p
    return d  # length == number of stresses

def aggregate_counts(
    data: Dict[int, Optional[List[int]]],
    allowed_ids: Optional[set] = None,
) -> Tuple[int, int, int, int, Optional[float]]:
    """
    Returns (total_eq_2, total_eq_3, total_2_or_3, total_all, prop_23).
    """
    total_eq_2 = 0
    total_eq_3 = 0
    total_all = 0

    if allowed_ids is None:
        iter_ids = data.keys()
    else:
        iter_ids = allowed_ids

    for line_id in iter_ids:
        pos = data.get(line_id)
        if pos is None:
            continue
        d = boundary_intervals(pos)
        total_all += len(d)
        total_eq_2 += sum(1 for di in d if di == 2)
        total_eq_3 += sum(1 for di in d if di == 3)

    total_2_or_3 = total_eq_2 + total_eq_3
    if total_all == 0:
        return total_eq_2, total_eq_3, total_2_or_3, total_all, None

    prop_23 = total_2_or_3 / total_all
    return total_eq_2, total_eq_3, total_2_or_3, total_all, prop_23


def fmt_float(x: Optional[float]) -> str:
    if x is None:
        return ""
    return f"{x:.6f}".replace(".", ",")


# -------------------------
# Pairing logic: *_CA.* with *_TA.*
# -------------------------

def find_pairs(folder: Path) -> List[Tuple[str, Path, Path]]:
    """
    Finds pairs where filenames end with _CA or _TA in the stem.
    Example: MyText_CA.txt and MyText_TA.txt -> base "MyText"
    Returns list of (base, ca_path, ta_path)
    """
    files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {".txt", ".tsv"}]

    ca_map: Dict[str, Path] = {}
    ta_map: Dict[str, Path] = {}

    for p in files:
        stem = p.stem  # filename without extension
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
def write_paired_h1(base: str, ca_path: Path, ta_path: Path, out_dir: Path) -> Dict[str, str]:
    """
    Writes a paired TSV for this text and returns a dict of summary stats for the global summary TSV.
    """
    CA, ca_no_pattern = read_tsv(ca_path)
    TA, ta_no_pattern = read_tsv(ta_path)

    common_ids = set(CA.keys()) & set(TA.keys())
    valid_ids = common_ids - ca_no_pattern - ta_no_pattern

    ca_eq2, ca_eq3, ca_23, ca_all, ca_p23 = aggregate_counts(CA, valid_ids)
    ta_eq2, ta_eq3, ta_23, ta_all, ta_p23 = aggregate_counts(TA, valid_ids)

    diff_p23 = None if (ca_p23 is None or ta_p23 is None) else (ca_p23 - ta_p23)

    support_flag = ""
    if diff_p23 is not None:
        if diff_p23 > 0:
            support_flag = "CA>TA"
        elif diff_p23 < 0:
            support_flag = "TA>CA"
        else:
            support_flag = "TIE"

    paired_row = {
        "base_name": base,
        "CA_file": ca_path.name,
        "TA_file": ta_path.name,
        "CA_total_intervals_all": str(ca_all),
        "CA_total_intervals_eq_2": str(ca_eq2),
        "CA_total_intervals_eq_3": str(ca_eq3),
        "CA_total_intervals_2_or_3": str(ca_23),
        "CA_prop_intervals_2_or_3": fmt_float(ca_p23),
        "TA_total_intervals_all": str(ta_all),
        "TA_total_intervals_eq_2": str(ta_eq2),
        "TA_total_intervals_eq_3": str(ta_eq3),
        "TA_total_intervals_2_or_3": str(ta_23),
        "TA_prop_intervals_2_or_3": fmt_float(ta_p23),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{base}_H1_paired.tsv"
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(paired_row.keys()), delimiter="\t")
        writer.writeheader()
        writer.writerow(paired_row)

    summary_row = dict(paired_row)
    summary_row.update({
        "diff_prop_2_or_3_CA_minus_TA": fmt_float(diff_p23),
        "support_prop_2_or_3_CA_vs_TA": support_flag,
    })

    summary_path = out_dir / f"{base}_H1_summary.tsv"
    with summary_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_row.keys()), delimiter="\t")
        writer.writeheader()
        writer.writerow(summary_row)

    return summary_row


def main():
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
        help="Folder for the paired H1 tables and summaries.",
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
        summary = write_paired_h1(base, ca_path, ta_path, out_dir)
        summary_rows.append(summary)
        print(f"Processed: {base}")

    summary_path = out_dir / "H1_summary_all_texts.tsv"
    with summary_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\nWrote global summary to: {summary_path}")


if __name__ == "__main__":
    main()
