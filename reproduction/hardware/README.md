# Hardware scripts

Scripts that submit circuits to real quantum hardware.  They are **not** part
of `make reproduce`: they need credentials, they cost queue time, and their
results depend on the state of the device on the day.

- `run_hardware.py` – the example experiment on a QPU, with
  `--backend {local,ibm,mqss}`.  `--backend local` runs the identical code
  path against a noisy simulator, so the pipeline can be tested without
  credentials.

## Credentials

Copy `../.env.example` to `../.env` and fill in your tokens.  `.env` is
gitignored – **never commit credentials**.

```bash
export $(grep -v '^#' reproduction/.env | xargs)
python reproduction/hardware/run_hardware.py --backend ibm --reps 10
```

## Patterns to copy for your own hardware runs

1. **Resume, do not restart.** Append each result immediately and skip
   already-collected work on startup; QPU jobs fail mid-run.
2. **Retry with backoff.** Treat queue and network errors as normal.
3. **Store raw counts.** Keep the per-shot bitstring counts in the CSV so the
   analysis can be redone offline, and re-analysis needs no QPU access.
4. **Log to a file.** `reproduction/logs/` keeps the run log next to the code
   (gitignored – copy the interesting parts into the paper's data package).
5. **Long runs belong in tmux**, not in an interactive shell.
