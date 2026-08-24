#!/usr/bin/env Rscript
# =============================================================================
# Example figure – E(lambda) with linear and Richardson extrapolation
# =============================================================================
# Reads the CSVs written by reproduction/scripts/example_zne.py and draws the
# template's single figure: measured expectation values against the noise
# scale factor, the two extrapolations back to lambda = 0, and the ideal value.
#
# Input:  build/results/example_zne.csv, build/results/example_zne_summary.csv
# Output: build/plots/example_zne.tex   (TikZ, compiled by `make compile_plots`)
#
# Usage:  Rscript reproduction/R/plot_example_zne.R      (from the project root)
# =============================================================================

source("./reproduction/R/config.R")

raw_path     <- file.path("build", "results", "example_zne.csv")
summary_path <- file.path("build", "results", "example_zne_summary.csv")

for (p in c(raw_path, summary_path)) {
  if (!file.exists(p)) {
    stop("Missing: ", p,
         "\nRun: make reproduce  (or python reproduction/scripts/example_zne.py)")
  }
}

df      <- read_csv(raw_path, show_col_types = FALSE)
summary <- read_csv(summary_path, show_col_types = FALSE)

ideal <- df$e_ideal[1]

# ── Per-lambda mean +/- standard error over the shot-noise repetitions ──
points <- df %>%
  group_by(lambda) %>%
  summarise(
    mean = mean(e_sampled),
    se   = sd(e_sampled) / sqrt(n()),
    .groups = "drop"
  )

# ── Extrapolation lines: from the fitted zero-noise value through the data ──
zero_noise <- summary %>%
  filter(method != "raw") %>%
  transmute(
    method = recode(method, linear = "Linear", richardson = "Richardson"),
    mean, se
  )

fit_linear <- lm(mean ~ lambda, data = points)
lin_line <- tibble(
  lambda = c(0, max(points$lambda)),
  mean   = predict(fit_linear, newdata = tibble(lambda = c(0, max(points$lambda)))),
  method = "Linear"
)

# Richardson: the Lagrange polynomial through all points, drawn as a curve.
rich_fit <- lm(mean ~ poly(lambda, degree = nrow(points) - 1, raw = TRUE),
               data = points)
rich_grid <- tibble(lambda = seq(0, max(points$lambda), length.out = 100))
rich_line <- rich_grid %>%
  mutate(mean = predict(rich_fit, newdata = rich_grid), method = "Richardson")

lines <- bind_rows(lin_line, rich_line)

# ── Plot ──
g <- ggplot() +
  geom_hline(yintercept = ideal, linetype = "dashed",
             colour = PALETTE$grey, linewidth = 0.3) +
  annotate("text", x = 2.2, y = ideal, vjust = 1.4, hjust = 0,
           size = SMALL.SIZE / .pt, colour = PALETTE$grey,
           label = "ideal") +
  geom_line(data = lines, aes(lambda, mean, colour = method, linetype = method),
            linewidth = LINE.SIZE * 0.4) +
  geom_point(data = zero_noise, aes(0, mean, colour = method, shape = method),
             size = SYM.SIZE) +
  geom_errorbar(data = zero_noise,
                aes(x = 0, ymin = mean - se, ymax = mean + se, colour = method),
                width = 0.15, linewidth = 0.3) +
  geom_errorbar(data = points,
                aes(x = lambda, ymin = mean - se, ymax = mean + se),
                width = 0.15, linewidth = 0.3, colour = PALETTE$black) +
  geom_point(data = points, aes(lambda, mean), colour = PALETTE$black,
             size = SYM.SIZE * 0.8) +
  scale_colour_manual(values = c(Linear = PALETTE$blue,
                                 Richardson = PALETTE$orange), name = NULL) +
  scale_linetype_manual(values = c(Linear = "solid",
                                   Richardson = "longdash"), name = NULL) +
  scale_shape_manual(values = c(Linear = 16, Richardson = 17), name = NULL) +
  labs(
    x = "Noise scale factor $\\lambda$",
    y = "$\\langle Z^{\\otimes n} \\rangle$"
  ) +
  theme_paper() +
  shrink_legend()

save_plot(g, "example_zne", width = COLWIDTH, height = 0.62 * COLWIDTH)

cat("Wrote build/plots/example_zne.tex\n")
