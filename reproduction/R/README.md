# R Plot Scripts

All R scripts source `config.R` for shared colours, layout constants, and
tikzDevice options (LuaLaTeX / IEEEtran, column width 8.85 cm).

## Scripts

- `config.R` — shared colour scheme, ggplot theme, tikzDevice settings.
- `plot_horoscope_extrapolation.R` — Richardson extrapolation failure-mode
  figure: E(λ) retention taxonomy + EQE1 hardware point.
  Reads `build/results/horoscope_circuits.csv` and
  `reproduction/data/qexa_hardware.csv`; writes `build/plots/horoscope_sweep.tex`.

## Adding a new figure

1. Create `plot_<name>.R` here.
2. Add `<name>` to `RAW_PLOTS` in the root `Makefile`.
3. Add a dependency rule pointing to the required CSV(s).
