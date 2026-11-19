"""
Purpose:
    Split aligned English source text, human Catalan translation, and
    machine Catalan translation into separate files with shared line IDs.
Input:
    --input-dir points to a folder of UTF-8 tab-separated text files (.txt).
    Each row contains the English source, human translation, and machine
    translation, in that order.

Output:
    --output-dir receives three UTF-8 tab-separated files per input
    (_EN.txt, _CA.txt, and _TA.txt), each with a line ID and its text.
"""

import argparse
from pathlib import Path

SUFFIXES = {"EN": 0, "CA": 1, "TA": 2}  # original, human, machine

def out_basename(path: Path) -> str:
    stem = path.stem
    return stem[:-len("_Alineat")] if stem.endswith("_Alineat") else stem

def process_file(path: Path, output_dir: Path):
    rows = {key: [] for key in SUFFIXES}
    with path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            cols = line.rstrip("\n").split("\t")
            while len(cols) < 3:
                cols.append("")  # pad missing columns
            for key, col_idx in SUFFIXES.items():
                rows[key].append(f"{idx}\t{cols[col_idx]}")

    output_dir.mkdir(parents=True, exist_ok=True)
    base = out_basename(path)
    for key in SUFFIXES:
        out_path = output_dir / f"{base}_{key}{path.suffix}"
        out_path.write_text("\n".join(rows[key]), encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(description="Split aligned texts by version.")
    parser.add_argument("--input-dir", type=Path, required=True,
                        help="Folder containing aligned .txt files")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="New or empty folder for the split .txt files")
    args = parser.parse_args()
    if not args.input_dir.is_dir():
        parser.error(f"Input directory does not exist: {args.input_dir}")

    output_dir = args.output_dir
    if output_dir.exists():
        if not output_dir.is_dir():
            parser.error(f"Output path is not a directory: {output_dir}")
        if any(output_dir.iterdir()):
            parser.error(
                f"Output directory is not empty: {output_dir}\n"
                "Choose a new or empty directory with --output-dir."
            )

    for path in args.input_dir.glob("*.txt"):
        stem = path.stem
        if stem.endswith(("_EN", "_CA", "_TA")):
            continue  # skip already-split files
        process_file(path, output_dir)

if __name__ == "__main__":
    main()
