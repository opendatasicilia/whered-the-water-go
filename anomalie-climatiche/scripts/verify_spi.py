"""Verifica di correttezza dello SPI ricalcolato secondo le best practice.
Controlli:
  (A) media e std per OGNI mese di calendario (su tutte le celle e anni) -> ~0 e ~1;
  (B) riepilogo globale ricalcolato vs fornito;
  (C) per-cella: distribuzione di media e std (devono concentrarsi su 0 e 1);
  (D) frequenza delle classi di siccita' SPI (confronto con le attese teoriche).
Salva CSV in output/data/ e stampa le tabelle."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import pandas as pd
import common

OUTD = os.path.join(common.OUT, "data")
os.makedirs(OUTD, exist_ok=True)
pd.set_option("display.width", 200)

# classi SPI standard (McKee 1993) e probabilita' teoriche da N(0,1)
from scipy.stats import norm
CLASSI = [("estrema siccita' (<=-2)", -np.inf, -2.0),
          ("severa (-2,-1.5]", -2.0, -1.5),
          ("moderata (-1.5,-1]", -1.5, -1.0),
          ("lieve (-1,0]", -1.0, 0.0),
          ("umido lieve (0,1]", 0.0, 1.0),
          ("umido mod.+ (>1)", 1.0, np.inf)]


def month_stats(da):
    v = da.values
    mon = da["time.month"].values
    rows = []
    for m in range(1, 13):
        x = v[mon == m]
        x = x[np.isfinite(x)]
        rows.append((common.MESI[m - 1], round(float(x.mean()), 3), round(float(x.std()), 3)))
    return rows


rows_month = []
rows_glob = []
rows_cell = []
rows_cls = []
for k in [1, 2, 3]:
    rec = common.load_spi_recomputed(k).load()
    prov = common.load_spi(k, center=False).load()

    # (A) media/std per mese - ricalcolato
    for mese, mu, sd in month_stats(rec):
        rows_month.append((f"SPI{k}", mese, mu, sd))

    # (B) globale
    for lab, da in [("ricalcolato", rec), ("fornito", prov)]:
        v = da.values[np.isfinite(da.values)]
        rows_glob.append((f"SPI{k}", lab, round(v.mean(), 4), round(v.std(), 4),
                          round(float(v.min()), 2), round(float(v.max()), 2),
                          round(100 * np.mean(np.abs(v) > 3), 2)))

    # (C) per-cella: media e std nel tempo, poi distribuzione tra le celle
    cell_mu = rec.mean("time").values
    cell_sd = rec.std("time").values
    cm = cell_mu[np.isfinite(cell_mu)]
    cs = cell_sd[np.isfinite(cell_sd)]
    rows_cell.append((f"SPI{k}",
                      round(float(np.median(cm)), 3),
                      round(float(np.percentile(cm, 5)), 3),
                      round(float(np.percentile(cm, 95)), 3),
                      round(float(np.median(cs)), 3),
                      round(float(np.percentile(cs, 5)), 3),
                      round(float(np.percentile(cs, 95)), 3)))

    # (D) frequenza classi vs teoria
    v = rec.values[np.isfinite(rec.values)]
    for nome, lo, hi in CLASSI:
        oss = 100 * np.mean((v > lo) & (v <= hi))
        teo = 100 * (norm.cdf(hi) - norm.cdf(lo))
        rows_cls.append((f"SPI{k}", nome, round(oss, 1), round(teo, 1)))
    rec.close(); prov.close()

tA = pd.DataFrame(rows_month, columns=["indice", "mese", "media", "std"])
tA.to_csv(os.path.join(OUTD, "verify_A_media_std_per_mese.csv"), index=False)
tB = pd.DataFrame(rows_glob, columns=["indice", "versione", "media", "std", "min", "max", "pct_|SPI|>3"])
tB.to_csv(os.path.join(OUTD, "verify_B_riepilogo_globale.csv"), index=False)
tC = pd.DataFrame(rows_cell, columns=["indice", "media_cella_mediana", "media_p5", "media_p95",
                                      "std_cella_mediana", "std_p5", "std_p95"])
tC.to_csv(os.path.join(OUTD, "verify_C_per_cella.csv"), index=False)
tD = pd.DataFrame(rows_cls, columns=["indice", "classe", "oss_%", "teorica_%"])
tD.to_csv(os.path.join(OUTD, "verify_D_classi_siccita.csv"), index=False)

print("==== (A) media/std per mese - SPI RICALCOLATO (atteso: ~0 e ~1) ====")
print(tA.pivot(index="mese", columns="indice", values=["media", "std"]).reindex(common.MESI).to_string())
print("\n==== (B) riepilogo globale: ricalcolato vs fornito ====")
print(tB.to_string(index=False))
print("\n==== (C) per-cella (media e std nel tempo, distribuzione tra celle) ====")
print(tC.to_string(index=False))
print("\n==== (D) frequenza classi di siccita' vs probabilita' teorica N(0,1) ====")
print(tD.to_string(index=False))
print("\nCSV in", OUTD)
