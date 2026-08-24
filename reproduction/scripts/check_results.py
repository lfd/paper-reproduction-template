#!/usr/bin/env python3
"""
Reproducibility check – fresh results vs. committed reference.
=============================================================

Compares every CSV in a reference directory with the same file in a results
directory: identical schema, identical row count, and numeric columns equal
within a tolerance.  Non-numeric columns must match exactly.

This is what turns "the code runs" into "the code reproduces": a reader (or
CI) can tell whether a rerun on a different machine still yields the numbers
the paper reports.

Usage
-----
  python reproduction/scripts/check_results.py \
      --reference reproduction/data/reference --results build/results

  # accept larger deviations (e.g. across BLAS/simulator versions)
  python reproduction/scripts/check_results.py --rtol 1e-3 --atol 1e-6

Note on tolerances
------------------
The defaults absorb floating-point noise, not a change of environment.  A
different simulator or BLAS version can shift an expectation value in its last
bits, and where that value feeds a random draw (shot sampling), the drawn
sample changes discretely – so a failing check across *different* library
versions is expected and informative, not a bug.  Compare with the pinned
environment (``requirements.txt``, Docker or Nix) before concluding anything.

Exit status: 0 if all files match, 1 otherwise.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPRO_DIR = SCRIPT_DIR.parent
PROJECT_DIR = REPRO_DIR.parent


def read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


def as_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def compare_file(ref: Path, res: Path, rtol: float, atol: float) -> list[str]:
    """Return a list of human-readable differences (empty ⇒ files match)."""
    if not res.exists():
        return [f"missing result file {res}"]

    ref_cols, ref_rows = read_csv(ref)
    res_cols, res_rows = read_csv(res)

    if ref_cols != res_cols:
        return [f"schema differs:\n    reference: {ref_cols}\n    result:    {res_cols}"]
    if len(ref_cols) == 0:
        return ["reference file has no header"]
    if len(ref_rows) != len(res_rows):
        return [f"row count differs: {len(ref_rows)} (reference) "
                f"vs {len(res_rows)} (result)"]

    diffs: list[str] = []
    for i, (a, b) in enumerate(zip(ref_rows, res_rows)):
        for col in ref_cols:
            va, vb = a[col], b[col]
            fa, fb = as_float(va), as_float(vb)
            if fa is None or fb is None:
                if (va or "") != (vb or ""):
                    diffs.append(f"row {i}, column '{col}': "
                                 f"{va!r} != {vb!r}")
                continue
            if not math.isclose(fa, fb, rel_tol=rtol, abs_tol=atol):
                diffs.append(f"row {i}, column '{col}': "
                             f"{fa!r} != {fb!r} "
                             f"(delta = {abs(fa - fb):.3g})")
            if len(diffs) >= 10:
                diffs.append("... further differences suppressed")
                return diffs
    return diffs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--reference", type=Path,
                        default=REPRO_DIR / "data" / "reference",
                        help="directory with the committed reference CSVs")
    parser.add_argument("--results", type=Path,
                        default=PROJECT_DIR / "build" / "results",
                        help="directory with freshly generated CSVs")
    parser.add_argument("--rtol", type=float, default=1e-6,
                        help="relative tolerance for numeric columns")
    parser.add_argument("--atol", type=float, default=1e-9,
                        help="absolute tolerance for numeric columns")
    args = parser.parse_args()

    references = sorted(args.reference.glob("*.csv"))
    if not references:
        print(f"No reference CSVs in {args.reference} – nothing to check.")
        return 0

    failed = False
    for ref in references:
        res = args.results / ref.name
        diffs = compare_file(ref, res, args.rtol, args.atol)
        if diffs:
            failed = True
            print(f"FAIL  {ref.name}")
            for line in diffs:
                print(f"      {line}")
        else:
            print(f"OK    {ref.name}")

    if failed:
        print("\nResults deviate from the committed reference.\n"
              "If the change is intended (new parameters, fixed bug), refresh\n"
              "the reference with:  cp build/results/*.csv "
              f"{args.reference.relative_to(PROJECT_DIR) if args.reference.is_relative_to(PROJECT_DIR) else args.reference}/")
        return 1

    print("\nAll results match the committed reference.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
