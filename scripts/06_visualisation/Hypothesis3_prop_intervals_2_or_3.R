#!/usr/bin/env Rscript

# Purpose:
#     Compare weighted measures of repeated motifs of two- or three-syllable
#     intervals across human translations, machine translations, and original
#     Catalan prose.
# Input:
#     Two tab-separated H3 summary files (.tsv) with decimal commas, one for
#     paired translations and one for original Catalan prose.
#
# Output:
#     One PNG image (.png) containing one set of boxplots with individual text
#     values.

# Boxplots for prop_seq_weighted_2_or_3 across HT, MT, CA
# - HT first (blue), MT second (green), CA third (orange)
# - Same Y-axis scale including all values
# - Boxplot outlier symbols hidden
# - Individual points shown with jitter
# - Y axis labels every 0.1

# Run from the project root.
results_dir <- file.path("data", "results")
input_ht_ta <- file.path(results_dir, "hypothesis3", "H3_summary_all_texts.tsv")
input_ca <- file.path(results_dir, "hypothesis3_onlyCA", "H3_summary_all_texts_onlyCA.tsv")
output_png <- file.path(
  results_dir, "plots", "generated",
  "boxplots_H3_2_or_3_same_scale.png"
)

dir.create(dirname(output_png), recursive = TRUE, showWarnings = FALSE)

# Read input files
ht_ta <- read.delim(input_ht_ta, sep = "\t", dec = ",", stringsAsFactors = FALSE)
ca    <- read.delim(input_ca,    sep = "\t", dec = ",", stringsAsFactors = FALSE)

# In this file, the column named CA_prop_seq_weighted_2_or_3 actually represents HT
ht_values <- ht_ta$CA_prop_seq_weighted_2_or_3
mt_values <- ht_ta$TA_prop_seq_weighted_2_or_3
ca_values <- ca$prop_seq_weighted_2_or_3

# Build long-format data frame
data <- data.frame(
  group = c(
    rep("HT", length(ht_values)),
    rep("MT", length(mt_values)),
    rep("CA", length(ca_values))
  ),
  value = c(ht_values, mt_values, ca_values)
)

# Remove missing values
data <- data[!is.na(data$value), ]

# Keep group order fixed in the plot
data$group <- factor(data$group, levels = c("HT", "MT", "CA"))

# Use full data range so the Y-axis keeps the same scale
y_lim <- range(data$value, na.rm = TRUE)

# Optional small margin so points do not touch the borders
y_pad <- 0.03 * diff(y_lim)
if (y_pad == 0) y_pad <- 0.01
y_lim <- c(y_lim[1] - y_pad, y_lim[2] + y_pad)

# Define Y-axis ticks every 0.1
y_ticks <- seq(
  from = floor(y_lim[1] * 10) / 10,
  to   = ceiling(y_lim[2] * 10) / 10,
  by   = 0.1
)

# Plot
png(output_png, width = 1000, height = 700, res = 120)

boxplot(
  value ~ group,
  data = data,
  main = "Weighted motif count across corpus components",
  xlab = "Corpus component",
  ylab = "Normalised weighted motif count",
  col = c("#8DA0CB", "#66C2A5", "#FC8D62"),  # HT blue, MT green, CA orange
  border = "#333333",
  outline = FALSE,
  ylim = y_lim,
  yaxt = "n"
)

axis(2, at = y_ticks, labels = sprintf("%.1f", y_ticks), las = 1)

stripchart(
  value ~ group,
  data = data,
  vertical = TRUE,
  method = "jitter",
  jitter = 0.12,
  pch = 16,
  cex = 0.6,
  col = rgb(0, 0, 0, 0.35),
  add = TRUE
)

dev.off()

