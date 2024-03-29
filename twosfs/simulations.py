"""Helper functions for running msprime simulations."""
from hashlib import blake2b
from typing import Iterable, Union

import msprime
import numpy as np
from scipy.special import betaln

from twosfs.demography import (
    expected_t2_demography,
    make_exp_demography,
    make_pwc_demography,
)
from twosfs.spectra import Spectra, add_spectra, spectra_from_TreeSequence


def list_rounded_parameters(params: Iterable[float], ndigits: int = 2) -> list[float]:
    """Round each parameter in params to ndigits places and return a list."""
    return list(map(lambda x: round(x, ndigits), params))


def _dispatch_model(
    model: str, model_parameters: dict
) -> tuple[msprime.AncestryModel, msprime.Demography, float]:
    if model == "const":
        coal_model = msprime.StandardCoalescent()
        demography = make_pwc_demography([1.0], [])
        t2 = expected_t2_demography(demography)
    elif model == "exp":
        coal_model = msprime.StandardCoalescent()
        demography = make_exp_demography(
            end_time=model_parameters["end_time"],
            growth_rate=model_parameters["growth_rate"],
        )
        t2 = expected_t2_demography(demography)
    elif model == "pwc":
        coal_model = msprime.StandardCoalescent()
        demography = make_pwc_demography(
            sizes=model_parameters["sizes"],
            times=model_parameters["times"],
        )
        t2 = expected_t2_demography(demography)
    elif model == "beta":
        coal_model = msprime.BetaCoalescent(alpha=model_parameters["alpha"])
        demography = None
        t2 = expected_t2_beta(alpha=model_parameters["alpha"])
    else:
        raise ValueError("Invalid model {model}. Must be const, exp, pwc, or beta.")
    return coal_model, demography, t2


def simulate_spectra(
    model: str,
    model_parameters: dict,
    msprime_parameters: dict,
    scaled_recombination_rate: float,
    random_seed: Union[int, np.random.Generator],
) -> Spectra:
    """Simulate spectra using msprime coalescent simulations."""
    if isinstance(random_seed, int):
        seed = random_seed
    elif isinstance(random_seed, np.random.Generator):
        seed = random_seed.integers(2 ** 32)
    else:
        raise ValueError("random_seed must be an int or a numpy.random.Generator")
    coal_model, demography, t2 = _dispatch_model(model, model_parameters)
    r = scaled_recombination_rate / (2 * t2)
    sims = msprime.sim_ancestry(
        model=coal_model,
        demography=demography,
        recombination_rate=r,
        random_seed=seed,
        **msprime_parameters,
    )
    windows = np.arange(msprime_parameters["sequence_length"] + 1)
    return add_spectra(spectra_from_TreeSequence(windows, r, tseq) for tseq in sims)


def expected_t2_beta(alpha, pop_size=1.0):
    """Compute the mean coalescent time of the diploid beta coalescent."""
    m = 2 + np.exp(alpha * np.log(2) - (alpha - 1) * np.log(3) - np.log(alpha - 1))
    return np.exp(
        np.log(4)
        + alpha * np.log(m)
        + (alpha - 1) * np.log(pop_size / 2)
        - np.log(alpha)
        - betaln(2 - alpha, alpha)
    )


def sims2pi(sims, num_replicates):
    """Compute pairwise diversity for a generator of tree sequences."""
    pi = sum(tseq.diversity(mode="branch") for tseq in sims)
    pi /= num_replicates
    return pi


def filename2seed(filename: str) -> int:
    """Generate a valid numpy seed by hashing a filename.

    Parameters
    ----------
    filename : str
        The simulation output filename.

    Returns
    -------
    int
        An integer between 0 and 2**32.

    Examples
    --------
    >>> filename2seed('path/to/my_simulation_output.hdf5')
    2974054299

    It is very unlikely to start two simulations with the same seed.

    >>> seed1 = filename2seed('path/to/my_simulation_output.rep1.hdf5')
    >>> seed2 = filename2seed('path/to/my_simulation_output.rep2.hdf5')
    >>> np.random.seed(seed1)
    >>> print(seed1, np.random.uniform())
    272825019 0.13286198770980562
    >>> np.random.seed(seed2)
    >>> print(seed2, np.random.uniform())
    2028164767 0.8321152367526514
    """
    h = blake2b(filename.encode(), digest_size=4)
    return int.from_bytes(h.digest(), "big")
