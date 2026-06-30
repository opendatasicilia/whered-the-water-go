"""Figura 2 - Mappe della precipitazione mensile media (1951-2024) con contorni
di anomalia spaziale relativa.

Interpretazione (esplicitata nel report come 'linee di anomalia 10-25%, 25-50%, >=50%'):
per ogni mese si calcola la climatologia media per cella e l'anomalia spaziale
relativa rispetto alla media regionale siciliana del mese:
    anomalia% = (media_cella - media_regionale) / media_regionale
I contorni evidenziano dove una cella riceve il 10-25%, 25-50% o >=50% in piu'
rispetto alla media dell'isola (effetto orografico).
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import common

pr = common.load_precip()
lat = pr.lat.values
lon = pr.lon.values
LON, LAT = np.meshgrid(lon, lat)

# climatologia mensile media (media su tutti gli anni per ciascun mese)
clim = pr.groupby("time.month").mean("time")  # (month, lat, lon)

fig, axes = plt.subplots(4, 3, figsize=(13, 14))
vmax = float(np.nanpercentile(clim.values, 99))
levels = [0.10, 0.25, 0.50]
lstyles = [(0, (4, 3)), (0, (6, 2)), "--"]
lw = [0.5, 0.8, 1.1]
lcol = ["0.55", "0.3", "k"]

for m in range(1, 13):
    ax = axes.flat[m - 1]
    field = clim.sel(month=m).values
    reg_mean = np.nanmean(field)
    anom = (field - reg_mean) / reg_mean  # anomalia spaziale relativa

    pcm = ax.pcolormesh(lon, lat, field, cmap="YlGnBu", vmin=0, vmax=vmax,
                        shading="auto")
    # contorni solo sull'anomalia positiva
    for lev, ls, w, c in zip(levels, lstyles, lw, lcol):
        try:
            ax.contour(lon, lat, anom, levels=[lev], colors=c,
                       linewidths=w, linestyles=ls)
        except Exception:
            pass
    cb = fig.colorbar(pcm, ax=ax, shrink=0.85, pad=0.02)
    cb.set_label("Precipitazione (mm)", fontsize=8)
    cb.ax.tick_params(labelsize=7)
    ax.set_title(f"{common.MESI[m-1]} (dal 1951 al 2024)", fontsize=11, weight="bold")
    ax.set_xlabel("Longitudine (E)", fontsize=8)
    ax.set_ylabel("Latitudine (N)", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.set_aspect(1.0)

handles = [Line2D([0], [0], color=c, lw=w, ls=ls, label=lab)
           for c, w, ls, lab in zip(lcol, lw, lstyles, ["10-25%", "25-50%", ">=50%"])]
fig.legend(handles=handles, loc="upper center", ncol=3, fontsize=10,
           title="Anomalia:", title_fontsize=10, frameon=False,
           bbox_to_anchor=(0.5, 1.005))
fig.tight_layout(rect=[0, 0, 1, 0.985])
out = os.path.join(common.OUT, "fig02_precip_maps.png")
fig.savefig(out, dpi=130, bbox_inches="tight")
print("saved", out)
