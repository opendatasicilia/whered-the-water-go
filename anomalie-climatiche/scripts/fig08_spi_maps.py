"""Figura 8 - Mappe SPI a 1, 2 e 3 mesi mediate su 4 periodi (1951-1968,
1969-1987, 1988-2005, 2006-2024). Colore = valore medio SPI del periodo.
Contorno solido = isolinea 0 (confine siccita'/umidita')."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import common

PERIODS = [(1951, 1968), (1969, 1987), (1988, 2005), (2006, 2024)]
lon = lat = None

fig, axes = plt.subplots(3, 4, figsize=(15, 9.5))
pcm = None
for r, scale in enumerate([1, 2, 3]):
    # SPI2/SPI3 sono gia' standardizzati (media~0): usati grezzi.
    # SPI1 ha bias -0.44: centrato per cella per rimuoverlo (vedi load_spi).
    da = common.load_spi(scale, center=(scale == 1))
    if lon is None:
        lon, lat = da.lon.values, da.lat.values
    yr = da["time.year"]
    for c, (y0, y1) in enumerate(PERIODS):
        ax = axes[r, c]
        sub = da.where((yr >= y0) & (yr <= y1), drop=True).mean("time").values
        pcm = ax.pcolormesh(lon, lat, sub, cmap="RdBu", vmin=-0.5, vmax=0.5,
                            shading="auto")
        # isolinea 0: confine tra siccita' (rosso) e umidita' (blu)
        ax.contour(lon, lat, sub, levels=[0.0], colors="k", linewidths=0.7)
        if r == 0:
            ax.set_title(f"{y0}-{y1}", fontsize=12, weight="bold")
        ax.set_xlabel("Longitudine (E)", fontsize=8)
        ax.set_ylabel("Latitudine (N)", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.set_aspect(1.0)
    da.close()
    # colorbar a destra di ogni riga
    cb = fig.colorbar(pcm, ax=axes[r, :].tolist(), shrink=0.8, pad=0.01)
    cb.set_label(f"Valore SPI{scale}", fontsize=9)

handles = [Line2D([0], [0], color="k", lw=0.8, ls="-", label="Siccita' lieve (-1.0 a 0.0)"),
           Line2D([0], [0], color="k", lw=0.8, ls="--", label="Umidita' lieve (0.0 a 1.0)")]
fig.legend(handles=handles, loc="upper left", ncol=2, fontsize=10,
           title="Classi SPI:", title_fontsize=10, frameon=False,
           bbox_to_anchor=(0.05, 1.0))
out = os.path.join(common.OUT, "fig08_spi_maps.png")
fig.savefig(out, dpi=130, bbox_inches="tight")
print("saved", out)
