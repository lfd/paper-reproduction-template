"""
Shared library for the reproduction package.

Keeping experiment logic here (rather than in the scripts) means the
simulation scripts, the hardware scripts and the tests all exercise the
same code:

- ``circuits``  circuit construction + expectation-value helpers
- ``noise``     noise-model factory (depolarising, damping, thermal)
- ``zne``       zero-noise extrapolation: folding + extrapolation
- ``stats``     paired statistics (t/Wilcoxon, effect size, variance)
"""

from core.circuits import (
    build_example_circuit,
    compute_ideal_expectation,
    compute_noisy_expectation,
    compute_qasm_expectation,
    expectation_from_counts,
    sample_shot_noise,
)
from core.noise import make_noise_model, get_fake_backend
from core.zne import (
    fold_circuit,
    extrapolate,
    lagrange_coefficients,
    sigma_ci,
)
from core.stats import paired_analysis

__all__ = [
    "build_example_circuit",
    "compute_ideal_expectation",
    "compute_noisy_expectation",
    "compute_qasm_expectation",
    "expectation_from_counts",
    "sample_shot_noise",
    "make_noise_model",
    "get_fake_backend",
    "fold_circuit",
    "extrapolate",
    "lagrange_coefficients",
    "sigma_ci",
    "paired_analysis",
]
