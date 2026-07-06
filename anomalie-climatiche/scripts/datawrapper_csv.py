"""Genera CSV pronti per Datawrapper a partire dai DATI CORRETTI (SPI ricalcolato
e precipitazione ISPRA). Output in output/datawrapper/."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import pandas as pd
import xarray as xr
import common

OUTD = os.path.join(common.OUT, "datawrapper")
os.makedirs(OUTD, exist_ok=True)

pr = common.load_precip()
times = pd.DatetimeIndex(pr.time.values)
mask = common.build_province_mask(pr.lat.values, pr.lon.values)
land = mask >= 0                       # celle in Sicilia (9 province)
P = pr.values                          # (time, lat, lon)
pr.close()

PERIODS = [("1951-1968", 1951, 1968), ("1969-1987", 1969, 1987),
           ("1988-2005", 1988, 2005), ("2006-2024", 2006, 2024)]
SIGLE = {"Palermo": "PA", "Messina": "ME", "Catania": "CT", "Enna": "EN",
         "Trapani": "TP", "Caltanissetta": "CL", "Siracusa": "SR",
         "Ragusa": "RG", "Agrigento": "AG"}


def sicily_mean(arr3d):
    m = land[None, :, :]
    v = np.where(m, arr3d, np.nan)
    return np.nanmean(v.reshape(arr3d.shape[0], -1), axis=1)


# carica SPI ricalcolato e calcola medie isola + per provincia/periodo
spi_island = {}
period_island_deficit = {1: {}, 2: {}, 3: {}}
prov_period = {p: {} for p in common.PROV_ORDER}
for k in [1, 2, 3]:
    da = common.load_spi_recomputed(k).load()
    spi_island[k] = sicily_mean(da.values)
    yr = da["time.year"].values
    for nome, y0, y1 in PERIODS:
        sub = da.values[(yr >= y0) & (yr <= y1)]
        pm = np.nanmean(sub, axis=0)               # media periodo per cella
        cells = pm[land]
        cells = cells[np.isfinite(cells)]
        period_island_deficit[k][nome] = 100 * np.mean(cells < 0)
        if k == 3:
            for pi, prov in enumerate(common.PROV_ORDER):
                sel = (mask == pi)
                prov_period[prov][nome] = float(np.nanmean(pm[sel]))
    da.close()

# ---------- CSV A: cronologia siccita' (SPI media mobile 12 mesi, isola) ----------
dfA = pd.DataFrame({"data": times.strftime("%Y-%m")})
for k in [1, 2, 3]:
    dfA[f"SPI{k}"] = np.round(pd.Series(spi_island[k]).rolling(12, center=True, min_periods=6).mean().values, 3)
dfA.to_csv(os.path.join(OUTD, "A_cronologia_siccita_sicilia.csv"), index=False)

# ---------- CSV B: % territorio in deficit per periodo ----------
rowsB = []
for nome, _, _ in PERIODS:
    rowsB.append({"periodo": nome,
                  "territorio in siccita di lungo periodo (%)": round(period_island_deficit[3][nome], 0),
                  "territorio in deficit breve (%)": round(period_island_deficit[1][nome], 0)})
pd.DataFrame(rowsB).to_csv(os.path.join(OUTD, "B_territorio_siccita_per_periodo.csv"), index=False)

# ---------- CSV C: anomalia di siccita' per provincia e periodo (SPI3) ----------
rowsC = []
for prov in common.PROV_ORDER:
    r = {"provincia": prov, "sigla": SIGLE[prov]}
    for nome, _, _ in PERIODS:
        r[nome] = round(prov_period[prov][nome], 2)
    rowsC.append(r)
pd.DataFrame(rowsC).to_csv(os.path.join(OUTD, "C_anomalia_provincia_periodo.csv"), index=False)

# ---------- CSV D: regime delle piogge (climatologia mensile, isola) ----------
sP = pd.Series(sicily_mean(P), index=times)
clim = [round(float(sP[sP.index.month == m].mean()), 1) for m in range(1, 13)]
pd.DataFrame({"mese": common.MESI, "pioggia media (mm)": clim}).to_csv(
    os.path.join(OUTD, "D_regime_piogge_sicilia.csv"), index=False)

# ---------- CSV E: pioggia annuale media in Sicilia ----------
# media spaziale mensile (salta i NaN), poi somma dei 12 mesi per anno.
# NB: NON usare nansum per cella: le celle no-data (NaN) diventerebbero 0
# e abbasserebbero la media (bug corretto in fase di verifica).
sP_isola = sicily_mean(P)                       # serie mensile media isola
sP_series = pd.Series(sP_isola, index=times)
ann_series = sP_series.groupby(sP_series.index.year).sum()
ann = {int(y): round(float(v), 0) for y, v in ann_series.items()}
dfE = pd.DataFrame({"anno": list(ann.keys()), "pioggia annua media (mm)": list(ann.values())})
media_lp = dfE["pioggia annua media (mm)"].mean()
dfE["media 1951-2024 (mm)"] = round(media_lp, 0)
dfE.to_csv(os.path.join(OUTD, "E_pioggia_annuale_sicilia.csv"), index=False)

print("CSV Datawrapper salvati in", OUTD)
for f in sorted(os.listdir(OUTD)):
    print(" -", f)
print(f"\nmedia annua isola: {media_lp:.0f} mm")
print("deficit SPI3 per periodo:", {n: round(period_island_deficit[3][n]) for n, _, _ in PERIODS})
