# Data

Static input data committed to the repository — these files do **not** change
during reproduction and are read-only inputs to the plotting scripts.

## Files

- `qexa_hardware.csv` — raw Euro-Q-Exa (EQE1) measurement results used as the
  real-hardware data point in the extrapolation figure.
- `qexa_drift/` — multi-day EQE1 drift measurements (raw per-session CSVs).

## Adding new data

Put raw, read-only input data here.  Generated/derived data goes under
`build/results/` (produced by `make repro`, gitignored).
