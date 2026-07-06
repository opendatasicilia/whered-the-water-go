"""Diagnostica SPI: confronta lo SPI 'predicted' fornito con uno SPI calcolato
correttamente dalla precipitazione (standardizzazione per singolo mese di calendario).
Produce due figure dimostrative."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import gamma, norm, gaussian_kde
import common

pr = common.load_precip()
times = pd.DatetimeIndex(pr.time.values)
mask = common.build_province_mask(pr.lat.values, pr.lon.values)


def proper_spi(precip_monthly, idx, k):
    """SPI corretto su una serie mensile: accumulo a k mesi, poi per OGNI mese
    di calendario fit gamma (con gestione degli zeri) -> normale standard."""
    s = pd.Series(precip_monthly, index=idx)
    acc = s.rolling(k, min_periods=k).sum()
    out = pd.Series(index=idx, dtype=float)
    for m in range(1, 13):
        sel = acc.index.month == m
        x = acc[sel].dropna()
        if len(x) < 10:
            continue
        vals = x.values
        zero = vals == 0
        q = zero.mean()                      # prob. di accumulo nullo
        pos = vals[~zero]
        if len(pos) < 5:
            continue
        a, loc, scl = gamma.fit(pos, floc=0)  # fit gamma sui positivi
        cdf = q + (1 - q) * gamma.cdf(vals, a, loc=0, scale=scl)
        cdf = np.clip(cdf, 1e-6, 1 - 1e-6)
        z = norm.ppf(cdf)
        out.loc[x.index] = z
    return out.values


# --- 1) Serie provincia-media: SPI fornito vs SPI corretto, per Enna e Palermo ---
prov_demo = ["Palermo", "Enna"]
provided = {}
proper = {}
for name in prov_demo:
    p = common.PROV_ORDER.index(name)
    pm = common.province_monthly_mean(pr, mask, p)
    for k in [1, 2, 3]:
        proper[(name, k)] = proper_spi(pm, times, k)

for k in [1, 2, 3]:
    da = common.load_spi(k, center=False).load()  # GREZZO
    for name in prov_demo:
        p = common.PROV_ORDER.index(name)
        provided[(name, k)] = common.province_monthly_mean(da, mask, p)
    da.close()

# Figura A: densita' confronto fornito vs corretto
fig, axes = plt.subplots(2, 3, figsize=(13, 7.5))
for r, name in enumerate(prov_demo):
    for c, k in enumerate([1, 2, 3]):
        ax = axes[r, c]
        for data, lab, col in [(provided[(name, k)], "fornito (predicted)", "crimson"),
                               (proper[(name, k)], "SPI corretto (per mese)", "navy")]:
            v = data[np.isfinite(data)]
            kde = gaussian_kde(v)
            xs = np.linspace(-4, 4, 300)
            ax.plot(xs, kde(xs), color=col, lw=1.8, label=lab)
            ax.axvline(np.mean(v), color=col, ls=":", lw=1)
        ax.axvline(0, color="0.6", lw=0.6)
        ax.set_title(f"{name} - SPI{k}", fontsize=11, weight="bold")
        ax.set_xlabel("SPI"); ax.set_ylabel("Densita'")
        ax.grid(alpha=0.3)
        if r == 0 and c == 0:
            ax.legend(fontsize=8)
fig.suptitle("SPI fornito (predicted) vs SPI standardizzato correttamente", fontsize=13)
fig.tight_layout(rect=[0, 0, 1, 0.97])
fig.savefig(os.path.join(common.OUT, "diag_spi_density_confronto.png"), dpi=130, bbox_inches="tight")
print("saved diag_spi_density_confronto.png")

# Figura B: media per mese di calendario (mostra il ciclo stagionale residuo)
fig, ax = plt.subplots(figsize=(9, 5))
months = np.arange(1, 13)
for k, col in zip([1, 2, 3], ["tab:blue", "tab:green", "tab:red"]):
    da = common.load_spi(k, center=False)
    mm = [float(da.isel(time=(da["time.month"] == m)).mean().values) for m in months]
    da.close()
    ax.plot(months, mm, "o-", color=col, label=f"SPI{k} fornito")
ax.axhline(0, color="k", lw=0.8)
ax.set_xticks(months); ax.set_xticklabels(common.MESI, rotation=45, ha="right")
ax.set_ylabel("media SPI sull'isola")
ax.set_title("Ciclo stagionale RESIDUO nello SPI fornito\n(in uno SPI corretto sarebbe piatto a 0)", fontsize=12)
ax.legend(); ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(common.OUT, "diag_spi_ciclo_stagionale.png"), dpi=130, bbox_inches="tight")
print("saved diag_spi_ciclo_stagionale.png")
pr.close()
