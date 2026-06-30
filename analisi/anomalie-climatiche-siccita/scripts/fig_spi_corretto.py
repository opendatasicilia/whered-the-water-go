"""Rigenera le Figure 8, 9, 10 usando lo SPI RICALCOLATO correttamente,
piu' una figura di verifica (ciclo stagionale: fornito vs ricalcolato).
Carica ogni scala SPI una sola volta."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from scipy.stats import gaussian_kde
import common
import xarray as xr

ref = xr.open_dataset(common.PRECIP_NC)
times = pd.DatetimeIndex(ref.time.values)
lat, lon = ref.lat.values, ref.lon.values
mask = common.build_province_mask(lat, lon)
ref.close()

PERIODS = [(1951, 1968), (1969, 1987), (1988, 2005), (2006, 2024)]
COL = {1: "blue", 2: "green", 3: "red"}

# carica una volta: per ogni scala -> period means (mappe) + serie provinciali
period_mean = {}
prov_series = {1: [], 2: [], 3: []}
season_month_mean = {}   # per verifica
for scale in [1, 2, 3]:
    da = common.load_spi_recomputed(scale).load()
    yr = da["time.year"]
    period_mean[scale] = [da.where((yr >= y0) & (yr <= y1), drop=True).mean("time").values
                          for y0, y1 in PERIODS]
    for p in range(len(common.PROV_ORDER)):
        prov_series[scale].append(common.province_monthly_mean(da, mask, p))
    season_month_mean[scale] = [float(da.isel(time=(da["time.month"] == m)).mean().values)
                                for m in range(1, 13)]
    da.close()

# ---------------- FIG 8 corretto: mappe SPI ----------------
fig, axes = plt.subplots(3, 4, figsize=(15, 9.5))
for r, scale in enumerate([1, 2, 3]):
    pcm = None
    for c, (y0, y1) in enumerate(PERIODS):
        ax = axes[r, c]
        sub = period_mean[scale][c]
        pcm = ax.pcolormesh(lon, lat, sub, cmap="RdBu", vmin=-0.5, vmax=0.5, shading="auto")
        ax.contour(lon, lat, sub, levels=[0.0], colors="k", linewidths=0.7)
        if r == 0:
            ax.set_title(f"{y0}-{y1}", fontsize=12, weight="bold")
        ax.set_xlabel("Longitudine (E)", fontsize=8)
        ax.set_ylabel("Latitudine (N)", fontsize=8)
        ax.tick_params(labelsize=7); ax.set_aspect(1.0)
    cb = fig.colorbar(pcm, ax=axes[r, :].tolist(), shrink=0.8, pad=0.01)
    cb.set_label(f"Valore SPI{scale} (ricalcolato)", fontsize=9)
fig.legend(handles=[Line2D([0], [0], color="k", lw=0.8, label="isolinea 0 (confine siccita'/umidita')")],
           loc="upper left", fontsize=10, frameon=False, bbox_to_anchor=(0.05, 1.0))
fig.savefig(os.path.join(common.OUT, "fig08_spi_maps_CORRETTO.png"), dpi=130, bbox_inches="tight")
print("saved fig08_spi_maps_CORRETTO.png")
plt.close(fig)

# ---------------- FIG 9 corretto: densita' SPI ----------------
fig, axes = plt.subplots(3, 3, figsize=(13, 10))
for p, name in enumerate(common.PROV_ORDER):
    ax = axes.flat[p]
    for scale in [1, 2, 3]:
        v = prov_series[scale][p]; v = v[np.isfinite(v)]
        kde = gaussian_kde(v)
        xs = np.linspace(v.min() - 0.5, v.max() + 0.5, 300)
        ax.plot(xs, kde(xs), color=COL[scale], lw=1.4, label=f"SPI{scale}")
    ax.set_title(name, fontsize=12, weight="bold")
    ax.set_xlabel("SPI"); ax.set_ylabel("Densita'")
    ax.grid(alpha=0.3); ax.tick_params(labelsize=8)
h, l = axes.flat[0].get_legend_handles_labels()
fig.legend(h, l, loc="upper center", ncol=3, fontsize=11, frameon=False, bbox_to_anchor=(0.5, 1.01))
fig.tight_layout(rect=[0, 0, 1, 0.98])
fig.savefig(os.path.join(common.OUT, "fig09_spi_density_CORRETTO.png"), dpi=130, bbox_inches="tight")
print("saved fig09_spi_density_CORRETTO.png")
plt.close(fig)

# ---------------- FIG 10 corretto: serie temporali SPI (media mobile 12m) ----------------
years = times.year + (times.month - 1) / 12.0
fig, axes = plt.subplots(3, 3, figsize=(15, 11))
for p, name in enumerate(common.PROV_ORDER):
    ax = axes.flat[p]
    for scale in [1, 2, 3]:
        roll = pd.Series(prov_series[scale][p], index=times).rolling(12, center=True, min_periods=1).mean()
        ax.plot(years, roll.values, color=COL[scale], lw=0.8, label=f"SPI{scale}")
    ax.axhline(0, color="0.6", lw=0.6)
    ax.set_title(name, fontsize=12, weight="bold")
    ax.set_xlabel("Anno"); ax.set_ylabel("SPI (Media Mobile 12m)")
    ax.grid(alpha=0.25); ax.tick_params(labelsize=8)
h, l = axes.flat[0].get_legend_handles_labels()
fig.legend(h, l, loc="upper center", ncol=3, fontsize=11, frameon=False, bbox_to_anchor=(0.5, 1.005))
fig.tight_layout(rect=[0, 0, 1, 0.98])
fig.savefig(os.path.join(common.OUT, "fig10_spi_ts_CORRETTO.png"), dpi=130, bbox_inches="tight")
print("saved fig10_spi_ts_CORRETTO.png")
plt.close(fig)

# ---------------- FIG verifica: ciclo stagionale fornito vs ricalcolato ----------------
prov_season = {}
for scale in [1, 2, 3]:
    da = common.load_spi(scale, center=False)
    prov_season[scale] = [float(da.isel(time=(da["time.month"] == m)).mean().values) for m in range(1, 13)]
    da.close()
fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
mm = np.arange(1, 13)
for scale, col in zip([1, 2, 3], ["tab:blue", "tab:green", "tab:red"]):
    axes[0].plot(mm, prov_season[scale], "o-", color=col, label=f"SPI{scale}")
    axes[1].plot(mm, season_month_mean[scale], "o-", color=col, label=f"SPI{scale}")
for ax, tit in zip(axes, ["FORNITO (predicted)", "RICALCOLATO (standard)"]):
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(mm); ax.set_xticklabels([m[:3] for m in common.MESI], rotation=45)
    ax.set_title(tit, fontsize=12, weight="bold"); ax.grid(alpha=0.3); ax.legend()
axes[0].set_ylabel("media SPI sull'isola")
fig.suptitle("Verifica: media SPI per mese di calendario\n(corretto = piatto a 0; fornito = ciclo stagionale residuo)", fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.96])
fig.savefig(os.path.join(common.OUT, "verify_ciclo_stagionale_confronto.png"), dpi=130, bbox_inches="tight")
print("saved verify_ciclo_stagionale_confronto.png")
