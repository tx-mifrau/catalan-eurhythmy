# Catalan Eurhythmy

This project contains the analysis code and working materials for *Do Machines Keep the Beat? Automatic Analysis of Eurhythmy in Catalan Human and Machine Literary Translation*. The study compares human translations (HT), machine translations (MT), and original Catalan prose (CA) using distances between stressed syllables and recurring rhythmic patterns.

## Installation

Run the
commands below from the project root.

```sh
python -m pip install -r requirements.txt
```

The figure scripts use base R. The original-text cleaner uses NLTK sentence
tokenization when the model data is available and a punctuation-based splitter
otherwise.

## Reproduce the rhythm summaries

Use the bundled [stress-position tables](data/input_wspositions) to reproduce the rhythmic analyses on our Catalan corpus. To analyse your own transcribed data, convert them to the same format by following the steps described in section [Preprocessing and stress encoding](#preprocessing-and-stress-encoding). Use `data/input_wspositions` for paired translations
and `data/input_wspositions/originals_CA` for original Catalan prose. The paired
tables use the historical labels `CA` for human translation and `TA` for machine
translation.

```sh
python scripts/04_rhythmic_analysis/hypothesis1.py --input-dir data/input_wspositions --output-dir work/hypothesis1
python scripts/04_rhythmic_analysis/hypothesis1_onlyCA.py --input-dir data/input_wspositions/originals_CA --output-dir work/hypothesis1_onlyCA
```

All six scripts use the same directory options. Use a distinct output
directory for each run.

| Analysis | Paired translations | Original Catalan prose |
| --- | --- | --- |
| H1 - Proportion of stress intervals of two or three syllables, including the initial boundary interval | [hypothesis1.py](scripts/04_rhythmic_analysis/hypothesis1.py) | [hypothesis1_onlyCA.py](scripts/04_rhythmic_analysis/hypothesis1_onlyCA.py) |
| H2 - Adjacent stresses and intervals of at least four syllables | [hypothesis2.py](scripts/04_rhythmic_analysis/hypothesis2.py) | [hypothesis2_onlyCA.py](scripts/04_rhythmic_analysis/hypothesis2_onlyCA.py) |
| H3 - Repeated motifs made up of intervals of two or three syllables | [hypothesis3.py](scripts/04_rhythmic_analysis/hypothesis3.py) | [hypothesis3_onlyCA.py](scripts/04_rhythmic_analysis/hypothesis3_onlyCA.py) |

The [line-metrics script](scripts/04_rhythmic_analysis/line_metrics_H1_H2_H3.py)
also requires matching cleaned and transcribed texts for the selected line.

## Reproduce the paired statistical tests

[paired_stat_tests.py](scripts/05_statistical_analysis/paired_stat_tests.py)
reads the bundled H1, revised H2, and H3 summaries and writes a combined TSV
and text report with four comparisons.

```sh
python scripts/05_statistical_analysis/paired_stat_tests.py --input-dir data/results --output-dir work/paired_stats
```

To use regenerated summaries, place them under `hypothesis1/`,
`hypothesis2/`, and `hypothesis3/` and pass their parent directory
as `--input-dir`.

## Regenerate the figures

```sh
Rscript scripts/06_visualisation/Hypothesis1_intervals2-3.R
Rscript scripts/06_visualisation/Hypothesis3_prop_intervals_2_or_3.R
Rscript scripts/06_visualisation/Hypothesis2_clashes_lapses.R
```

These scripts read the bundled summaries in [data/results](data/results) and
write PNGs in `data/results/plots/generated/`. Individual dots are jittered,
so their horizontal positions can vary between runs.

## Preprocessing and stress encoding

To preprocess another corpus, supply your own input texts. For paired
translations, run [split_aligned_text.py](scripts/01_preprocessing/split_aligned_text.py)
followed by [clean_aligned_translations.py](scripts/01_preprocessing/clean_aligned_translations.py).
For original Catalan prose, use
[clean_original_catalan_texts.py](scripts/01_preprocessing/clean_original_catalan_texts.py).
Each script accepts `--input-dir` and a new or empty `--output-dir`.
For aligned translations, the splitter's output directory is the cleaner's
input directory.

The [transcription notes](scripts/02_phonological_transcription/TRANSCRIPTION.md)
describe the Segre procedure. With your own existing transcription files, run
[1_to_binary.py](scripts/03_stress_encoding/1_to_binary.py) followed by
[2_convert2wS.py](scripts/03_stress_encoding/2_convert2wS.py). Both accept
`--input-dir` and `--output-dir`. The second script produces the
stress-position tables used above.

## Citation and licensing

See [CITATION.cff](CITATION.cff) for how to cite the analysis code. The project code is licensed under Creative Commons Attribution-NonCommercial 4.0 International. Corpus texts and other third-party materials are subject to their own terms. See [LICENSE](LICENSE) for the license details.
