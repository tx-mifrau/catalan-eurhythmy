#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Purpose:
    Measure repeated rhythmic motifs composed of inter-stress intervals of
    two or three syllables, including their lengths and weighted counts.
    Compare human and machine Catalan translations by text.
Input:
    Paired UTF-8 tab-separated stress-position tables (.txt or .tsv).
    Matching filenames end in _CA for human and _TA for machine translation.
    Each table contains id, sw_pattern, and strong_positions.

Output:
    UTF-8 tab-separated files (.tsv) containing a paired metrics table and a
    summary per text, plus a combined summary (H3_summary_all_texts.tsv).
"""

# Details:
#
# Compute Hypothesis 3 metrics for paired (_CA, _TA) files, aggregating at the text level.
#
# Hypothesis: CA has more and longer repeated motifs of intervals in {2,3}.
#
# INPUT files (TSV, even if .txt):
#   id<TAB>sw_pattern<TAB>strong_positions
# Example:
#   1    SwSwwS    0,2,5
#
# We skip lines where either side has [NO PATTERN] and [NO POSITIONS].

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
# H3 metrics (repeated motifs of 2/3 intervals)
# -------------------------

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
    """
    Returns lengths of consecutive blocks where a motif of {2,3} repeats
    at least twice (e.g., 223223, 33, 2323).
    """
    lengths: List[int] = []
    if not intervals:
        return lengths

    n = len(intervals)
    i = 0
    while i < n:
        if intervals[i] not in (2, 3):
            i += 1
            continue

        # find the next segment of only 2/3 intervals
        j = i
        while j < n and intervals[j] in (2, 3):
            j += 1
        segment = intervals[i:j]
        seg_len = len(segment)

        k = 0
        while k < seg_len:
            # smallest motif length that repeats at least twice
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

def aggregate_repeated_motifs(
    data: Dict[int, Optional[List[int]]],
    allowed_ids: Optional[set] = None,
) -> Tuple[int, int, int, int, Optional[float], Optional[float], int, Optional[float]]:
    """
    Returns (total_intervals, total_sequences, total_seq_len, max_seq_len,
    mean_seq_len, prop_in_sequences, total_seq_weighted, prop_seq_weighted).
    """
    total_intervals = 0
    total_runs = 0
    total_run_len = 0
    max_run_len = 0
    total_weighted = 0

    if allowed_ids is None:
        iter_ids = data.keys()
    else:
        iter_ids = allowed_ids

    for line_id in iter_ids:
        pos = data.get(line_id)
        if pos is None:
            continue
        d = boundary_intervals(pos)
        # Sequences are computed per line; never extend a sequence across lines.
        total_intervals += len(d)
        sequences = repeated_motif_lengths_23(d)
        if sequences:
            total_runs += len(sequences)
            total_run_len += sum(sequences)
            max_run_len = max(max_run_len, max(sequences))
            total_weighted += sum(s * s for s in sequences)

    if total_intervals == 0:
        return total_intervals, total_runs, total_run_len, max_run_len, None, None, total_weighted, None

    mean_run_len = (total_run_len / total_runs) if total_runs else None
    prop_in_runs = total_run_len / total_intervals
    prop_weighted = total_weighted / total_intervals
    return (
        total_intervals,
        total_runs,
        total_run_len,
        max_run_len,
        mean_run_len,
        prop_in_runs,
        total_weighted,
        prop_weighted,
    )

def fmt_float(x: Optional[float]) -> str:
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

def write_paired_h3(base: str, ca_path: Path, ta_path: Path, out_dir: Path) -> Dict[str, str]:
    CA, ca_no_pattern = read_tsv(ca_path)
    TA, ta_no_pattern = read_tsv(ta_path)

    common_ids = set(CA.keys()) & set(TA.keys())
    valid_ids = common_ids - ca_no_pattern - ta_no_pattern

    (
        ca_total,
        ca_runs,
        ca_run_len,
        ca_max_run,
        ca_mean_run,
        ca_prop,
        ca_weighted,
        ca_weighted_prop,
    ) = aggregate_repeated_motifs(CA, valid_ids)
    (
        ta_total,
        ta_runs,
        ta_run_len,
        ta_max_run,
        ta_mean_run,
        ta_prop,
        ta_weighted,
        ta_weighted_prop,
    ) = aggregate_repeated_motifs(TA, valid_ids)

    diff_runs = ca_runs - ta_runs
    diff_run_len = ca_run_len - ta_run_len
    diff_max_run = ca_max_run - ta_max_run
    diff_mean_run = None if (ca_mean_run is None or ta_mean_run is None) else (ca_mean_run - ta_mean_run)
    diff_prop = None if (ca_prop is None or ta_prop is None) else (ca_prop - ta_prop)
    diff_weighted_prop = None if (ca_weighted_prop is None or ta_weighted_prop is None) else (ca_weighted_prop - ta_weighted_prop)

    paired_row = {
        "base_name": base,
        "CA_file": ca_path.name,
        "TA_file": ta_path.name,
        "CA_total_intervals_all": str(ca_total),
        "CA_total_sequences_2_or_3": str(ca_runs),
        "CA_total_seq_len_2_or_3": str(ca_run_len),
        "CA_max_seq_len_2_or_3": str(ca_max_run),
        "CA_mean_seq_len_2_or_3": fmt_float(ca_mean_run),
        "CA_prop_intervals_in_2_or_3_sequences": fmt_float(ca_prop),
        "CA_total_seq_weighted_2_or_3": str(ca_weighted),
        "CA_prop_seq_weighted_2_or_3": fmt_float(ca_weighted_prop),
        "TA_total_intervals_all": str(ta_total),
        "TA_total_sequences_2_or_3": str(ta_runs),
        "TA_total_seq_len_2_or_3": str(ta_run_len),
        "TA_max_seq_len_2_or_3": str(ta_max_run),
        "TA_mean_seq_len_2_or_3": fmt_float(ta_mean_run),
        "TA_prop_intervals_in_2_or_3_sequences": fmt_float(ta_prop),
        "TA_total_seq_weighted_2_or_3": str(ta_weighted),
        "TA_prop_seq_weighted_2_or_3": fmt_float(ta_weighted_prop),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{base}_H3_paired.tsv"
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(paired_row.keys()), delimiter="\t")
        writer.writeheader()
        writer.writerow(paired_row)

    summary_row = dict(paired_row)
    summary_row.update({
        "diff_total_sequences_2_or_3_CA_minus_TA": str(diff_runs),
        "diff_total_seq_len_2_or_3_CA_minus_TA": str(diff_run_len),
        "diff_max_seq_len_2_or_3_CA_minus_TA": str(diff_max_run),
        "diff_mean_seq_len_2_or_3_CA_minus_TA": fmt_float(diff_mean_run),
        "diff_prop_intervals_in_2_or_3_sequences_CA_minus_TA": fmt_float(diff_prop),
        "diff_prop_seq_weighted_2_or_3_CA_minus_TA": fmt_float(diff_weighted_prop),
        "support_total_sequences_2_or_3_CA_vs_TA": support_label(float(diff_runs)),
        "support_total_seq_len_2_or_3_CA_vs_TA": support_label(float(diff_run_len)),
        "support_max_seq_len_2_or_3_CA_vs_TA": support_label(float(diff_max_run)),
        "support_mean_seq_len_2_or_3_CA_vs_TA": support_label(diff_mean_run),
        "support_prop_intervals_in_2_or_3_sequences_CA_vs_TA": support_label(diff_prop),
        "support_prop_seq_weighted_2_or_3_CA_vs_TA": support_label(diff_weighted_prop),
    })

    summary_path = out_dir / f"{base}_H3_summary.tsv"
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
        help="Folder for the paired H3 tables and summaries.",
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
        summary = write_paired_h3(base, ca_path, ta_path, out_dir)
        summary_rows.append(summary)
        print(f"Processed: {base}")

    summary_path = out_dir / "H3_summary_all_texts.tsv"
    with summary_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\nWrote global summary to: {summary_path}")


if __name__ == "__main__":
    main()
