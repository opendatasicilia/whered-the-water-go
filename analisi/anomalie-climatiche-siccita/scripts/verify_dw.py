"""Verifica indipendente dei valori esportati per Datawrapper (CSV A-E).
Ricalcola gli aggregati dai NetCDF con xarray (percorso diverso da datawrapper_csv.py)
e confronta con i CSV. Stampa PASS/FAIL con differenza massima."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import pandas as pd
import xarray as xr
import common

DW = os.path.join(common.OUT, "datawrapper")

# maschera province -> DataArray booleano "land" (le 9 province)
pr = common.load_precip()
mask = common.build_province_mask(pr.lat.values, pr.lon.values)
land = xr.DataArray(mask >= 0, dims=("lat", "lon"),
                    coords={"lat": pr.lat, "lon": pr.lon})
prov_da = xr.DataArray(mask, dims=("lat", "lon"),
                       coords={"lat": pr.lat, "lon": pr.lon})

def chk(name, ref, got, tol=0.05):
    d = float(np.nanmax(np.abs(np.asarray(ref) - np.asarray(got))))
    print(f"  [{'PASS' if d <= tol else 'FAIL'}] {name}: max|Δ|={d:.4g} (tol {tol})")
    return d <= tol

# media spaziale sull'isola con xarray (where + mean su lat,lon)
def isl(da):
    return da.where(land).mean(("lat", "lon"))

ok = True

# ---------- D: climatologia mensile ----------
print("== D: climatologia mensile precipitazione ==")
clim_x = isl(pr).groupby("time.month").mean("time").values  # (12,)
dD = pd.read_csv(os.path.join(DW, "D_regime_piogge_sicilia.csv"))
ok &= chk("D pioggia media mensile", dD["pioggia media (mm)"].values, np.round(clim_x, 1), tol=0.15)

# ---------- E: pioggia annuale media + media lungo periodo ----------
print("== E: pioggia annuale media ==")
ann_x = isl(pr).groupby("time.year").sum("time").values   # (74,) mm/anno medi isola
dE = pd.read_csv(os.path.join(DW, "E_pioggia_annuale_sicilia.csv"))
ok &= chk("E pioggia annua", dE["pioggia annua media (mm)"].values, np.round(ann_x, 0), tol=1.0)
ok &= chk("E media lungo periodo", dE["media 1951-2024 (mm)"].iloc[0], round(float(np.mean(ann_x)), 0), tol=1.0)
pr.close()

# ---------- B e C e A: dagli SPI ricalcolati ----------
PERIODS = [("1951-1968", 1951, 1968), ("1969-1987", 1969, 1987),
           ("1988-2005", 1988, 2005), ("2006-2024", 2006, 2024)]
dB = pd.read_csv(os.path.join(DW, "B_territorio_siccita_per_periodo.csv"))
dC = pd.read_csv(os.path.join(DW, "C_anomalia_provincia_periodo.csv"))
dA = pd.read_csv(os.path.join(DW, "A_cronologia_siccita_sicilia.csv"))

for k, col_b in [(3, "territorio in siccita di lungo periodo (%)"),
                 (1, "territorio in deficit breve (%)")]:
    da = common.load_spi_recomputed(k).load()
    yr = da["time.year"]
    print(f"== B: % territorio in deficit SPI{k} ==")
    got = []
    for nome, y0, y1 in PERIODS:
        pm = da.where((yr >= y0) & (yr <= y1), drop=True).mean("time")  # media periodo per cella
        cells = pm.where(land).values
        cells = cells[np.isfinite(cells)]
        got.append(round(100 * np.mean(cells < 0), 0))
    ok &= chk(f"B SPI{k}", dB[col_b].values, got, tol=1.0)

    if k == 3:
        print("== C: SPI3 medio per provincia e periodo ==")
        for pi, prov in enumerate(common.PROV_ORDER):
            sel = prov_da == pi
            ref = dC[dC["provincia"] == prov]
            got_c = []
            for nome, y0, y1 in PERIODS:
                pm = da.where((yr >= y0) & (yr <= y1), drop=True).mean("time")
                got_c.append(round(float(pm.where(sel).mean().values), 2))
            ok &= chk(f"C {prov}", ref[[p[0] for p in PERIODS]].values[0], got_c, tol=0.02)

        print("== A: cronologia SPI3 (5 punti campione) ==")
        s = isl(da).to_series()
        roll = s.rolling(12, center=True, min_periods=6).mean()
        idx = pd.DatetimeIndex(dA["data"] + "-01")
        sample = [0, 200, 444, 700, len(dA) - 1]
        ref_a = dA["SPI3"].values[sample]
        got_a = np.round(roll.reindex(idx).values[sample], 3)
        ok &= chk("A SPI3 campione", np.nan_to_num(ref_a), np.nan_to_num(got_a), tol=0.01)
    da.close()

print("\nRISULTATO:", "TUTTI I VALORI VERIFICATI ✓" if ok else "DISCREPANZE TROVATE ✗")
