#!/usr/bin/env python3
"""
Fallback renderer for the example figure.
========================================

The *canonical* figure comes from the R/tikzDevice pipeline
(``reproduction/R/plot_example_zne.R`` → ``build/plots/example_zne.tex``,
compiled by ``make reproduce``).  That toolchain needs R with tidyverse and
tikzDevice, which not every reader has installed.

This script renders an equivalent matplotlib version into
``paper/plots_precompiled/``, which the paper's ``\\includetikz`` macro uses
whenever ``build/plots/example_zne.tex`` is absent.  The committed fallback is
what makes ``make`` work in a bare LaTeX-only environment.

Input :  build/results/example_zne.csv, build/results/example_zne_summary.csv
Output:  paper/plots_precompiled/example_zne.pdf

Usage :  make fallback     (or: python reproduction/scripts/make_fallback.py)
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
REPRO_DIR = SCRIPT_DIR.parent
PROJECT_DIR = REPRO_DIR.parent

RAW_CSV = PROJECT_DIR / "build" / "results" / "example_zne.csv"
SUMMARY_CSV = PROJECT_DIR / "build" / "results" / "example_zne_summary.csv"
OUT_PDF = PROJECT_DIR / "paper" / "plots_precompiled" / "example_zne.pdf"

# Same palette as reproduction/R/config.R
PALETTE = dict(black="#000000", orange="#E69F00", grey="#999999",
               teal="#009371", red="#ED665A", blue="#1F78B4",
               purple="#BEAED4")

# IEEEtran single-column width in inches
COLWIDTH = 8.85553 / 2.54


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(
            f"Missing {path}.\nRun: python reproduction/scripts/example_zne.py",
        )
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def main() -> None:
    rows = read_rows(RAW_CSV)
    summary = read_rows(SUMMARY_CSV)

    ideal = float(rows[0]["e_ideal"])

    by_lambda: dict[float, list[float]] = defaultdict(list)
    for row in rows:
        by_lambda[float(row["lambda"])].append(float(row["e_sampled"]))
    lambdas = np.array(sorted(by_lambda))
    means = np.array([np.mean(by_lambda[lam]) for lam in lambdas])
    ses = np.array([
        np.std(by_lambda[lam], ddof=1) / np.sqrt(len(by_lambda[lam]))
        for lam in lambdas
    ])

    zero_noise = {
        row["method"]: (float(row["mean"]), float(row["se"]))
        for row in summary if row["method"] != "raw"
    }

    fig, ax = plt.subplots(figsize=(COLWIDTH, 0.62 * COLWIDTH))

    ax.axhline(ideal, ls="--", lw=0.6, color=PALETTE["grey"])
    ax.text(2.2, ideal, "ideal", va="top", ha="left", fontsize=7,
            color=PALETTE["grey"])

    # Linear fit through the measured points, extended to lambda = 0.
    slope, intercept = np.polyfit(lambdas, means, 1)
    grid = np.linspace(0, lambdas.max(), 100)
    ax.plot(grid, slope * grid + intercept, lw=0.9, color=PALETTE["blue"],
            label="Linear")

    # Richardson: Lagrange polynomial through all points.
    poly = np.polyfit(lambdas, means, len(lambdas) - 1)
    ax.plot(grid, np.polyval(poly, grid), lw=0.9, ls="--",
            color=PALETTE["orange"], label="Richardson")

    ax.errorbar(lambdas, means, yerr=ses, fmt="o", ms=3, lw=0.8, capsize=2,
                color=PALETTE["black"], zorder=5)

    styles = {"linear": (PALETTE["blue"], "o"), "richardson": (PALETTE["orange"], "^")}
    for method, (mean, se) in zero_noise.items():
        colour, marker = styles.get(method, (PALETTE["teal"], "s"))
        ax.errorbar([0], [mean], yerr=[se], fmt=marker, ms=4, lw=0.8,
                    capsize=2, color=colour, zorder=6)

    ax.set_xlabel(r"Noise scale factor $\lambda$", fontsize=9)
    ax.set_ylabel(r"$\langle Z^{\otimes n} \rangle$", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.legend(fontsize=7, frameon=False, loc="lower left")
    ax.grid(True, lw=0.3, color="#DDDDDD")
    fig.tight_layout(pad=0.2)

    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PDF)
    print(f"  wrote {OUT_PDF}")


if __name__ == "__main__":
    main()
