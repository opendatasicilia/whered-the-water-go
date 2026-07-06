"""Calcolo dello SPI secondo la definizione standard (McKee et al. 1993, WMO 2012).

Metodo (per ogni scala k = 1, 2, 3 mesi):
  1. accumulo della precipitazione su finestra mobile di k mesi;
  2. per OGNI cella e OGNI mese di calendario (gen, feb, ...) separatamente:
     - frazione di accumuli nulli q (distribuzione mista per gli zeri);
     - fit di una distribuzione Gamma sui valori positivi con lo stimatore
       di Thom (1958), forma chiusa e operativa:
           A = ln(media) - media(ln);  alpha = (1+sqrt(1+4A/3))/(4A);  beta = media/alpha
     - CDF mista  H(x) = q + (1-q)*Gamma_cdf(x; alpha, beta);
     - SPI = Phi^-1(H(x))  (quantile della normale standard).
Periodo di riferimento per il fit: intero 1951-2024.
Output: data/Sicily_SPI_{k}_recomputed_1951_2024.nc  (var 'SPI', dims time,lat,lon).
"""
import os
import numpy as np
import xarray as xr
from scipy.special import gammainc
from scipy.stats import norm

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
PRECIP = os.path.join(DATA, "Sicily_ISPRA_precip_a1951_2024.nc")

ds = xr.open_dataset(PRECIP)
pr = ds["precip"]
P = pr.values.astype("float64")              # (time, lat, lon)
T, NLAT, NLON = P.shape
months = pr["time.month"].values
time = pr.time.values
lat = pr.lat.values
lon = pr.lon.values
ds.close()

MIN_YEARS = 20        # minimo anni positivi per fittare una cella/mese


def rolling_sum(P, k):
    """Somma mobile su k mesi lungo l'asse tempo (NaN per i primi k-1)."""
    cs = np.cumsum(P, axis=0)
    cs = np.concatenate([np.zeros((1, NLAT, NLON)), cs], axis=0)  # cs[t]=sum P[0:t]
    acc = np.full_like(P, np.nan)
    # acc[t] = somma su [t-k+1 .. t] = cs[t+1] - cs[t+1-k], per t >= k-1
    acc[k - 1:] = cs[k:] - cs[: T - (k - 1)]
    return acc


def spi_for_scale(k):
    acc = rolling_sum(P, k)
    SPI = np.full_like(acc, np.nan)
    for m in range(1, 13):
        idx = np.where(months == m)[0]
        idx = idx[idx >= k - 1]                # solo accumuli validi
        X = acc[idx]                           # (n_anni, lat, lon)
        finite = np.isfinite(X)
        n = finite.sum(0)
        # frazione di zeri (tra i valori finiti)
        nz = np.where(finite, X == 0, False).sum(0)
        with np.errstate(invalid="ignore", divide="ignore"):
            q = np.where(n > 0, nz / np.maximum(n, 1), np.nan)
            # statistiche sui positivi
            Xpos = np.where(finite & (X > 0), X, np.nan)
            npos = np.isfinite(Xpos).sum(0)
            mean_pos = np.nanmean(Xpos, axis=0)
            mean_log = np.nanmean(np.log(Xpos), axis=0)
            A = np.log(mean_pos) - mean_log
            alpha = (1.0 + np.sqrt(1.0 + 4.0 * A / 3.0)) / (4.0 * A)
            beta = mean_pos / alpha
            # CDF gamma per ogni anno (broadcast su lat,lon)
            G = gammainc(alpha[None, :, :], X / beta[None, :, :])   # regolarizzata, x=0 -> 0
            H = q[None, :, :] + (1.0 - q[None, :, :]) * G
        H = np.clip(H, 1e-6, 1 - 1e-6)
        z = norm.ppf(H)
        # invalida celle/mesi non fittabili
        bad = (npos < MIN_YEARS) | ~np.isfinite(alpha) | (A <= 0)
        z = np.where(bad[None, :, :], np.nan, z)
        z = np.where(finite, z, np.nan)
        SPI[idx] = z
    return SPI


for k in [1, 2, 3]:
    print(f"calcolo SPI{k} ...", flush=True)
    spi = spi_for_scale(k)
    da = xr.DataArray(spi.astype("float32"), dims=("time", "lat", "lon"),
                      coords={"time": time, "lat": lat, "lon": lon}, name="SPI")
    da.attrs.update(long_name=f"Standardized Precipitation Index ({k}-month)",
                    method="Gamma (Thom 1958 MLE) + zero-handling, per-cell per-calendar-month",
                    reference_period="1951-2024", scale_months=k)
    out = os.path.join(DATA, f"Sicily_SPI_{k}_recomputed_1951_2024.nc")
    da.to_netcdf(out, encoding={"SPI": {"zlib": True, "complevel": 4}})
    fin = spi[np.isfinite(spi)]
    print(f"  salvato {out}")
    print(f"  globale: media={fin.mean():+.4f} std={fin.std():.4f} "
          f"min={fin.min():.2f} max={fin.max():.2f} |SPI|>3={100*np.mean(np.abs(fin)>3):.2f}%")
print("FATTO")
