"""
Purpose:
    Encode each transcribed syllable as 0 (unstressed), 1 (primary stress),
    or 2 (secondary stress).
Input:
    --input-dir points to UTF-8 tab-separated files named
    transcribed_<number>_<name>.txt, for example transcribed_18_example_CA.txt.
    Each row contains a numeric line ID, unique within the file, and a
    transcription whose syllables are separated by vertical bars.

Output:
    --output-dir receives UTF-8 tab-separated files (*_binary_*.txt) with
    a line ID and a stress pattern or a [BINARY NOT POSSIBLE] marker.
"""

import argparse
import csv
from pathlib import Path


def is_untranscribed(text: str) -> bool:
    """Return True if text contains any bracketed content [ ... ]."""
    return "[" in text and "]" in text


def transcription_to_binary(transcription: str) -> str:
    """
    Convert syllable transcription to a binary stress pattern.
    Returns a string of 0/1/2 (0 = unstressed, 1 = primary `, 2 = secondary %),
    or '[BINARY NOT POSSIBLE]'.
    """
    transcription = transcription.strip()

    # Case: untranscribed or placeholder text
    if not transcription or is_untranscribed(transcription):
        return "[BINARY NOT POSSIBLE]"

    # Split into syllables
    syllables = [s.strip() for s in transcription.split("|")]

    # If no usable syllables
    if not syllables:
        return "[BINARY NOT POSSIBLE]"

    try:
        # 1 for primary stress (`), 2 for secondary stress (%), else 0
        pattern = "".join(
            "1" if "`" in s else "2" if "%" in s else "0"
            for s in syllables
        )
        return pattern
    except Exception:
        return "[BINARY NOT POSSIBLE]"


def output_name_for(input_name: str) -> str | None:
    """
    Map 'transcribed_18_Mcpherson_Freak_TA.txt' -> '18_binary_Mcpherson_Freak_TA.txt'.
    Returns None if filename does not match expected pattern.
    """
    prefix = "transcribed_"
    if not input_name.startswith(prefix):
        return None
    rest = input_name[len(prefix):]
    if "_" not in rest:
        return None
    num, tail = rest.split("_", 1)
    if not num.isdigit():
        return None
    return f"{num}_binary_{tail}"


def convert_file(input_path: Path, output_path: Path) -> None:
    with input_path.open("r", encoding="utf-8") as f_in, \
         output_path.open("w", encoding="utf-8", newline="") as f_out:

        reader = csv.reader(f_in, delimiter="\t")
        writer = csv.writer(f_out, delimiter="\t")

        for row in reader:
            # Basic sanity check
            if len(row) < 2:
                continue

            line_number = row[0]
            transcription = row[1]

            pattern = transcription_to_binary(transcription)

            writer.writerow([line_number, pattern])


def main() -> None:
    parser = argparse.ArgumentParser(description="Encode syllable stress patterns.")
    parser.add_argument("--input-dir", type=Path, required=True,
                        help="Folder containing transcribed .txt files")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Folder for the encoded stress patterns")
    args = parser.parse_args()
    if not args.input_dir.is_dir():
        parser.error(f"Input directory does not exist: {args.input_dir}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    inputs = sorted(args.input_dir.glob("transcribed_*.txt"))
    if not inputs:
        print(f"No files found in {args.input_dir}")
        return

    for src in inputs:
        out_name = output_name_for(src.name)
        if not out_name:
            print(f"Skipping unexpected filename: {src.name}")
            continue
        dst = args.output_dir / out_name
        convert_file(src, dst)
        print(f"OK: {src.name} -> {dst.name}")


if __name__ == "__main__":
    main()
