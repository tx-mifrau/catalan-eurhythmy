#!/usr/bin/env Rscript

# Purpose:
#     Compare proportions of inter-stress intervals of two or three syllables
#     across human translations, machine translations, and original Catalan
#     prose.
# Input:
#     Two tab-separated H1 summary files (.tsv) with decimal commas, one for
#     paired translations and one for original Catalan prose.
#
# Output:
#     One PNG image (.png) containing one set of boxplots with individual text
#     values.

# Boxplots for prop_intervals_2_or_3 across HT, MT, CA
# - HT first (blue), MT second (green), CA third (orange)
# - Y axis based on observed range, rounded to 0.05
# - Y-axis labels every 0.05
# - Boxplot outlier symbols hidden
# - Individual points shown with jitter

# Run from the project root.
results_dir <- file.path("data", "results")
input_ht_mt <- file.path(results_dir, "hypothesis1", "H1_summary_all_texts.tsv")
input_ca <- file.path(results_dir, "hypothesis1_onlyCA", "H1_summary_all_texts_onlyCA.tsv")
output_png <- file.path(results_dir, "plots", "generated", "boxplots_H1_prop_intervals_2_or_3.png")

dir.create(dirname(output_png), recursive = TRUE, showWarnings = FALSE)

# Read input files
ht_mt <- read.delim(input_ht_mt, sep = "\t", dec = ",", stringsAsFactors = FALSE)
ca    <- read.delim(input_ca,    sep = "\t", dec = ",", stringsAsFactors = FALSE)

# In this file, the column named CA_prop_intervals_2_or_3 actually represents HT
ht_values <- ht_mt$CA_prop_intervals_2_or_3
mt_values <- ht_mt$TA_prop_intervals_2_or_3
ca_values <- ca$prop_intervals_2_or_3

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

# Observed range
raw_lim <- range(data$value, na.rm = TRUE)

# Small padding
y_pad <- 0.03 * diff(raw_lim)
if (y_pad == 0) y_pad <- 0.01

# Round limits to nearest 0.05 so axis ticks align cleanly
y_min <- floor((raw_lim[1] - y_pad) / 0.05) * 0.05
y_max <- ceiling((raw_lim[2] + y_pad) / 0.05) * 0.05
y_lim <- c(y_min, y_max)

# Define Y-axis ticks every 0.05 within plotted range
y_ticks <- seq(y_min, y_max, by = 0.05)

# Save PNG
png(output_png, width = 1000, height = 700, res = 120)

# Wider left margin for more axis labels
par(mar = c(5.5, 6.8, 4.5, 2) + 0.1)

boxplot(
  value ~ group,
  data = data,
  main = "Proportion of intervals 2-3 across corpus components",
  xlab = "Corpus component",
  ylab = "Proportion of intervals 2-3",
  col = c("#8DA0CB", "#66C2A5", "#FC8D62"),
  border = "#333333",
  outline = FALSE,
  ylim = y_lim,
  yaxt = "n"
)

axis(
  2,
  at = y_ticks,
  labels = sprintf("%.2f", y_ticks),
  las = 1,
  cex.axis = 0.85
)

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

# Show the plot in RStudio (Plots pane) when running interactively
if (interactive()) {
  par(mar = c(5.5, 6.8, 4.5, 2) + 0.1)
  
  boxplot(
    value ~ group,
    data = data,
    main = "Proportion of intervals 2-3 across corpus components",
    xlab = "Corpus component",
    ylab = "Proportion of intervals 2-3",
    col = c("#8DA0CB", "#66C2A5", "#FC8D62"),
    border = "#333333",
    outline = FALSE,
    ylim = y_lim,
    yaxt = "n"
  )
  
  axis(
    2,
    at = y_ticks,
    labels = sprintf("%.2f", y_ticks),
    las = 1,
    cex.axis = 0.85
  )
  
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
}

