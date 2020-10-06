# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:light
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.6.0
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %load_ext autoreload
# %autoreload 1
# %aimport twosfs.demographicmodel, twosfs.simulations, twosfs.spectra, twosfs.statistics # noqa

import matplotlib.pyplot as plt
import numpy as np
from scipy.special import rel_entr

import twosfs.statistics as stats
from twosfs.demographicmodel import DemographicModel
from twosfs.spectra import load_spectra

# ## Import data

alphas = [f"{a:.2f}" for a in np.arange(1.05, 2.0, 0.05)]
model = "3Epoch"
sample_size = 100
kmax = 20

modelfn = "../simulations/fastNeutrino/xibeta-alpha={0}.{1}.txt"
betafn = "../simulations/msprime/xibeta-alpha={0}.npz"
fittedfn = "../simulations/msprime/fastNeutrino.xibeta-alpha={0}.{1}.npz"

data_kingman = load_spectra("../simulations/msprime/kingman.npz")
data_kingman.normalize()

demo_models = []
data_beta = []
data_fitted = []
for alpha in alphas:
    dm = DemographicModel(modelfn.format(alpha, model))
    dm.rescale()
    demo_models.append(dm)

    spectra = load_spectra(betafn.format(alpha))
    spectra.normalize()
    data_beta.append(spectra)
    spectra = load_spectra(fittedfn.format(alpha, model))
    spectra.normalize()
    data_fitted.append(spectra)

lumped_kingman = data_kingman.lumped_twosfs(kmax)
lumped_beta = [s.lumped_twosfs(kmax) for s in data_beta]
lumped_fitted = [s.lumped_twosfs(kmax) for s in data_fitted]

# ## Fitted demographic models

t = np.logspace(-2, 2, 100)
for alpha, dm in zip(alphas, demo_models):
    plt.semilogx(t, dm.population_size(t), label=alpha)
plt.legend(title="alpha")
plt.ylim([0.5, 50])
plt.yscale("log")
plt.ylabel("Population size (coal. units)")
plt.xlabel("Time (coal. units)")

# ## SFS comparisons

for alpha, dbeta, dfitted in zip(alphas, data_beta, data_fitted):
    plt.loglog(data_kingman.sfs / data_kingman.sfs[1], "-k", label="Const-N")
    plt.loglog(dbeta.sfs / dbeta.sfs[1], "x", label="beta")
    plt.loglog(dfitted.sfs / dfitted.sfs[1], ".", label="fitted")
    plt.vlines(kmax, 5e-3, 1, color="0.5", linestyle="dashed", label="kmax")
    plt.title("alpha = " + alpha)
    plt.legend()
    plt.show()

# ## 2-SFS comparisons

# First, look at no recombination

d = 0
for alpha, dbeta, dfitted in zip(alphas, lumped_beta, lumped_fitted):
    twosfs_beta = dbeta[d, 1:, 1:]
    twosfs_fitted = dfitted[d, 1:, 1:]
    plt.pcolormesh(
        np.log2(twosfs_beta / twosfs_fitted), vmin=-0.5, vmax=0.5, cmap="PuOr_r"
    )
    plt.colorbar()
    plt.title(alpha)
    plt.show()

    print(np.sum(rel_entr(twosfs_fitted, twosfs_beta)))

for alpha, dbeta, dfitted in zip(alphas, lumped_beta, lumped_fitted):
    twosfs_beta = dbeta[d, 1:, 1:]
    F_beta = stats.conditional_sfs(twosfs_beta)
    twosfs_fitted = dfitted[d, 1:, 1:]
    F_fitted = stats.conditional_sfs(twosfs_fitted)
    D = stats.distance(F_beta, F_fitted)
    plt.plot(D)
    print(np.sum(D))

npairs = 10000
nresample = 1000
D_kingman = []
D_beta = []
for alpha, dbeta, dfitted in zip(alphas, lumped_beta, lumped_fitted):
    twosfs_beta = dbeta[d, 1:, 1:]
    twosfs_fitted = dfitted[d, 1:, 1:]
    D_kingman.append(
        stats.resample_distance(twosfs_fitted, twosfs_fitted, npairs, nresample)
    )
    D_beta.append(
        stats.resample_distance(twosfs_beta, twosfs_fitted, npairs, nresample)
    )

bins = np.linspace(7, 23, 100)
for alpha, d_k, d_b in zip(alphas, D_kingman, D_beta):
    total_k = np.sum(d_k, axis=1)
    total_b = np.sum(d_b, axis=1)
    power = np.mean(stats.rank(total_b, total_k) > 0.95 * nresample)
    plt.hist(total_k, histtype="step", bins=bins)
    plt.hist(total_b, histtype="step", bins=bins)
    plt.title(alpha)
    plt.show()
    print(power)

power = []
for alpha, d_k, d_b in zip(alphas, D_kingman, D_beta):
    total_k = np.sum(d_k, axis=1)
    total_b = np.sum(d_b, axis=1)
    power.append(np.mean(stats.rank(total_b, total_k) > 0.95 * nresample))
plt.plot(np.array(alphas, dtype=float), power, ".")
plt.ylim([0, 1.05])
plt.ylabel("Power")
plt.xlim([1, 2])
plt.xlabel("alpha")
