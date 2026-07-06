"""Tabelle diagnostiche (pochi punti dati) per capire il problema SPI.
Confronta SPI fornito ('predicted') vs SPI ricalcolato correttamente (per mese),
sulla serie media della provincia di Enna.
Salva 3 CSV in output/data/ e stampa le tabelle."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import pandas as pd
import xarray as xr
from scipy.stats import gamma, norm
import common

OUTD = os.path.join(common.OUT, "data")
os.makedirs(OUTD, exist_ok=True)
pd.set_option("display.width", 200)

pr = common.load_precip()
times = pd.DatetimeIndex(pr.time.values)
mask = common.build_province_mask(pr.lat.values, pr.lon.values)
PROV = "Enna"
p = common.PROV_ORDER.index(PROV)
precip_enna = common.province_monthly_mean(pr, mask, p)
pr.close()


def proper_spi(precip_monthly, idx, k):
    s = pd.Series(precip_monthly, index=idx)
    acc = s.rolling(k, min_periods=k).sum()
    out = pd.Series(index=idx, dtype=float)
    for m in range(1, 13):
        x = acc[acc.index.month == m].dropna()
        if len(x) < 10:
            continue
        vals = x.values
        zero = vals == 0
        q = zero.mean()
        pos = vals[~zero]
        if len(pos) < 5:
            continue
        a, loc, scl = gamma.fit(pos, floc=0)
        cdf = q + (1 - q) * gamma.cdf(vals, a, loc=0, scale=scl)
        z = norm.ppf(np.clip(cdf, 1e-6, 1 - 1e-6))
        out.loc[x.index] = z
    return out

# accumuli e SPI corretto
acc = {k: pd.Series(precip_enna, index=times).rolling(k, min_periods=k).sum() for k in [1, 2, 3]}
proper = {k: proper_spi(precip_enna, times, k) for k in [1, 2, 3]}
provided = {}
for k in [1, 2, 3]:
    da = common.load_spi(k, center=False).load()
    provided[k] = pd.Series(common.province_monthly_mean(da, mask, p), index=times)
    da.close()

# ---------- TAB 1: ciclo stagionale (media per mese) ----------
rows = []
for m in range(1, 13):
    r = {"mese": common.MESI[m - 1]}
    for k in [1, 2, 3]:
        r[f"SPI{k}_fornito"] = round(float(provided[k][provided[k].index.month == m].mean()), 2)
        r[f"SPI{k}_corretto"] = round(float(proper[k][proper[k].index.month == m].mean()), 2)
    rows.append(r)
t1 = pd.DataFrame(rows)
t1.to_csv(os.path.join(OUTD, "tab1_ciclo_stagionale_Enna.csv"), index=False)
print("\n==== TAB 1 - media SPI per mese (Enna): FORNITO vs CORRETTO ====")
print("(in uno SPI corretto la media di ogni mese deve essere ~0)")
print(t1.to_string(index=False))

# ---------- TAB 2: riepilogo statistico ----------
rows = []
for k in [1, 2, 3]:
    for lab, ser in [("fornito", provided[k]), ("corretto", proper[k])]:
        v = ser.values[np.isfinite(ser.values)]
        rows.append({"indice": f"SPI{k}", "versione": lab,
                     "media": round(v.mean(), 3), "std": round(v.std(), 3),
                     "min": round(v.min(), 2), "max": round(v.max(), 2),
                     "pct_|SPI|>3": round(100 * np.mean(np.abs(v) > 3), 2)})
t2 = pd.DataFrame(rows)
t2.to_csv(os.path.join(OUTD, "tab2_riepilogo_Enna.csv"), index=False)
print("\n==== TAB 2 - riepilogo statistico (Enna) ====")
print("(SPI corretto deve avere media~0, std~1, niente |SPI|>3-4)")
print(t2.to_string(index=False))

# ---------- TAB 3: esempio concreto, anno 2002 (annata secca) ----------
yr = 2002
rows = []
for m in range(1, 13):
    ts = pd.Timestamp(yr, m, 1)
    rows.append({
        "data": ts.strftime("%Y-%m"),
        "precip_mese_mm": round(float(precip_enna[times.get_loc(ts)]), 1),
        "accum_1m_mm": round(float(acc[1][ts]), 1),
        "SPI1_fornito": round(float(provided[1][ts]), 2),
        "SPI1_corretto": round(float(proper[1][ts]), 2),
        "accum_3m_mm": round(float(acc[3][ts]), 1) if pd.notna(acc[3][ts]) else None,
        "SPI3_fornito": round(float(provided[3][ts]), 2),
        "SPI3_corretto": round(float(proper[3][ts]), 2) if pd.notna(proper[3][ts]) else None,
    })
t3 = pd.DataFrame(rows)
t3.to_csv(os.path.join(OUTD, f"tab3_esempio_{yr}_Enna.csv"), index=False)
print(f"\n==== TAB 3 - esempio concreto Enna, anno {yr} ====")
print("(guarda i mesi estivi: lo SPI1 fornito li segna molto negativi anche se e' la normale siccita' estiva)")
print(t3.to_string(index=False))

print("\nCSV salvati in", OUTD)
