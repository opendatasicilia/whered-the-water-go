"""Figura 1 (pannello destro) - Mappa delle 9 province siciliane.
Il pannello sinistro del report (elevazione Italia 1 km) richiede un DEM esterno
non incluso nei dati forniti, quindi non e' riproducibile da questo dataset."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import geopandas as gpd
import common

gdf = gpd.read_file(common.GEOJSON).to_crs(4326)
# ordine legenda come nel report
order = ["Trapani", "Palermo", "Messina", "Agrigento", "Caltanissetta",
         "Enna", "Catania", "Ragusa", "Siracusa"]
cmap = plt.get_cmap("tab10")
colors = {n: cmap(i % 10) for i, n in enumerate(order)}

fig, ax = plt.subplots(figsize=(8, 7))
for n in order:
    g = gdf[gdf["provincia"] == n]
    g.plot(ax=ax, color=colors[n], edgecolor="white", linewidth=0.6, label=n)
handles = [plt.Line2D([0], [0], marker="o", ls="", color=colors[n], label=n) for n in order]
ax.legend(handles=handles, loc="upper right", fontsize=9, frameon=False)
ax.set_title("Mappa delle Regioni Siciliane", fontsize=13, weight="bold")
ax.set_xlabel("Longitudine (E)")
ax.set_ylabel("Latitudine (N)")
ax.set_aspect(1.0)
fig.tight_layout()
out = os.path.join(common.OUT, "fig01_province_map.png")
fig.savefig(out, dpi=130, bbox_inches="tight")
print("saved", out)
