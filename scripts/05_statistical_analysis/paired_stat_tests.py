"""
Purpose:
    Compare rhythmic measures for human and machine translations using a
    paired t-test or a Wilcoxon signed-rank test, selected with a
    Shapiro-Wilk normality test on paired differences.
Input:
    --input-dir points to the folder containing the paired H1, revised H2
    (H2NEW), and H3 summary tables. The tables are UTF-8 TSV files with
    paired human and machine measurements and decimal commas.

Output:
    --output-dir receives a combined results table
    (paired_statistical_tests.tsv) and a UTF-8 plain-text report
    (paired_statistical_tests_report.txt).
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from scipy import stats


ALPHA = 0.05


@dataclass(frozen=True)
class AnalysisSpec:
    hypothesis: str
    metric: str
    file_path: Path
    ca_column: str
    ta_column: str
    report_label: str


def analysis_specs(input_dir: Path) -> list[AnalysisSpec]:
    return [
        AnalysisSpec(
            hypothesis="H1",
            metric="Simple proportions",
            file_path=input_dir / "hypothesis1" / "H1_summary_all_texts.tsv",
            ca_column="CA_prop_intervals_2_or_3",
            ta_column="TA_prop_intervals_2_or_3",
            report_label="prop_intervals_2_or_3",
        ),
        AnalysisSpec(
            hypothesis="H2NEW",
            metric="Stress-to-stress interval-1 proportions",
            file_path=input_dir / "hypothesis2" / "H2_summary_all_texts.tsv",
            ca_column="CA_prop_intervals_eq_1",
            ta_column="TA_prop_intervals_eq_1",
            report_label="prop_intervals_1",
        ),
        AnalysisSpec(
            hypothesis="H2NEW",
            metric="Stress-to-stress interval-4+ proportions",
            file_path=input_dir / "hypothesis2" / "H2_summary_all_texts.tsv",
            ca_column="CA_prop_intervals_ge_4",
            ta_column="TA_prop_intervals_ge_4",
            report_label="prop_intervals_4",
        ),
        AnalysisSpec(
            hypothesis="H3",
            metric="Weighted proportions",
            file_path=input_dir / "hypothesis3" / "H3_summary_all_texts.tsv",
            ca_column="CA_prop_seq_weighted_2_or_3",
            ta_column="TA_prop_seq_weighted_2_or_3",
            report_label="prop_seq_weighted_2_or_3",
        ),
    ]


def read_summary_table(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep="\t", decimal=",")
    for column in df.columns:
        if df[column].dtype == object:
            cleaned = df[column].astype(str).str.replace(",", ".", regex=False)
            try:
                df[column] = pd.to_numeric(cleaned)
            except ValueError:
                df[column] = df[column]
    return df


def cohen_d_paired(differences: pd.Series) -> float | None:
    std = differences.std(ddof=1)
    if pd.isna(std) or std == 0:
        return None
    return differences.mean() / std


def wilcoxon_effect_r(p_value: float, n_pairs: int) -> float | None:
    if n_pairs <= 0 or pd.isna(p_value) or p_value <= 0:
        return None
    z_value = abs(stats.norm.isf(p_value / 2))
    return z_value / math.sqrt(n_pairs)


def interpret_significance(p_value: float) -> str:
    if p_value < 0.01:
        return "highly significant"
    if p_value < 0.05:
        return "significant"
    return "not significant"


def choose_test(differences: pd.Series) -> tuple[str, float, float]:
    shapiro_stat, shapiro_p = stats.shapiro(differences)
    if shapiro_p > ALPHA:
        return "paired_t_test", shapiro_stat, shapiro_p
    return "wilcoxon_signed_rank", shapiro_stat, shapiro_p


def run_analysis(spec: AnalysisSpec) -> dict[str, object]:
    df = read_summary_table(spec.file_path)
    paired = df[["base_name", spec.ca_column, spec.ta_column]].copy()
    paired = paired.dropna()
    paired["difference_ca_minus_ta"] = paired[spec.ca_column] - paired[spec.ta_column]

    test_name, shapiro_stat, shapiro_p = choose_test(paired["difference_ca_minus_ta"])
    mean_ca = paired[spec.ca_column].mean()
    mean_ta = paired[spec.ta_column].mean()
    mean_diff = paired["difference_ca_minus_ta"].mean()
    n_pairs = len(paired)

    comparison = (
        "stress-to-stress interval proportions"
        if spec.hypothesis == "H2NEW"
        else "the rhythmic patterns"
    )
    result: dict[str, object] = {
        "hypothesis": spec.hypothesis,
        "metric": spec.metric,
        "measure": spec.report_label,
        "n_pairs": n_pairs,
        "null_hypothesis": f"There is no significant difference in {comparison} between human and machine translation.",
        "alternative_hypothesis": f"There is a significant difference in {comparison} between human and machine translation.",
        "ca_column": spec.ca_column,
        "ta_column": spec.ta_column,
        "mean_ca": mean_ca,
        "mean_ta": mean_ta,
        "mean_difference_ca_minus_ta": mean_diff,
        "shapiro_w": shapiro_stat,
        "shapiro_p": shapiro_p,
    }

    if test_name == "paired_t_test":
        test_stat, p_value = stats.ttest_rel(paired[spec.ca_column], paired[spec.ta_column])
        effect_size = cohen_d_paired(paired["difference_ca_minus_ta"])
        result.update(
            {
                "selected_test": "Paired Samples T-test",
                "test_statistic_name": "t",
                "test_statistic": test_stat,
                "p_value": p_value,
                "effect_size_name": "Cohen's d",
                "effect_size": effect_size,
            }
        )
    else:
        test_stat, p_value = stats.wilcoxon(paired[spec.ca_column], paired[spec.ta_column])
        effect_size = wilcoxon_effect_r(p_value, n_pairs)
        result.update(
            {
                "selected_test": "Wilcoxon Signed-Rank Test",
                "test_statistic_name": "W",
                "test_statistic": test_stat,
                "p_value": p_value,
                "effect_size_name": "r",
                "effect_size": effect_size,
            }
        )

    higher_group = "TA" if mean_ta > mean_ca else "CA"
    result["higher_group"] = higher_group
    result["significance"] = interpret_significance(result["p_value"])
    result["paper_report"] = build_report_sentence(result)
    return result


def format_p_value(value: float) -> str:
    if value < 0.001:
        return "p < 0.001"
    return f"p = {value:.4f}"


def build_report_sentence(result: dict[str, object]) -> str:
    test_name = result["selected_test"]
    stat_name = result["test_statistic_name"]
    stat_value = result["test_statistic"]
    p_value = result["p_value"]
    effect_name = result["effect_size_name"]
    effect_value = result["effect_size"]
    higher_group = result["higher_group"]
    significance = result["significance"]
    effect_text = "nan" if effect_value is None else f"{effect_value:.3f}"

    direction = "Machine Translation (TA)" if higher_group == "TA" else "Human Translation (CA)"
    return (
        f"{result['hypothesis']} ({result['measure']}): A Shapiro-Wilk test on the paired differences "
        f"(CA - TA) returned W={result['shapiro_w']:.3f}, {format_p_value(result['shapiro_p'])}, so a {test_name} was used. "
        f"The measure was {significance}; {direction} showed the higher mean "
        f"(CA M={result['mean_ca']:.6f}, TA M={result['mean_ta']:.6f}; "
        f"{stat_name}={stat_value:.3f}, {format_p_value(p_value)}, {effect_name}={effect_text})."
    )


def save_results(results: list[dict[str, object]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    results_df = pd.DataFrame(results)
    results_df.to_csv(output_dir / "paired_statistical_tests.tsv", sep="\t", index=False)

    report_path = output_dir / "paired_statistical_tests_report.txt"
    lines = [
        "Paired statistical tests for rhythmic measures",
        "",
        "Null hypothesis (H0): There is no significant difference in the rhythmic patterns between human and machine translation.",
        "Alternative hypothesis (H1): There is a significant difference in the rhythmic patterns between human and machine translation.",
        "",
    ]
    lines.extend(str(result["paper_report"]) for result in results)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run paired tests for H1, revised H2, and H3.")
    parser.add_argument("--input-dir", type=Path, required=True,
                        help="Folder containing the hypothesis1, hypothesis2, and hypothesis3 summaries")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Folder for the combined results and report")
    args = parser.parse_args()
    if not args.input_dir.is_dir():
        parser.error(f"Input directory does not exist: {args.input_dir}")

    results = [run_analysis(spec) for spec in analysis_specs(args.input_dir)]
    save_results(results, args.output_dir)

    for result in results:
        print(result["paper_report"])


if __name__ == "__main__":
    main()
