"""Figura 9 - Distribuzioni di densita' (KDE) di SPI1, SPI2, SPI3 per le 9
province (1951-2024). Per ogni provincia si usa la serie mensile media spaziale
e si stima la KDE dei valori SPI.
SPI1 e' centrato per rimuovere il bias dei dati (vedi load_spi); SPI2/SPI3 grezzi."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
import common

# precarico maschera dalla griglia precip (identica)
import xarray as xr
ref = xr.open_dataset(common.PRECIP_NC)
mask = common.build_province_mask(ref.lat.values, ref.lon.values)
ref.close()

# serie mensile media per provincia per ogni SPI
series = {1: [], 2: [], 3: []}
for scale in [1, 2, 3]:
    da = common.load_spi(scale, center=(scale == 1)).load()
    for p in range(len(common.PROV_ORDER)):
        series[scale].append(common.province_monthly_mean(da, mask, p))
    da.close()

COL = {1: "blue", 2: "green", 3: "red"}
fig, axes = plt.subplots(3, 3, figsize=(13, 10))
for p, name in enumerate(common.PROV_ORDER):
    ax = axes.flat[p]
    for scale in [1, 2, 3]:
        vals = series[scale][p]
        vals = vals[np.isfinite(vals)]
        kde = gaussian_kde(vals)
        xs = np.linspace(vals.min() - 0.5, vals.max() + 0.5, 300)
        ax.plot(xs, kde(xs), color=COL[scale], lw=1.4, label=f"SPI{scale}")
    ax.set_title(name, fontsize=12, weight="bold")
    ax.set_xlabel("SPI", fontsize=9)
    ax.set_ylabel("Densita'", fontsize=9)
    ax.grid(alpha=0.3)
    ax.tick_params(labelsize=8)

handles, labels = axes.flat[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="upper center", ncol=3, fontsize=11,
           frameon=False, bbox_to_anchor=(0.5, 1.01))
fig.tight_layout(rect=[0, 0, 1, 0.98])
out = os.path.join(common.OUT, "fig09_spi_density.png")
fig.savefig(out, dpi=130, bbox_inches="tight")
print("saved", out)
