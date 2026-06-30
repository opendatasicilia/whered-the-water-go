"""Figura 3 - Distribuzioni di densita' (KDE) della precipitazione stagionale
per le 9 province (1951-2024). Per ogni provincia: media spaziale mensile ->
totali stagionali per anno -> KDE per le 4 stagioni."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
import common

pr = common.load_precip()
times = pr.time.values
mask = common.build_province_mask(pr.lat.values, pr.lon.values)

fig, axes = plt.subplots(3, 3, figsize=(13, 10))
for p, name in enumerate(common.PROV_ORDER):
    ax = axes.flat[p]
    monthly = common.province_monthly_mean(pr, mask, p)
    seas = common.seasonal_totals(monthly, times, agg="sum")
    xmax = 0
    for sname, col in common.SEASON_COLORS.items():
        _, vals = seas[sname]
        vals = vals[np.isfinite(vals)]
        kde = gaussian_kde(vals)
        xs = np.linspace(max(0, vals.min() - 30), vals.max() + 30, 300)
        ax.plot(xs, kde(xs), color=col, lw=1.5, label=sname)
        xmax = max(xmax, vals.max())
    ax.set_title(name, fontsize=12, weight="bold")
    ax.set_xlabel("Precipitazione stagionale (mm)", fontsize=9)
    ax.set_ylabel("Densita'", fontsize=9)
    ax.set_xlim(0, xmax + 50)
    ax.grid(alpha=0.3)
    ax.tick_params(labelsize=8)

handles, labels = axes.flat[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="upper center", ncol=4, fontsize=11,
           frameon=False, bbox_to_anchor=(0.5, 1.01))
fig.tight_layout(rect=[0, 0, 1, 0.98])
out = os.path.join(common.OUT, "fig03_precip_density.png")
fig.savefig(out, dpi=130, bbox_inches="tight")
print("saved", out)
