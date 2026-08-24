#!/usr/bin/env python3
"""
Example experiment – zero-noise extrapolation under depolarising noise.
=======================================================================

This is the worked example of the reproduction template.  It is deliberately
small (seconds to run, no credentials, no hardware) but exercises every stage
a real experiment goes through:

    circuit  →  noise model  →  noise scaling (folding)  →  shot sampling
             →  extrapolation  →  paired statistics  →  CSV

Protocol
--------
  * Circuit:      ``core.circuits.build_example_circuit`` (Rx + ZZ layers),
                  observable ⟨Z⊗…⊗Z⟩.
  * Noise:        depolarising channel (``--noise`` selects others).
  * Noise scaling: gate-level unitary folding at λ ∈ ``--scales``.  The exact
                  noisy expectation E(λ) is computed once per λ by
                  density-matrix simulation; shot noise is then sampled
                  ``--reps`` times per λ, so a repetition is a *finite-sample
                  estimate*, not a re-simulation.
  * Mitigation:   linear and Richardson extrapolation of E(λ) to λ = 0.
  * Statistics:   paired comparison of |E − E_ideal| for raw vs. mitigated,
                  reporting effect size, p-values and the variance ratio.

Outputs (under ``--outdir``, default ``build/results/``)
  * ``example_zne.csv``          – one row per (rep, λ): sampled and exact E(λ).
  * ``example_zne_summary.csv``  – one row per method (raw, linear,
                                   richardson): bias, SE, statistics.

Everything is seeded (``--seed``), so a rerun reproduces the committed
reference results in ``reproduction/data/reference/`` – see ``make check``.

Usage
-----
  python reproduction/scripts/example_zne.py --outdir build/results
  python reproduction/scripts/example_zne.py --noise thermal_relaxation
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from qiskit import transpile

# ── path setup: import the shared library as `core.*` ──
SCRIPT_DIR = Path(__file__).resolve().parent          # reproduction/scripts/
REPRO_DIR = SCRIPT_DIR.parent                         # reproduction/
PROJECT_DIR = REPRO_DIR.parent                        # project root
sys.path.insert(0, str(REPRO_DIR))

from core.circuits import (                           # noqa: E402
    build_example_circuit,
    compute_ideal_expectation,
    compute_noisy_expectation,
    sample_shot_noise,
)
from core.noise import make_noise_model               # noqa: E402
from core.stats import paired_analysis                # noqa: E402
from core.zne import extrapolate, fold_circuit, sigma_ci  # noqa: E402

DEFAULT_OUTDIR = PROJECT_DIR / "build" / "results"
BASIS_GATES = ["rx", "ry", "rz", "sx", "sxdg", "x", "cx", "id"]


# ── experiment ───────────────────────────────────────────────────────────

def run(
    n_qubits: int,
    n_steps: int,
    scales: list[float],
    noise_type: str,
    p_1q: float,
    p_2q: float,
    n_reps: int,
    n_shots: int,
    seed: int,
) -> tuple[list[dict], list[dict]]:
    """Run the sweep and return (raw rows, summary rows)."""
    rng = np.random.default_rng(seed)
    noise_model = make_noise_model(noise_type, p_1q=p_1q, p_2q=p_2q)

    # Transpile once, *then* fold: folding a non-transpiled circuit would
    # amplify gates that the transpiler later rewrites.
    circuit = build_example_circuit(n_qubits=n_qubits, n_steps=n_steps)
    transpiled = transpile(
        circuit, basis_gates=BASIS_GATES, optimization_level=1,
    )
    ideal = compute_ideal_expectation(transpiled)

    # Exact noisy expectation per noise scale factor.
    exact: dict[float, float] = {}
    for lam in scales:
        folded = fold_circuit(transpiled, lam, strategy="from_left")
        exact[lam] = compute_noisy_expectation(folded, noise_model)
        print(
            f"  lambda = {lam:>4.1f}   depth = {folded.depth():>4d}   "
            f"E = {exact[lam]:+.4f}",
        )

    # Shot-noise repetitions + per-repetition extrapolation.
    rows: list[dict] = []
    per_method: dict[str, list[float]] = {"raw": [], "linear": [], "richardson": []}
    for rep in range(n_reps):
        sampled = {
            lam: sample_shot_noise(exact[lam], n_shots, rng) for lam in scales
        }
        for lam in scales:
            rows.append({
                "rep": rep,
                "lambda": lam,
                "e_sampled": sampled[lam],
                "e_exact": exact[lam],
                "e_ideal": ideal,
                "n_shots": n_shots,
                "noise_type": noise_type,
            })
        values = [sampled[lam] for lam in scales]
        per_method["raw"].append(sampled[scales[0]])
        per_method["linear"].append(extrapolate(scales, values, "linear"))
        per_method["richardson"].append(extrapolate(scales, values, "richardson"))

    # Summary: bias and spread per method, plus the paired comparison
    # against the unmitigated estimator.
    summary: list[dict] = []
    raw = np.asarray(per_method["raw"])
    for method, samples in per_method.items():
        arr = np.asarray(samples)
        # The raw estimator is the reference of the paired comparison, so its
        # own comparison columns stay empty.
        stats = (
            paired_analysis(raw, arr, ideal) if method != "raw"
            else {k: None for k in ("mean_improvement", "cohen_d",
                                    "p_value_t", "sigma_ratio", "frac_worse")}
        )
        summary.append({
            "method": method,
            "n": n_reps,
            "n_shots": n_shots,
            "noise_type": noise_type,
            "scales": ";".join(f"{s:g}" for s in scales),
            "sigma_ci": sigma_ci(scales),
            "e_ideal": ideal,
            "mean": float(arr.mean()),
            "se": float(arr.std(ddof=1) / np.sqrt(n_reps)),
            "bias": float(arr.mean() - ideal),
            "mean_abs_error": float(np.abs(arr - ideal).mean()),
            # vs. raw: positive improvement ⇒ closer to the ideal value
            "mean_improvement": stats["mean_improvement"],
            "cohen_d": stats["cohen_d"],
            "p_value_t": stats["p_value_t"],
            "sigma_ratio": stats["sigma_ratio"],
            "frac_worse": stats["frac_worse"],
        })
    return rows, summary


# ── CSV output ───────────────────────────────────────────────────────────

def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"  wrote {path}  ({len(rows)} rows)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR,
                        help="output directory for the CSV files")
    parser.add_argument("--qubits", type=int, default=4)
    parser.add_argument("--steps", type=int, default=1,
                        help="repetitions of the Rx+ZZ layer")
    parser.add_argument("--scales", type=float, nargs="+",
                        default=[1.0, 3.0, 5.0],
                        help="noise scale factors (first one is the raw run)")
    parser.add_argument("--noise", default="depolarizing",
                        choices=["depolarizing", "amplitude_damping",
                                 "thermal_relaxation"])
    parser.add_argument("--p1q", type=float, default=1e-3,
                        help="single-qubit gate error parameter")
    parser.add_argument("--p2q", type=float, default=1e-2,
                        help="two-qubit gate error parameter")
    parser.add_argument("--reps", type=int, default=50,
                        help="shot-noise repetitions per scale factor")
    parser.add_argument("--shots", type=int, default=4096)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print(f"Example ZNE experiment  ({args.noise} noise, "
          f"{args.reps} reps x {args.shots} shots)")
    rows, summary = run(
        n_qubits=args.qubits,
        n_steps=args.steps,
        scales=list(args.scales),
        noise_type=args.noise,
        p_1q=args.p1q,
        p_2q=args.p2q,
        n_reps=args.reps,
        n_shots=args.shots,
        seed=args.seed,
    )
    write_csv(args.outdir / "example_zne.csv", rows)
    write_csv(args.outdir / "example_zne_summary.csv", summary)

    for row in summary:
        d = "     -" if row["cohen_d"] is None else f"{row['cohen_d']:+.2f}"
        print(f"  {row['method']:>10s}:  mean = {row['mean']:+.4f}"
              f"  bias = {row['bias']:+.4f}"
              f"  SE = {row['se']:.4f}"
              f"  d = {d}")


if __name__ == "__main__":
    main()
