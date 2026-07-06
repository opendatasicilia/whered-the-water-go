"""Figura 10 - Serie temporali delle medie mobili di SPI1, SPI2, SPI3 per le 9
province (1951-2024). Per ogni provincia: serie mensile media spaziale ->
media mobile a 12 mesi -> tracciata nel tempo.
SPI1 centrato (bias), SPI2/SPI3 grezzi."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import common
import xarray as xr

ref = xr.open_dataset(common.PRECIP_NC)
times = pd.DatetimeIndex(ref.time.values)
mask = common.build_province_mask(ref.lat.values, ref.lon.values)
ref.close()

WIN = 12
series = {1: [], 2: [], 3: []}
for scale in [1, 2, 3]:
    da = common.load_spi(scale, center=(scale == 1)).load()
    for p in range(len(common.PROV_ORDER)):
        m = common.province_monthly_mean(da, mask, p)
        roll = pd.Series(m, index=times).rolling(WIN, center=True, min_periods=1).mean()
        series[scale].append(roll.values)
    da.close()

COL = {1: "blue", 2: "green", 3: "red"}
years = times.year + (times.month - 1) / 12.0
fig, axes = plt.subplots(3, 3, figsize=(15, 11))
for p, name in enumerate(common.PROV_ORDER):
    ax = axes.flat[p]
    for scale in [1, 2, 3]:
        ax.plot(years, series[scale][p], color=COL[scale], lw=0.8, label=f"SPI{scale}")
    ax.axhline(0, color="0.6", lw=0.6)
    ax.set_title(name, fontsize=12, weight="bold")
    ax.set_xlabel("Anno", fontsize=9)
    ax.set_ylabel("SPI (Media Mobile)", fontsize=9)
    ax.grid(alpha=0.25)
    ax.tick_params(labelsize=8)

handles, labels = axes.flat[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="upper center", ncol=3, fontsize=11,
           frameon=False, bbox_to_anchor=(0.5, 1.005))
fig.tight_layout(rect=[0, 0, 1, 0.98])
out = os.path.join(common.OUT, "fig10_spi_ts.png")
fig.savefig(out, dpi=130, bbox_inches="tight")
print("saved", out)
