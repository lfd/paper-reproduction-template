# Simulation scripts

Scripts that produce the paper's numbers.  Each one writes CSV files to
`build/results/` and takes an `--outdir` so it can be run outside `make`.

- `example_zne.py` – the template's worked example: zero-noise extrapolation
  of a small Rx+ZZ circuit under depolarising noise.  Deterministic
  (`--seed`), runs in seconds, needs no credentials.
- `check_results.py` – compares a fresh run against the committed reference
  CSVs in `../data/reference/` (`make check`).
- `make_fallback.py` – renders the matplotlib fallback figure into
  `paper/plots_precompiled/`, so the paper also compiles without R.

Hardware scripts live in `../hardware/`; shared code lives in `../core/`.

## Usage

```bash
make reproduce                     # everything: results + figures
python reproduction/scripts/example_zne.py --outdir build/results
python reproduction/scripts/example_zne.py --noise thermal_relaxation --reps 200
make check                         # results still match the reference?
```

## Conventions worth keeping

- **Seed everything** that draws random numbers, and expose the seed on the
  command line.
- **Write CSV, not plots.** Plotting is R's job (`../R/`); a script that
  emits data can be re-analysed without re-running the experiment.
- **One row per observation** in the raw CSV, aggregates in a separate
  `*_summary.csv`.  Reviewers ask for the raw rows.
- **Print what you did** (parameters, intermediate values) so a log of the
  run is a record of the run.
