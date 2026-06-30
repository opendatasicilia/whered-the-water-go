"""Utility condivise per la riproduzione delle analisi del report Sicilia 1951-2024.

Dati disponibili:
  - data/Sicily_ISPRA_precip_a1951_2024.nc      var: precip   (time, lat, lon)
  - data/Sicily_SPI_1_predicted_1951_2024.nc.nc var: SPI_pred (lat, lon, time)
  - data/Sicily_SPI_2_predicted_1951_2024.nc    var: SPI_pred (lat, lon, time)
  - data/Sicily_SPI_3_predicted_1951_2024.nc.nc var: SPI_pred (lat, lon, time)
  - data/sicilia_prov.geojson  confini 9 province (ISTAT via confini-amministrativi.it)
"""
import os
import numpy as np
import xarray as xr

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, "data")
OUT = os.path.join(BASE, "output")

PRECIP_NC = os.path.join(DATA, "Sicily_ISPRA_precip_a1951_2024.nc")
SPI_NC = {
    1: os.path.join(DATA, "Sicily_SPI_1_predicted_1951_2024.nc.nc"),
    2: os.path.join(DATA, "Sicily_SPI_2_predicted_1951_2024.nc"),
    3: os.path.join(DATA, "Sicily_SPI_3_predicted_1951_2024.nc.nc"),
}
GEOJSON = os.path.join(DATA, "sicilia_prov.geojson")

# Ordine province come nelle figure del report (3 colonne x 3 righe)
PROV_ORDER = ["Palermo", "Messina", "Catania",
              "Enna", "Trapani", "Caltanissetta",
              "Siracusa", "Ragusa", "Agrigento"]

MESI = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
        "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]

# Stagioni meteorologiche
SEASONS = {
    "Inverno": [12, 1, 2],
    "Primavera": [3, 4, 5],
    "Estate": [6, 7, 8],
    "Autunno": [9, 10, 11],
}
SEASON_COLORS = {"Inverno": "blue", "Primavera": "green",
                 "Estate": "orange", "Autunno": "red"}


def load_precip():
    ds = xr.open_dataset(PRECIP_NC)
    return ds["precip"]


def load_spi(scale, center=True):
    """Carica SPI alla scala richiesta (var SPI_pred).

    NB: nei file forniti SPI1 ha un bias negativo (media ~ -0.44, std ~0.82),
    quindi non e' perfettamente standardizzato come SPI2/SPI3 (media ~0, std ~1).
    Con center=True si sottrae la media temporale di ciascuna cella, riportando
    ogni cella a media 0 (definizione di anomalia SPI) e riproducendo l'aspetto
    delle figure del report. I dati grezzi restano disponibili con center=False.
    """
    ds = xr.open_dataset(SPI_NC[scale])
    da = ds["SPI_pred"].transpose("time", "lat", "lon")
    if center:
        da = da - da.mean("time")
    return da


def build_province_mask(lat, lon, cache=os.path.join(DATA, "prov_mask.npy")):
    """Restituisce un array 2D (lat, lon) di indici provincia (-1 = fuori).
    L'indice corrisponde alla posizione in PROV_ORDER. Cache su disco."""
    if os.path.exists(cache):
        idx = np.load(cache)
        if idx.shape == (lat.size, lon.size):
            return idx
    import geopandas as gpd
    import regionmask
    gdf = gpd.read_file(GEOJSON).to_crs(4326)
    gdf = gdf.set_index("provincia").loc[PROV_ORDER].reset_index()
    gdf["num"] = range(len(PROV_ORDER))
    regions = regionmask.from_geopandas(gdf, names="provincia", numbers="num")
    mask = regions.mask(lon, lat)  # NaN fuori, altrimenti numero regione
    idx = np.where(np.isnan(mask.values), -1, mask.values).astype(np.int16)
    np.save(cache, idx)
    return idx


def province_monthly_mean(da, mask, prov_idx):
    """Serie mensile (time,) media spaziale sulle celle della provincia prov_idx."""
    sel = (mask == prov_idx)
    import numpy as np
    arr = da.values  # (time, lat, lon)
    m = sel[np.newaxis, :, :]
    vals = np.where(m, arr, np.nan)
    return np.nanmean(vals.reshape(arr.shape[0], -1), axis=1)


def seasonal_totals(monthly, times, agg="sum"):
    """Da serie mensile -> dict stagione -> (anni, valori). agg='sum' (precip) o 'mean' (SPI)."""
    import numpy as np, pandas as pd
    s = pd.Series(monthly, index=pd.DatetimeIndex(times))
    out = {}
    for name, months in SEASONS.items():
        sub = s[s.index.month.isin(months)]
        yr = sub.index.year.values.copy()
        # Dicembre appartiene all'inverno dell'anno successivo
        if name == "Inverno":
            yr = np.where(sub.index.month.values == 12, yr + 1, yr)
        df = pd.DataFrame({"y": yr, "v": sub.values})
        g = df.groupby("y")["v"].agg(agg)
        out[name] = (g.index.values, g.values)
    return out


SPI_RECOMP = {k: os.path.join(DATA, f"Sicily_SPI_{k}_recomputed_1951_2024.nc")
              for k in [1, 2, 3]}


def load_spi_recomputed(scale):
    """Carica lo SPI ricalcolato (definizione standard, var 'SPI')."""
    ds = xr.open_dataset(SPI_RECOMP[scale])
    return ds["SPI"].transpose("time", "lat", "lon")
