"""
Circuit helpers.
================

A small parameterised example circuit plus ideal-, noisy- and shot-based
expectation-value helpers for the observable Z⊗…⊗Z.

Replace ``build_example_circuit`` with the circuits of your own paper; the
expectation helpers below are generic and can usually be kept as they are.
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator


# ── circuit construction ─────────────────────────────────────────────────

def build_example_circuit(
    n_qubits: int = 4,
    n_steps: int = 1,
    theta_x: float = 0.35,
    theta_zz: float = 0.55,
) -> QuantumCircuit:
    """A layered Rx + ZZ circuit – the example workload of this template.

    One step applies ``Rx(theta_x)`` to every qubit, followed by
    ``CX-Rz(theta_zz)-CX`` on the even and then the odd nearest-neighbour
    pairs.  This is a generic Trotter-like layer: shallow, entangling, and
    with a non-trivial ⟨Z⊗…⊗Z⟩ that a noise model visibly degrades.

    No measurements are appended – folding (``core.zne.fold_circuit``) and
    measurement are applied by the caller.

    Parameters
    ----------
    n_qubits : int
        Number of qubits (≥ 2).
    n_steps : int
        Number of repetitions of the layer.
    theta_x : float
        Rx rotation angle.
    theta_zz : float
        Rz angle inside the ZZ interaction.
    """
    if n_qubits < 2:
        raise ValueError("n_qubits must be >= 2")

    qc = QuantumCircuit(n_qubits, name="example")
    for _ in range(n_steps):
        for q in range(n_qubits):
            qc.rx(theta_x, q)
        for offset in (0, 1):
            for q in range(offset, n_qubits - 1, 2):
                qc.cx(q, q + 1)
                qc.rz(theta_zz, q + 1)
                qc.cx(q, q + 1)
    return qc


# ── expectation values ───────────────────────────────────────────────────

def _zn_signs(n_qubits: int) -> np.ndarray:
    """(-1)^popcount(x) for x = 0 … 2^n − 1.

    Used to compute ⟨Z⊗…⊗Z⟩ = Σ_x  sign(x) · P(x).
    """
    n_states = 1 << n_qubits
    return np.array(
        [(-1) ** bin(x).count("1") for x in range(n_states)], dtype=float,
    )


def compute_ideal_expectation(circuit: QuantumCircuit) -> float:
    """⟨Z⊗…⊗Z⟩ via noiseless statevector simulation.

    The circuit is run starting from |0…0⟩.
    """
    qc = circuit.copy()
    qc.save_statevector()
    sim = AerSimulator(method="statevector")
    tc = transpile(qc, sim, optimization_level=0)
    result = sim.run(tc).result()
    sv = np.asarray(result.data()["statevector"])
    probs = np.abs(sv) ** 2
    signs = _zn_signs(circuit.num_qubits)
    return float(signs @ probs)


def compute_noisy_expectation(
    circuit: QuantumCircuit,
    noise_model,
) -> float:
    """⟨Z⊗…⊗Z⟩ via density-matrix simulation under *noise_model*.

    No shot noise – returns the exact noisy expectation.
    The circuit should already be in the simulator's basis gates.
    """
    qc = circuit.copy()
    qc.save_density_matrix()
    sim = AerSimulator(method="density_matrix", noise_model=noise_model)
    # optimization_level=0: do NOT re-optimise (would undo folding)
    tc = transpile(qc, sim, optimization_level=0)
    result = sim.run(tc).result()
    dm = np.asarray(result.data()["density_matrix"])
    diag = np.real(np.diag(dm))
    signs = _zn_signs(circuit.num_qubits)
    return float(signs @ diag)


def sample_shot_noise(
    exact_expectation: float,
    n_shots: int,
    rng: np.random.Generator,
) -> float:
    """Simulate shot noise for a ⟨Z⊗…⊗Z⟩ measurement.

    The observable is diagonal in the computational basis, so a
    measurement yields +1 (even parity) or −1 (odd parity).
    The probability of even parity is  P_even = (1 + ⟨ZZ…Z⟩) / 2.
    We draw  n_even ~ Binomial(n_shots, P_even)  and return
    ⟨ZZ…Z⟩_shot = 2 n_even / n_shots − 1.
    """
    p_even = np.clip((1.0 + exact_expectation) / 2.0, 0.0, 1.0)
    n_even = rng.binomial(n_shots, p_even)
    return 2.0 * n_even / n_shots - 1.0


# ── QASM shot-based simulation ──────────────────────────────────────────

def compute_qasm_expectation(
    circuit: QuantumCircuit,
    n_shots: int,
    noise_model=None,
    seed: int = 42,
) -> float:
    """Compute ⟨Z⊗…⊗Z⟩ via shot-based QASM simulation.

    Unlike ``compute_noisy_expectation`` (which returns the *exact* noisy
    expectation via density matrix), this function performs actual
    measurement sampling – matching the behaviour of IBM's QASM Simulator.

    The circuit should already be transpiled and folded.  Only
    measurements are appended; no further gate optimisation is performed.

    Parameters
    ----------
    circuit : QuantumCircuit
        Transpiled + folded circuit (**no** measurements).
    n_shots : int
        Number of measurement shots.
    noise_model : NoiseModel or None
        If None, performs ideal (noiseless) simulation.
    seed : int
        Random seed for shot-noise reproducibility.

    Returns
    -------
    float
        Shot-estimated ⟨Z⊗…⊗Z⟩.
    """
    qc = circuit.copy()
    qc.measure_all()

    kw = {"noise_model": noise_model} if noise_model else {}
    sim = AerSimulator(**kw)

    # optimization_level = 0: preserve the folded gate structure
    tc = transpile(qc, sim, optimization_level=0)
    result = sim.run(tc, shots=n_shots, seed_simulator=seed).result()
    counts = result.get_counts()

    return expectation_from_counts(counts)


def expectation_from_counts(counts: dict) -> float:
    """Compute ⟨Z⊗…⊗Z⟩ from measurement bit-string counts.

    Z⊗…⊗Z has eigenvalue (−1)^{popcount(x)} for basis state |x⟩.
    """
    total = 0
    exp_val = 0.0
    for bitstring, count in counts.items():
        bs = bitstring.replace(" ", "")
        parity = (-1) ** bs.count("1")
        exp_val += parity * count
        total += count
    return exp_val / total
