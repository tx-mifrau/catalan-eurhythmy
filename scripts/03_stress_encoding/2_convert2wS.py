"""
Purpose:
    Convert numerical stress patterns to weak (w) and strong (S) syllables
    and record the zero-based positions of strong syllables.
Input:
    --input-dir points to UTF-8 tab-separated files named
    <number>_binary_<name>.txt, as produced by 1_to_binary.py.
    Each row contains a numeric line ID, unique within the file, and a
    numerical stress pattern or an unavailable-pattern marker.
    Rows with missing or nonnumeric IDs are skipped.

Output:
    --output-dir receives UTF-8 tab-separated files (*_wsposition_*.txt)
    with the columns id, sw_pattern, and strong_positions. Positions are
    zero-based and comma-separated.
"""

import argparse
import re
import csv
from pathlib import Path

def parse_row(row: list[str]):
    """
    Expected TSV: <id>\t<pattern>
    pattern may include only 0/1/2; anything else is ignored.
    """
    if not row or all(not cell.strip() for cell in row):
        return None

    if len(row) < 2:
        raise ValueError(f"Bad row (expected: id + pattern): {row!r}")

    line_id = int(row[0].strip())

    # keep only 0/1/2 in case there is punctuation
    pattern = re.sub(r"[^012]", "", row[1])
    if pattern == "":
        raise ValueError(f"No 0/1/2 digits found in pattern: {row!r}")

    return line_id, pattern

def convert(pattern: str):
    # 1 and 2 are strong; 0 is weak
    sw = "".join("S" if ch in ("1", "2") else "w" for ch in pattern)
    strong_positions = [i for i, ch in enumerate(pattern) if ch in ("1", "2")]
    return sw, strong_positions

def output_name_for(input_name: str) -> str | None:
    """
    Map '31_binary_Swift_Gulliver_CA.txt' -> '31_wsposition_Swift_Gulliver_CA.txt'.
    Returns None if filename does not match expected pattern.
    """
    marker = "_binary_"
    if marker not in input_name:
        return None
    prefix, suffix = input_name.split(marker, 1)
    if not prefix.isdigit():
        return None
    return f"{prefix}_wsposition_{suffix}"


def convert_file_to_tsv(input_path: str | Path, output_path: str | Path):
    input_path = Path(input_path)
    output_path = Path(output_path)

    with input_path.open("r", encoding="utf-8") as f_in, output_path.open("w", encoding="utf-8", newline="") as f_out:
        reader = csv.reader(f_in, delimiter="\t")
        writer = csv.writer(f_out, delimiter="\t")
        # header row
        writer.writerow(["id", "sw_pattern", "strong_positions"])

        for row in reader:
            if not row or all(not cell.strip() for cell in row):
                continue
            if len(row) < 2:
                raise ValueError(f"Bad row (expected: id + pattern): {row!r}")

            if not row[0].strip():
                continue
            if not row[0].strip().isdigit():
                continue
            line_id = int(row[0].strip())
            if "[BINARY NOT POSSIBLE]" in row[1]:
                writer.writerow([line_id, "[NO PATTERN]", "[NO POSITIONS]"])
                continue

            parsed = parse_row(row)
            if parsed is None:
                continue
            _, pattern = parsed
            sw, pos = convert(pattern)
            pos_str = ",".join(map(str, pos))  # empty string if no stresses
            writer.writerow([line_id, sw, pos_str])

def main() -> None:
    parser = argparse.ArgumentParser(description="Convert stress patterns to weak and strong syllables.")
    parser.add_argument("--input-dir", type=Path, required=True,
                        help="Folder containing numerical stress patterns")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Folder for the stress-position tables")
    args = parser.parse_args()
    if not args.input_dir.is_dir():
        parser.error(f"Input directory does not exist: {args.input_dir}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    inputs = sorted(args.input_dir.glob("*_binary_*.txt"))
    if not inputs:
        print(f"No files found in {args.input_dir}")
        return

    for src in inputs:
        out_name = output_name_for(src.name)
        if not out_name:
            print(f"Skipping unexpected filename: {src.name}")
            continue
        dst = args.output_dir / out_name
        convert_file_to_tsv(src, dst)
        print(f"OK: {src.name} -> {dst.name}")


if __name__ == "__main__":
    main()
