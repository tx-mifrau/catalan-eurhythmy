#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Purpose:
    Calculate H1, H2, and H3 interval and motif metrics for one aligned line
    in a human and machine Catalan translation.
    H2 counts only intervals between consecutive stresses. The displayed
    intervals and interval total include the initial line-to-stress gap
    used for H1 and H3.
Input:
    --input-dir contains paired UTF-8 stress-position tables (TSV).
    --cleaned-dir must contain the matching cleaned_*.txt files.
    --transcribed-dir must contain an existing transcribed_*.txt file for
    each translation, human and machine. Both files are required to look
    up and display the transcriptions alongside the metrics.
    Cleaned and transcribed files are UTF-8 and tab-separated.
    The selected line ID must exist in both stress-position tables.
    If it is missing from a cleaned or transcribed file, the script
    displays [NOT FOUND] for that field.

Output:
    Console text showing the two versions of the line, their transcriptions,
    and their rhythmic metrics. The script writes no output file.
"""

# Details:
#
# Compute H1/H2/H3-style metrics for a single line (id) from a CA and TA file.
#
# Metrics:
#   - Proportion of intervals in {2,3}
#   - Proportion of intervals == 1
#   - Proportion of intervals >= 4
#   - Weighted motif count (sum of squared motif lengths)
#   - Proportion of weighted motif count (weighted / total intervals)

import csv
from pathlib import Path
from typing import List, Optional, Tuple


# ---- User inputs (example) ----
LINE_ID = 82
NOVEL_TITLE = "Lawrence_Virgin"  # match part of the filename after wsposition_

# ---- Parsing ----
def parse_positions(s: str) -> Optional[List[int]]:
    s = (s or "").strip()
    if not s:
        return []
    if s.casefold() == "[no positions]":
        return None
    return [int(x) for x in s.split(",") if x.strip() != ""]

def read_line_positions(path: str, line_id: int) -> Tuple[Optional[List[int]], Optional[str], Optional[List[int]]]:
    """
    Returns (positions, sw_pattern) for the given id.
    positions is None if [no positions], sw_pattern is None if [no pattern].
    """
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        required = {"id", "sw_pattern", "strong_positions"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                f"{path}: header must include columns {sorted(required)}; got {reader.fieldnames}"
            )

        for row in reader:
            if int(row["id"]) != line_id:
                continue
            sw = (row.get("sw_pattern", "") or "").strip()
            sw = None if sw.casefold() == "[no pattern]" or sw == "" else sw
            pos = parse_positions(row.get("strong_positions", ""))
            pos = None if pos is None else sorted(pos)
            return pos, sw, pos

    raise ValueError(f"id {line_id} not found in {path}")


def find_ca_ta_paths(title: str, folder: Path) -> Tuple[str, str]:
    """
    Find stress-position CA and TA files whose filenames contain the given title.
    """
    pattern = f"*wsposition*{title}*_CA.*"
    ca_matches = list(folder.glob(pattern))
    if not ca_matches:
        raise ValueError(f"No CA file found for title '{title}' in {folder}")
    if len(ca_matches) > 1:
        raise ValueError(f"Multiple CA files found for title '{title}': {[p.name for p in ca_matches]}")
    ca_path = ca_matches[0]

    ta_path = ca_path.with_name(ca_path.name.replace("_CA", "_TA"))
    if not ta_path.exists():
        raise ValueError(f"TA file not found for {ca_path.name}")

    return str(ca_path), str(ta_path)


def find_cleaned_ca_ta_paths(title: str, folder: Path) -> Tuple[str, str]:
    """
    Find cleaned CA and TA files whose filenames contain the given title.
    """
    pattern = f"cleaned_*{title}*_CA.txt"
    ca_matches = list(folder.glob(pattern))
    if not ca_matches:
        raise ValueError(f"No cleaned CA file found for title '{title}' in {folder}")
    if len(ca_matches) > 1:
        raise ValueError(f"Multiple cleaned CA files found for title '{title}': {[p.name for p in ca_matches]}")
    ca_path = ca_matches[0]

    ta_path = ca_path.with_name(ca_path.name.replace("_CA.txt", "_TA.txt"))
    if not ta_path.exists():
        raise ValueError(f"Cleaned TA file not found for {ca_path.name}")

    return str(ca_path), str(ta_path)

def find_transcribed_ca_ta_paths(title: str, folder: Path) -> Tuple[str, str]:
    """
    Find transcribed CA and TA files whose filenames contain the given title.
    """
    pattern = f"transcribed_*{title}*_CA.txt"
    ca_matches = list(folder.glob(pattern))
    if not ca_matches:
        raise ValueError(f"No transcribed CA file found for title '{title}' in {folder}")
    if len(ca_matches) > 1:
        raise ValueError(f"Multiple transcribed CA files found for title '{title}': {[p.name for p in ca_matches]}")
    ca_path = ca_matches[0]

    ta_path = ca_path.with_name(ca_path.name.replace("_CA.txt", "_TA.txt"))
    if not ta_path.exists():
        raise ValueError(f"Transcribed TA file not found for {ca_path.name}")

    return str(ca_path), str(ta_path)


def read_cleaned_line(path: str, line_id: int) -> str:
    """
    Reads the cleaned_with_ids line text for the given id.
    Expected format: id<TAB>text
    """
    with open(path, "r", encoding="utf-8") as f:
        for row in f:
            row = row.rstrip("\n")
            if not row:
                continue
            parts = row.split("\t", 1)
            if len(parts) != 2:
                continue
            try:
                rid = int(parts[0])
            except ValueError:
                continue
            if rid == line_id:
                return parts[1]
    return "[NOT FOUND]"

def read_transcribed_line(path: str, line_id: int) -> str:
    """
    Reads the transcribed_with_ids line text for the given id.
    Expected format: id<TAB>text
    """
    with open(path, "r", encoding="utf-8") as f:
        for row in f:
            row = row.rstrip("\n")
            if not row:
                continue
            parts = row.split("\t", 1)
            if len(parts) != 2:
                continue
            try:
                rid = int(parts[0])
            except ValueError:
                continue
            if rid == line_id:
                return parts[1]
    return "[NOT FOUND]"


# ---- Metrics ----
def boundary_intervals(pos: List[int]) -> List[int]:
    if not pos:
        return []
    d: List[int] = []
    prev = -1
    for p in pos:
        d.append(p - prev)
        prev = p
    return d

def repeated_motif_lengths_23(intervals: List[int]) -> List[int]:
    lengths: List[int] = []
    if not intervals:
        return lengths

    n = len(intervals)
    i = 0
    while i < n:
        if intervals[i] not in (2, 3):
            i += 1
            continue

        j = i
        while j < n and intervals[j] in (2, 3):
            j += 1
        segment = intervals[i:j]
        seg_len = len(segment)

        k = 0
        while k < seg_len:
            motif_len = None
            max_p = (seg_len - k) // 2
            for p in range(1, max_p + 1):
                if segment[k:k + p] == segment[k + p:k + 2 * p]:
                    motif_len = p
                    break

            if motif_len is None:
                k += 1
                continue

            repeats = 2
            while k + (repeats + 1) * motif_len <= seg_len:
                start = k + repeats * motif_len
                if segment[start:start + motif_len] == segment[k:k + motif_len]:
                    repeats += 1
                else:
                    break

            total_len = repeats * motif_len
            lengths.append(total_len)
            k += total_len

        i = j

    return lengths

def compute_metrics(pos: Optional[List[int]]) -> dict:
    if pos is None:
        return {
            "total_intervals": 0,
            "prop_2_or_3": None,
            "prop_eq_1": None,
            "prop_ge_4": None,
            "total_seq_weighted": 0,
            "prop_seq_weighted": None,
            "intervals": [],
            "sequences": [],
        }

    d = boundary_intervals(pos)
    total = len(d)

    h2_intervals = d[1:]
    h2_total = len(h2_intervals)
    n1 = sum(1 for di in h2_intervals if di == 1)
    n4 = sum(1 for di in h2_intervals if di >= 4)

    n2 = sum(1 for di in d if di == 2)
    n3 = sum(1 for di in d if di == 3)
    n23 = n2 + n3

    sequences = repeated_motif_lengths_23(d)
    total_seq_weighted = sum(s * s for s in sequences)

    def safe_div(a: int, b: int) -> Optional[float]:
        return (a / b) if b else None

    return {
        "total_intervals": total,
        "prop_2_or_3": safe_div(n23, total),
        "prop_eq_1": safe_div(n1, h2_total),
        "prop_ge_4": safe_div(n4, h2_total),
        "total_seq_weighted": total_seq_weighted,
        "prop_seq_weighted": safe_div(total_seq_weighted, total),
        "intervals": d,
        "sequences": sequences,
    }


def fmt(x: Optional[float]) -> str:
    if x is None:
        return "NA"
    return f"{x:.6f}"


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Compare rhythmic metrics for one aligned line.")
    ap.add_argument("--input-dir", type=Path, required=True,
                    help="Folder containing paired stress-position tables")
    ap.add_argument("--cleaned-dir", type=Path, required=True,
                    help="Folder containing matching cleaned .txt files")
    ap.add_argument("--transcribed-dir", type=Path, required=True,
                    help="Folder containing matching transcribed .txt files")
    args = ap.parse_args()
    for directory in (args.input_dir, args.cleaned_dir, args.transcribed_dir):
        if not directory.is_dir():
            ap.error(f"Input directory does not exist: {directory}")

    ca_path, ta_path = find_ca_ta_paths(NOVEL_TITLE, args.input_dir)
    ca_cleaned_path, ta_cleaned_path = find_cleaned_ca_ta_paths(NOVEL_TITLE, args.cleaned_dir)
    ca_transcribed_path, ta_transcribed_path = find_transcribed_ca_ta_paths(NOVEL_TITLE, args.transcribed_dir)
    ca_pos, ca_sw, _ = read_line_positions(ca_path, LINE_ID)
    ta_pos, ta_sw, _ = read_line_positions(ta_path, LINE_ID)
    ca_text = read_cleaned_line(ca_cleaned_path, LINE_ID)
    ta_text = read_cleaned_line(ta_cleaned_path, LINE_ID)
    ca_transcribed_text = read_transcribed_line(ca_transcribed_path, LINE_ID)
    ta_transcribed_text = read_transcribed_line(ta_transcribed_path, LINE_ID)

    ca = compute_metrics(ca_pos)
    ta = compute_metrics(ta_pos)

    print(f"Line id: {LINE_ID}")
    print("")
    print(f"CA file: {ca_path}")
    print(f"  line (sw_pattern): {ca_sw}")
    print(f"  line (cleaned text): {ca_text}")
    print(f"  line (transcribed text): {ca_transcribed_text}")
    print(f"  intervals: {ca['intervals']}")
    print(f"  repeated_motif_lengths_23: {ca['sequences']}")
    print(f"  total_intervals: {ca['total_intervals']}")
    print(f"  prop_2_or_3: {fmt(ca['prop_2_or_3'])}")
    print(f"  prop_eq_1: {fmt(ca['prop_eq_1'])}")
    print(f"  prop_ge_4: {fmt(ca['prop_ge_4'])}")
    print(f"  total_seq_weighted: {ca['total_seq_weighted']}")
    print(f"  prop_seq_weighted: {fmt(ca['prop_seq_weighted'])}")
    print("")
    print(f"TA file: {ta_path}")
    print(f"  line (sw_pattern): {ta_sw}")
    print(f"  line (cleaned text): {ta_text}")
    print(f"  line (transcribed text): {ta_transcribed_text}")
    print(f"  intervals: {ta['intervals']}")
    print(f"  repeated_motif_lengths_23: {ta['sequences']}")
    print(f"  total_intervals: {ta['total_intervals']}")
    print(f"  prop_2_or_3: {fmt(ta['prop_2_or_3'])}")
    print(f"  prop_eq_1: {fmt(ta['prop_eq_1'])}")
    print(f"  prop_ge_4: {fmt(ta['prop_ge_4'])}")
    print(f"  total_seq_weighted: {ta['total_seq_weighted']}")
    print(f"  prop_seq_weighted: {fmt(ta['prop_seq_weighted'])}")


if __name__ == "__main__":
    main()
