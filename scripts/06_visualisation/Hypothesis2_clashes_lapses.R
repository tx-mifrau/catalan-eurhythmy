#!/usr/bin/env Rscript

# Purpose:
#     Compare proportions of stress clashes and stress lapses across human
#     translations, machine translations, and original Catalan prose.
# Input:
#     Two tab-separated H2NEW summary files (.tsv) with decimal commas, one
#     for paired translations and one for original Catalan prose.
#
# Output:
#     One PNG image (.png) containing two sets of boxplots, one for each
#     measure.

# H2NEW: Compare stress-to-stress clash and lapse proportions across HT, MT, CA

# Run from the project root.
results_dir <- file.path("data", "results")
input_ht_mt <- file.path(results_dir, "hypothesis2", "H2_summary_all_texts.tsv")
input_ca <- file.path(results_dir, "hypothesis2_onlyCA", "H2_summary_all_texts_onlyCA.tsv")
output_png <- file.path(results_dir, "plots", "generated", "boxplots_H2_intervals_eq1_ge4.png")

dir.create(dirname(output_png), recursive = TRUE, showWarnings = FALSE)

ht_mt <- read.delim(input_ht_mt, sep = "\t", dec = ",", stringsAsFactors = FALSE)
ca    <- read.delim(input_ca,    sep = "\t", dec = ",", stringsAsFactors = FALSE)

# HT and MT from the paired H2NEW file.
ht_eq1 <- ht_mt$CA_prop_intervals_eq_1
mt_eq1 <- ht_mt$TA_prop_intervals_eq_1
ht_ge4 <- ht_mt$CA_prop_intervals_ge_4
mt_ge4 <- ht_mt$TA_prop_intervals_ge_4

# CA from the onlyCA H2NEW file.
ca_eq1 <- ca$prop_intervals_eq_1
ca_ge4 <- ca$prop_intervals_ge_4

make_data <- function(ht_values, mt_values, ca_values) {
  data <- data.frame(
    group = c(
      rep("HT", length(ht_values)),
      rep("MT", length(mt_values)),
      rep("CA", length(ca_values))
    ),
    value = c(ht_values, mt_values, ca_values)
  )
  data <- data[!is.na(data$value), ]
  data$group <- factor(data$group, levels = c("HT", "MT", "CA"))
  data
}

plot_box <- function(data, title, ylab_text, y_lim, y_ticks) {
  boxplot(
    value ~ group,
    data = data,
    main = title,
    xlab = "Corpus component",
    ylab = ylab_text,
    col = c("#8DA0CB", "#66C2A5", "#FC8D62"),
    border = "#333333",
    outline = FALSE,
    ylim = y_lim,
    yaxt = "n",
    cex.main = 0.9
  )
  axis(2, at = y_ticks, labels = sprintf("%.2f", y_ticks), las = 1)
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

data_eq1 <- make_data(ht_eq1, mt_eq1, ca_eq1)
data_ge4 <- make_data(ht_ge4, mt_ge4, ca_ge4)

title_eq1 <- "Proportion of clash intervals across corpus components"
title_ge4 <- "Proportion of lapse intervals across corpus components"

# Shared Y-axis range across both plots.
all_values <- c(data_eq1$value, data_ge4$value)
y_lim <- range(all_values, na.rm = TRUE)
y_pad <- 0.03 * diff(y_lim)
if (y_pad == 0) y_pad <- 0.01
y_lim <- c(y_lim[1] - y_pad, y_lim[2] + y_pad)

y_ticks <- pretty(y_lim, n = 6)

png(output_png, width = 1400, height = 700, res = 120)
par(mfrow = c(1, 2), mar = c(5, 4, 4, 1))
plot_box(data_eq1, title_eq1, "Proportion of intervals = 1", y_lim, y_ticks)
plot_box(data_ge4, title_ge4, "Proportion of intervals >= 4", y_lim, y_ticks)
dev.off()

if (interactive()) {
  par(mfrow = c(1, 2), mar = c(5, 4, 4, 1))
  plot_box(data_eq1, title_eq1, "Proportion of intervals = 1", y_lim, y_ticks)
  plot_box(data_ge4, title_ge4, "Proportion of intervals >= 4", y_lim, y_ticks)
}

