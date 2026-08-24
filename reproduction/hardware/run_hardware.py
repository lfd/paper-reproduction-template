#!/usr/bin/env python3
"""
Example hardware run – the same experiment on a QPU.
====================================================

Hardware runs differ from simulation in ways that a reproduction package has
to handle explicitly, and this script shows the four patterns worth copying:

  1. **Credentials from the environment** (never from the source): a token is
     read from the process environment or from ``reproduction/.env``.
  2. **Crash resumption**: results are appended row-by-row and completed
     (rep, lambda) pairs are skipped, so an interrupted run continues where it
     stopped instead of starting over.
  3. **Retry with backoff**: queue and network failures are expected, not
     exceptional.
  4. **Provenance**: backend name, timestamp, shot count and the raw counts of
     every submission are written to the CSV, so the analysis can be redone
     offline without re-running the QPU.

The workload is the same example circuit as ``scripts/example_zne.py``, so the
hardware and simulation branches are directly comparable.

Backends
--------
  --backend local   Aer with a depolarising model – smoke test, no credentials
  --backend ibm     IBM Quantum via qiskit-ibm-runtime (IBM_QUANTUM_TOKEN)
  --backend mqss    IQM machines at LRZ via the MQSS adapter (MQSS_TOKEN)

Usage
-----
  # verify the pipeline without touching a QPU:
  python reproduction/hardware/run_hardware.py --backend local

  # real run (deploy inside tmux – QPU queues are long):
  python reproduction/hardware/run_hardware.py --backend ibm --reps 10

  # resume after an interruption: same command, same --outdir
  python reproduction/hardware/run_hardware.py --backend ibm --reps 10

Output (under ``--outdir``, default ``build/results/``)
  ``hardware_<backend>.csv`` – one row per (rep, lambda) with counts.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from qiskit import transpile

# ── path setup ──
SCRIPT_DIR = Path(__file__).resolve().parent      # reproduction/hardware/
REPRO_DIR = SCRIPT_DIR.parent                     # reproduction/
PROJECT_DIR = REPRO_DIR.parent                    # project root
sys.path.insert(0, str(REPRO_DIR))

from core.circuits import (                       # noqa: E402
    build_example_circuit,
    compute_ideal_expectation,
    expectation_from_counts,
)
from core.zne import fold_circuit                 # noqa: E402

DEFAULT_OUTDIR = PROJECT_DIR / "build" / "results"
LOGS_DIR = REPRO_DIR / "logs"

SCALE_FACTORS = [1.0, 3.0, 5.0]
MAX_RETRIES = 5
RETRY_BASE_DELAY_S = 30

log = logging.getLogger("hardware")


# ── logging ──────────────────────────────────────────────────────────────

def setup_logging(name: str = "hardware") -> None:
    """Log to stdout *and* to reproduction/logs/ – a hardware run that is not
    logged cannot be audited afterwards.

    Only this logger is configured (not the root logger), so Qiskit's own
    INFO chatter stays out of the run log.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter("%(asctime)s  %(levelname)-7s %(message)s")
    for handler in (logging.FileHandler(LOGS_DIR / f"{name}.log"),
                    logging.StreamHandler(sys.stdout)):
        handler.setFormatter(formatter)
        log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False


# ── credentials ──────────────────────────────────────────────────────────

def read_token(var: str) -> str:
    """Read *var* from the environment, falling back to ``reproduction/.env``.

    Tokens must never be committed: ``.env`` is gitignored, ``.env.example``
    documents the required variables.
    """
    token = os.environ.get(var)
    if not token:
        env_file = REPRO_DIR / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith(f"{var}="):
                    token = line.split("=", 1)[1].strip().strip("'\"")
                    break
    if not token:
        raise RuntimeError(
            f"{var} not found.  Set it in the environment or add {var}=... "
            f"to reproduction/.env (copy .env.example; never commit the token).",
        )
    return token


# ── backends ─────────────────────────────────────────────────────────────

def get_backend(kind: str, name: str | None):
    """Return (backend, backend_name).  ``backend`` is None for ``local``."""
    if kind == "local":
        return None, "aer_depolarizing"

    if kind == "ibm":
        from qiskit_ibm_runtime import QiskitRuntimeService

        service = QiskitRuntimeService(
            channel=os.environ.get("IBM_QUANTUM_CHANNEL",
                                   "ibm_quantum_platform"),
            token=read_token("IBM_QUANTUM_TOKEN"),
            instance=os.environ.get("IBM_QUANTUM_INSTANCE") or None,
        )
        backend = (service.backend(name) if name
                   else service.least_busy(operational=True, simulator=False))
        log.info(f"Connected to IBM backend {backend.name}")
        return backend, backend.name

    if kind == "mqss":
        # LRZ Munich Quantum Software Stack (e.g. the IQM Euro-Q-Exa machine).
        from mqss.qiskit_adapter import MQSSQiskitAdapter

        adapter = MQSSQiskitAdapter(token=read_token("MQSS_TOKEN"))
        backend_name = name or "EQE1"
        backend = adapter.get_backend(backend_name)
        log.info(f"Connected to MQSS backend {backend_name}")
        return backend, backend_name

    raise ValueError(f"Unknown backend kind '{kind}'")


