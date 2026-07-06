"""Verifica la tesi del report ('siccita' dominante dopo il 2006, >70% del
territorio') usando lo SPI RICALCOLATO. Per ogni periodo e scala calcola:
  - media spaziale dell'SPI sull'isola;
  - % di territorio con SPI medio < 0 (in deficit) e < -0.5 (siccita' apprezzabile).
Confronta anche col dato fornito."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import pandas as pd
import common

OUTD = os.path.join(common.OUT, "data")
PERIODS = [(1951, 1968), (1969, 1987), (1988, 2005), (2006, 2024)]
pd.set_option("display.width", 220)

rows = []
for scale in [1, 2, 3]:
    rec = common.load_spi_recomputed(scale).load()
    prov = common.load_spi(scale, center=False).load()
    yr_r = rec["time.year"]; yr_p = prov["time.year"]
    for (y0, y1) in PERIODS:
        m_rec = rec.where((yr_r >= y0) & (yr_r <= y1), drop=True).mean("time").values
        m_prov = prov.where((yr_p >= y0) & (yr_p <= y1), drop=True).mean("time").values
        cr = m_rec[np.isfinite(m_rec)]
        cp = m_prov[np.isfinite(m_prov)]
        rows.append({
            "indice": f"SPI{scale}", "periodo": f"{y0}-{y1}",
            "media_isola_RICALC": round(float(cr.mean()), 3),
            "%terr_deficit_RICALC": round(100 * np.mean(cr < 0), 0),
            "%terr_siccita_RICALC(<-0.5)": round(100 * np.mean(cr < -0.5), 0),
            "media_isola_FORNITO": round(float(cp.mean()), 3),
            "%terr_deficit_FORNITO": round(100 * np.mean(cp < 0), 0),
        })
    rec.close(); prov.close()

t = pd.DataFrame(rows)
t.to_csv(os.path.join(OUTD, "analisi_periodi_siccita.csv"), index=False)
print("==== Siccita' per periodo: SPI RICALCOLATO vs FORNITO ====")
print("(media isola: <0 = periodo piu' secco della media 1951-2024)")
print(t.to_string(index=False))

print("\n--- sintesi: periodo piu' SECCO per scala (SPI ricalcolato) ---")
for scale in [1, 2, 3]:
    sub = t[t.indice == f"SPI{scale}"]
    drow = sub.loc[sub["media_isola_RICALC"].idxmin()]
    print(f"  SPI{scale}: piu' secco = {drow.periodo}  (media isola {drow.media_isola_RICALC})")
