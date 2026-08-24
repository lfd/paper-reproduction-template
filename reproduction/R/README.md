# R plotting scripts

All scripts `source("./reproduction/R/config.R")` for the shared palette,
ggplot theme and tikzDevice settings (LuaLaTeX, IEEEtran, column width
8.85 cm), and are run from the **project root**.

## Scripts

- `config.R` – palette, `theme_paper()`, `save_plot()`, layout constants.
- `plot_example_zne.R` – the example figure: E(λ) with linear and Richardson
  extrapolation.  Reads `build/results/example_zne*.csv`, writes
  `build/plots/example_zne.tex`.

Figures are emitted as TikZ, not PDF: `make compile_plots` compiles them via
`../gen_img.sh` so text in figures uses the paper's own fonts and maths.

## Adding a figure

1. Create `plot_<name>.R` here, ending in
   `save_plot(g, "<name>", width = COLWIDTH)`.
2. Add `<name>` to `RAW_PLOTS` in the root `Makefile`.
3. Add a dependency rule from the CSV(s) the script reads.
4. Include it in `paper/main.tex` with `\includetikz[width=\columnwidth]{<name>}`.
