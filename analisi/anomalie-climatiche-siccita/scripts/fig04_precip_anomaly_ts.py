"""Figura 4 - Serie temporali della precipitazione stagionale per provincia con
medie di lungo periodo e rilevamento delle anomalie. Le anomalie sono i punti
che deviano oltre +-2 deviazioni standard dalla media stagionale 1951-2024."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import common

pr = common.load_precip()
times = pr.time.values
mask = common.build_province_mask(pr.lat.values, pr.lon.values)

fig, axes = plt.subplots(3, 3, figsize=(15, 11))
for p, name in enumerate(common.PROV_ORDER):
    ax = axes.flat[p]
    monthly = common.province_monthly_mean(pr, mask, p)
    seas = common.seasonal_totals(monthly, times, agg="sum")
    for sname, col in common.SEASON_COLORS.items():
        yrs, vals = seas[sname]
        ax.plot(yrs, vals, color=col, lw=1.0, label=sname)
        mu, sd = np.nanmean(vals), np.nanstd(vals)
        ax.axhline(mu, color=col, ls="--", lw=1.0)
        anom = np.abs(vals - mu) > 2 * sd
        ax.scatter(yrs[anom], vals[anom], color="k", s=12, zorder=5)
        for x, y in zip(yrs[anom], vals[anom]):
            ax.annotate(str(int(x)), (x, y), fontsize=5, ha="left", va="bottom")
    ax.set_title(name, fontsize=12, weight="bold")
    ax.set_xlabel("Anno", fontsize=9)
    ax.set_ylabel("Precipitazione (mm)", fontsize=9)
    ax.grid(alpha=0.25)
    ax.tick_params(labelsize=8)

handles = [Line2D([0], [0], color=c, lw=1.5, label=s) for s, c in common.SEASON_COLORS.items()]
handles += [Line2D([0], [0], color=c, lw=1.2, ls="--", label=f"Media {s}") for s, c in common.SEASON_COLORS.items()]
handles += [Line2D([0], [0], color="k", marker="o", ls="", label="Anomalia")]
fig.legend(handles=handles, loc="upper center", ncol=9, fontsize=8.5,
           frameon=False, bbox_to_anchor=(0.5, 1.005))
fig.tight_layout(rect=[0, 0, 1, 0.975])
out = os.path.join(common.OUT, "fig04_precip_anomaly_ts.png")
fig.savefig(out, dpi=130, bbox_inches="tight")
print("saved", out)
