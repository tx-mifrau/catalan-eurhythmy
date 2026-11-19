#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Purpose:
    Calculate the proportion of inter-stress intervals of two or three
    syllables, including the interval from the start of the line. Summarize
    each original Catalan text.
Input:
    UTF-8 tab-separated stress-position tables (.txt or .tsv), one per
    original Catalan text. Each table contains id, sw_pattern, and
    strong_positions.

Output:
    UTF-8 tab-separated files (.tsv) containing one summary per text and a
    combined summary (H1_summary_all_texts_onlyCA.tsv).
"""

# Details:
#
# Compute Hypothesis 1 metrics (boundary-inclusive inter-stress intervals) for all
# files in a folder (single-language, no CA/TA pairing), aggregating at the text level.
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
# - One summary TSV per text.
# - One global summary TSV for all texts.
#

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
# File discovery: all *.txt/*.tsv
# -------------------------

def find_files(folder: Path) -> List[Path]:
    return sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {".txt", ".tsv"}])


# -------------------------
# Output writers
# -------------------------
def write_single_h1(path: Path, out_dir: Path) -> Dict[str, str]:
    """
    Writes a summary TSV for this text and returns a dict of summary stats for the global summary TSV.
    """
    data, no_pattern_ids = read_tsv(path)
    valid_ids = set(data.keys()) - no_pattern_ids

    eq2, eq3, total_23, total_all, p23 = aggregate_counts(data, valid_ids)

    summary_row = {
        "file_name": path.name,
        "total_intervals_all": str(total_all),
        "total_intervals_eq_2": str(eq2),
        "total_intervals_eq_3": str(eq3),
        "total_intervals_2_or_3": str(total_23),
        "prop_intervals_2_or_3": fmt_float(p23),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / f"{path.stem}_H1_summary.tsv"
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
        help="Folder containing original Catalan stress-position tables (.txt or .tsv).",
    )
    ap.add_argument(
        "--output-dir", "--out-folder",
        type=Path,
        required=True,
        help="Folder for the H1 summary tables.",
    )
    args = ap.parse_args()

    folder = args.input_dir
    if not folder.is_dir():
        ap.error(f"Input directory does not exist: {folder}")

    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    files = find_files(folder)
    if not files:
        raise SystemExit(
            "No input files found. Expected .txt or .tsv files\n"
            "in the specified folder."
        )

    summary_rows: List[Dict[str, str]] = []
    for path in files:
        summary = write_single_h1(path, out_dir)
        summary_rows.append(summary)
        print(f"Processed: {path.name}")

    summary_path = out_dir / "H1_summary_all_texts_onlyCA.tsv"
    with summary_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\nWrote global summary to: {summary_path}")


if __name__ == "__main__":
    main()
