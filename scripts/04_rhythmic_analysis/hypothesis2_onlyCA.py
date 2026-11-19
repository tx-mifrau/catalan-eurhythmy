#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Purpose:
    Calculate the proportions of stress clashes (adjacent stresses) and
    stress lapses (inter-stress intervals of four or more syllables).
    Summarize each original Catalan text.
Input:
    UTF-8 tab-separated stress-position tables (.txt or .tsv), one per
    original Catalan text. Each table contains id, sw_pattern, and
    strong_positions.

Output:
    UTF-8 tab-separated files (.tsv) containing one summary per text and a
    combined summary (H2_summary_all_texts_onlyCA.tsv).
"""

# Details:
#
# Compute Hypothesis 2 metrics for all files in a folder (single-language, no CA/TA pairing),
# aggregating at the text level.
# NEW version:
# - Clash: proportion of consecutive inter-stress intervals == 1
# - Initial line stress is not counted as a clash
# - Lapse (long): proportion of inter-stress intervals >= 4
#
# INPUT files (TSV):
#   id<TAB>sw_pattern<TAB>strong_positions
# Example:
#   1    SwSwwS    0,2,5

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
# File discovery
# -------------------------

def find_files(folder: Path) -> List[Path]:
    return sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {".txt", ".tsv"}])


# -------------------------
# Output writers
# -------------------------

def write_single_h2(path: Path, out_dir: Path) -> Dict[str, str]:
    data = read_tsv(path)

    valid_ids = sorted(
        line_id for line_id, (pos, sw) in data.items()
        if pos is not None and sw is not None
    )

    total_K = 0
    total_n1 = 0
    total_n4 = 0

    for line_id in valid_ids:
        pos, _ = data[line_id]
        pos = pos if pos is not None else []

        d = boundary_intervals(pos)

        total_K += len(d)
        total_n1 += sum(1 for di in d if di == 1)
        total_n4 += sum(1 for di in d if di >= 4)

    prop_1 = (total_n1 / total_K) if total_K else None
    prop_4 = (total_n4 / total_K) if total_K else None

    summary_row = {
        "file_name": path.name,
        "total_intervals_all": str(total_K),
        "total_intervals_eq_1": str(total_n1),
        "total_intervals_ge_4": str(total_n4),
        "prop_intervals_eq_1": fmt_num(prop_1),
        "prop_intervals_ge_4": fmt_num(prop_4),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / f"{path.stem}_H2NEW_summary.tsv"
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
        help="Folder containing original Catalan stress-position tables (.txt or .tsv).",
    )
    ap.add_argument(
        "--output-dir", "--out-folder",
        type=Path,
        required=True,
        help="Folder for the H2 summary tables.",
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
        summary = write_single_h2(path, out_dir)
        summary_rows.append(summary)
        print(f"Processed: {path.name}")

    summary_path = out_dir / "H2_summary_all_texts_onlyCA.tsv"
    with summary_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\nWrote global summary to: {summary_path}")


if __name__ == "__main__":
    main()