# ── circuits ─────────────────────────────────────────────────────────────

def prepare_circuits(backend, n_qubits: int, n_steps: int) -> tuple[dict, float]:
    """Transpile the example circuit, then fold it at each scale factor."""
    base = build_example_circuit(n_qubits=n_qubits, n_steps=n_steps)
    ideal = compute_ideal_expectation(base)
    log.info(f"Ideal <Z^{n_qubits}> = {ideal:+.6f}")

    if backend is not None:
        transpiled = transpile(base, backend=backend, optimization_level=1)
    else:
        transpiled = transpile(
            base, optimization_level=1,
            basis_gates=["rx", "rz", "sx", "sxdg", "x", "cx", "id"],
        )

    circuits = {}
    for lam in SCALE_FACTORS:
        folded = fold_circuit(transpiled, lam, strategy="from_left")
        folded.measure_all()
        circuits[lam] = folded
        log.info(f"  lambda = {lam:>4.1f}: depth {folded.depth():>4d}, "
                 f"{sum(folded.count_ops().values()):>4d} ops")
    return circuits, ideal


# ── resumable collection ─────────────────────────────────────────────────

def completed_pairs(path: Path) -> set[tuple[int, float]]:
    if not path.exists() or path.stat().st_size == 0:
        return set()
    with path.open() as fh:
        return {(int(r["rep"]), float(r["scale_factor"]))
                for r in csv.DictReader(fh)}


def append_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    is_new = not path.exists() or path.stat().st_size == 0
    with path.open("a", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        if is_new:
            writer.writeheader()
        writer.writerows(rows)


def run_batch(backend, circuits: list, n_shots: int, sim=None, seed: int = 0):
    """Submit a batch of circuits, retrying transient failures."""
    if backend is None:
        return sim.run(circuits, shots=n_shots, seed_simulator=seed).result()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log.info(f"  submitting {len(circuits)} circuits "
                     f"(attempt {attempt}/{MAX_RETRIES}) ...")
            job = backend.run(circuits, shots=n_shots)
            log.info(f"  job id: {job.job_id()}")
            return job.result()
        except Exception as exc:  # noqa: BLE001 – QPU/network faults are expected
            log.warning(f"  attempt {attempt} failed: {exc}")
            if attempt == MAX_RETRIES:
                raise
            delay = RETRY_BASE_DELAY_S * 2 ** (attempt - 1)
            log.info(f"  retrying in {delay}s ...")
            time.sleep(delay)


def collect(
    circuits: dict,
    ideal: float,
    backend,
    backend_name: str,
    n_reps: int,
    n_shots: int,
    out_path: Path,
    seed: int,
) -> None:
    done = completed_pairs(out_path)
    if done:
        log.info(f"Resuming: {len(done)} (rep, lambda) rows already collected.")

    sim = None
    if backend is None:
        from qiskit_aer import AerSimulator

        from core.noise import make_noise_model
        sim = AerSimulator(
            noise_model=make_noise_model("depolarizing", p_1q=1e-3, p_2q=1e-2),
        )

    for rep in range(n_reps):
        todo = [lam for lam in SCALE_FACTORS if (rep, lam) not in done]
        if not todo:
            continue
        batch = [circuits[lam] for lam in todo]
        timestamp = datetime.now(timezone.utc).isoformat()
        result = run_batch(backend, batch, n_shots, sim=sim, seed=seed + rep)

        rows = []
        for j, lam in enumerate(todo):
            counts = result.get_counts(j) if len(todo) > 1 else result.get_counts()
            rows.append({
                "backend": backend_name,
                "rep": rep,
                "scale_factor": lam,
                "exp_val": f"{expectation_from_counts(counts):.6f}",
                "ideal": f"{ideal:.6f}",
                "n_shots": n_shots,
                "timestamp": timestamp,
                "counts": json.dumps(counts),
            })
        append_rows(out_path, rows)
        summary = "  ".join(
            f"E({r['scale_factor']:g}) = {float(r['exp_val']):+.4f}" for r in rows
        )
        log.info(f"  [rep {rep + 1:>3d}/{n_reps}]  {summary}")

    log.info(f"Collection complete: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--backend", default="local",
                        choices=["local", "ibm", "mqss"])
    parser.add_argument("--backend-name", default=None,
                        help="specific device (default: least busy / EQE1)")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--qubits", type=int, default=4)
    parser.add_argument("--steps", type=int, default=1)
    parser.add_argument("--reps", type=int, default=10)
    parser.add_argument("--shots", type=int, default=4096)
    parser.add_argument("--seed", type=int, default=42,
                        help="seed for --backend local")
    args = parser.parse_args()

    setup_logging()
    backend, backend_name = get_backend(args.backend, args.backend_name)
    circuits, ideal = prepare_circuits(backend, args.qubits, args.steps)
    out_path = args.outdir / f"hardware_{args.backend}.csv"
    collect(
        circuits, ideal, backend, backend_name,
        n_reps=args.reps, n_shots=args.shots, out_path=out_path, seed=args.seed,
    )


if __name__ == "__main__":
    main()
