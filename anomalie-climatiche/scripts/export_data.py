"""Esporta in CSV i dati derivati alla base delle figure del report."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import pandas as pd
import xarray as xr
import common

OUTD = os.path.join(common.OUT, "data")
os.makedirs(OUTD, exist_ok=True)

pr = common.load_precip()
times = pd.DatetimeIndex(pr.time.values)
mask = common.build_province_mask(pr.lat.values, pr.lon.values)

# 1) serie mensile precip media per provincia
mon = {}
for p, name in enumerate(common.PROV_ORDER):
    mon[name] = common.province_monthly_mean(pr, mask, p)
dfm = pd.DataFrame(mon, index=times)
dfm.index.name = "data"
dfm.to_csv(os.path.join(OUTD, "precip_mensile_provincia_mm.csv"))

# 2) totali stagionali precip per anno e provincia (base fig3/fig4)
rows = []
for p, name in enumerate(common.PROV_ORDER):
    seas = common.seasonal_totals(mon[name], times, agg="sum")
    for sname, (yrs, vals) in seas.items():
        for y, v in zip(yrs, vals):
            rows.append((name, sname, int(y), round(float(v), 2)))
pd.DataFrame(rows, columns=["provincia", "stagione", "anno", "precip_mm"]).to_csv(
    os.path.join(OUTD, "precip_stagionale_provincia.csv"), index=False)

# 3) climatologia mensile precip per provincia (media 1951-2024)
clim_rows = []
for name in common.PROV_ORDER:
    s = pd.Series(mon[name], index=times)
    for m in range(1, 13):
        clim_rows.append((name, common.MESI[m-1], round(float(s[s.index.month == m].mean()), 2)))
pd.DataFrame(clim_rows, columns=["provincia", "mese", "precip_media_mm"]).to_csv(
    os.path.join(OUTD, "precip_climatologia_mensile_provincia.csv"), index=False)
pr.close()

# 4) SPI: serie mensile per provincia + medie per periodo
PERIODS = [(1951, 1968), (1969, 1987), (1988, 2005), (2006, 2024)]
spi_series = {}
period_rows = []
for scale in [1, 2, 3]:
    da = common.load_spi(scale, center=(scale == 1)).load()
    yr = da["time.year"].values
    for p, name in enumerate(common.PROV_ORDER):
        s = common.province_monthly_mean(da, mask, p)
        spi_series[(name, scale)] = s
        for (y0, y1) in PERIODS:
            sel = (yr >= y0) & (yr <= y1)
            period_rows.append((name, f"SPI{scale}", f"{y0}-{y1}",
                                round(float(np.nanmean(s[sel])), 4)))
    da.close()

idx = times
cols = {f"{name}_SPI{scale}": spi_series[(name, scale)]
        for scale in [1, 2, 3] for name in common.PROV_ORDER}
dfspi = pd.DataFrame(cols, index=idx)
dfspi.index.name = "data"
dfspi.to_csv(os.path.join(OUTD, "spi_mensile_provincia.csv"))

pd.DataFrame(period_rows, columns=["provincia", "indice", "periodo", "spi_medio"]).to_csv(
    os.path.join(OUTD, "spi_medie_periodo_provincia.csv"), index=False)

# 5) statistiche di siccita' per provincia (% valori < -0.5, < -1)
stat_rows = []
for scale in [1, 2, 3]:
    for name in common.PROV_ORDER:
        s = spi_series[(name, scale)]
        s = s[np.isfinite(s)]
        stat_rows.append((name, f"SPI{scale}",
                          round(100 * np.mean(s < -0.5), 1),
                          round(100 * np.mean(s < -1.0), 1),
                          round(float(np.mean(s)), 3)))
pd.DataFrame(stat_rows, columns=["provincia", "indice", "pct_sotto_-0.5",
             "pct_sotto_-1.0", "media"]).to_csv(
    os.path.join(OUTD, "spi_statistiche_siccita_provincia.csv"), index=False)

print("CSV esportati in", OUTD)
for f in sorted(os.listdir(OUTD)):
    print(" -", f)
