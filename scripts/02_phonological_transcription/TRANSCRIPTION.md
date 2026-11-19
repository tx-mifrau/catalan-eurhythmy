# Phonological transcription

## Purpose

Document how the study obtained phonological transcriptions using Segre.
Segre supports four varieties of Catalan: Central, North-Western, Balearic, and Valencian.

## Input

Use the cleaned UTF-8 `.txt` files. For aligned translations, use the cleaned
human and machine files. For original Catalan prose, use the curated selection
when available, or the full cleaned set otherwise. Preserve any tab-separated line IDs.
For aligned translations, each output row retains its alignment ID, even
when transcription fails. This lets readers match the corresponding lines in the English source and the human and machine translations.

## Procedure

```text
For each selected file:
    For each line:
        Separate the line ID, if present, from the text.
        If the text is empty or marked [EMPTY LINE]:
            Record [TEXT NOT TRANSCRIBED].
        Otherwise:
            Obtain a transcription from Segre using the Valencian variety setting.
            Use the transcription if it succeeds and returns text.
            Otherwise, record [TEXT NOT TRANSCRIBED].
        Write the line ID and result in the original row order.
    Save a separate log if any lines could not be transcribed.
```

## Output

One UTF-8 tab-separated `transcribed_*.txt` file per input, plus a `.txt` log
when any lines could not be transcribed. The original-prose workflow also
records line counts for cleaned human translations in a separate report.

Live transcription requires authorized TextServer access. Readers can reproduce
the downstream rhythm analysis using the saved stress-position tables in
[`data/input_wspositions`](../../data/input_wspositions).
[UPC Segre documentation and demo](https://nlp.lsi.upc.edu/freeling/demo/segre.php)
