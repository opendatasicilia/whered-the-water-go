"""Controllo di qualita' (QC) sui file SPI FORNITI vs SPI RICALCOLATO.

Verifica le tre proprieta' falsificabili che definiscono uno SPI (McKee 1993,
WMO 2012), riproducendo i numeri del documento docs/REPORT_VERIFICA_SPI:

  Test A  -> media e deviazione standard per OGNI mese di calendario   (atteso ~0 e ~1)
  Test B  -> statistiche globali, min/max e frequenza delle code        (z-score N(0,1))
  Test C  -> frequenza delle classi di siccita' vs probabilita' N(0,1)

I file forniti sono aperti grezzi (var 'SPI_pred', SENZA ri-centraggio); quelli
ricalcolati usano la var 'SPI'. Stampa le tabelle e salva un riepilogo in
output/data/check_provided_spi_{A,B,C}.csv.

Uso:  python3 scripts/check_provided_spi.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import pandas as pd
import xarray as xr
from scipy.stats import norm
import common

OUTD = os.path.join(common.OUT, "data")
os.makedirs(OUTD, exist_ok=True)
pd.set_option("display.width", 200)

# classi di siccita' standard e probabilita' teoriche da N(0,1)
CLASSI = [("estrema (<=-2)", -np.inf, -2.0),
          ("severa (da -2 a -1.5)", -2.0, -1.5),
          ("moderata (da -1.5 a -1)", -1.5, -1.0),
          ("lieve secco (da -1 a 0)", -1.0, 0.0),
          ("lieve umido (da 0 a 1)", 0.0, 1.0),
          ("umido marcato (oltre 1)", 1.0, np.inf)]


def load_flat(path, var):
    """Carica una variabile (time, lat, lon) e restituisce (cubo, mesi)."""
    ds = xr.open_dataset(path)
    da = ds[var].transpose("time", "lat", "lon")
    v = da.values.astype("float64")
    mon = da["time.month"].values
    ds.close()
    return v, mon


# sorgenti: (etichetta, scala, path, variabile)
SORG = []
for k in (1, 2, 3):
    SORG.append((f"SPI{k} fornito", k, common.SPI_NC[k], "SPI_pred"))
    SORG.append((f"SPI{k} ricalc.", k, common.SPI_RECOMP[k], "SPI"))

rows_A, rows_B, rows_C = [], [], []

print("=" * 78)
print("QC SPI — file forniti (SPI_pred) vs ricalcolato (SPI). Atteso: N(0,1) per mese.")
print("=" * 78)

for lab, k, path, var in SORG:
    v, mon = load_flat(path, var)
    fin = v[np.isfinite(v)]

    # ---- Test A: media/std per mese di calendario ----
    medie = []
    for m in range(1, 13):
        x = v[mon == m]
        x = x[np.isfinite(x)]
        medie.append(x.mean())
        rows_A.append((lab, common.MESI[m - 1], round(float(x.mean()), 3),
                       round(float(x.std()), 3)))
    max_abs_media = float(np.max(np.abs(medie)))

    # ---- Test B: globali e code ----
    g_mean, g_std = float(fin.mean()), float(fin.std())
    g_min, g_max = float(fin.min()), float(fin.max())
    p3 = 100 * np.mean(np.abs(fin) > 3)
    p4 = 100 * np.mean(np.abs(fin) > 4)
    rows_B.append((lab, round(g_mean, 3), round(g_std, 3), round(g_min, 2),
                   round(g_max, 2), round(float(p3), 3), round(float(p4), 4),
                   round(max_abs_media, 3)))

    # ---- Test C: frequenza classi ----
    for nome, lo, hi in CLASSI:
        oss = 100 * np.mean((fin > lo) & (fin <= hi))
        teo = 100 * (norm.cdf(hi) - norm.cdf(lo))
        rows_C.append((lab, nome, round(float(oss), 2), round(float(teo), 2)))

    print(f"\n[{lab}]  globale: media={g_mean:+.3f} std={g_std:.3f} "
          f"min={g_min:+.2f} max={g_max:+.2f} | "
          f"max|media mese|={max_abs_media:.2f} (atteso ~0.1) | "
          f"|SPI|>4={p4:.4f}% (teor. 0.006%)")

tA = pd.DataFrame(rows_A, columns=["sorgente", "mese", "media", "std"])
tB = pd.DataFrame(rows_B, columns=["sorgente", "media", "std", "min", "max",
                                   "pct_|SPI|>3", "pct_|SPI|>4", "max_|media_mese|"])
tC = pd.DataFrame(rows_C, columns=["sorgente", "classe", "oss_%", "teorica_%"])
tA.to_csv(os.path.join(OUTD, "check_provided_spi_A.csv"), index=False)
tB.to_csv(os.path.join(OUTD, "check_provided_spi_B.csv"), index=False)
tC.to_csv(os.path.join(OUTD, "check_provided_spi_C.csv"), index=False)

print("\n==== TEST A — media SPI per mese (pivot; atteso ~0 ovunque) ====")
print(tA.pivot(index="mese", columns="sorgente", values="media")
        .reindex(common.MESI).to_string())
print("\n==== TEST B — statistiche globali e code ====")
print(tB.to_string(index=False))
print("\n==== TEST C — frequenza classi vs teoria N(0,1) ====")
print(tC.pivot(index="classe", columns="sorgente", values="oss_%").to_string())

print(f"\nCSV salvati in {OUTD}: check_provided_spi_{{A,B,C}}.csv")
