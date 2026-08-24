# Data

Static, read-only inputs that are committed to the repository.  Anything a
script *generates* belongs in `build/results/` (gitignored).

## Contents

- `reference/` – the CSVs a correct run of `make reproduce` must produce.
  `make check` diffs a fresh run against them, which is how a reader can tell
  reproduction from mere execution.  Refresh them deliberately (and say so in
  the commit message) when a parameter or a bug fix changes the numbers:

  ```bash
  make reproduce && cp build/results/*.csv reproduction/data/reference/
  ```

## Adding data

Put raw measurement data (hardware runs, digitised figures from other papers,
calibration snapshots) here, one directory per source, and document its
provenance – instrument, date, and how it was obtained – in this file.  Large
binary data belongs in an archive (e.g. Zenodo) referenced from here, not in
git.
