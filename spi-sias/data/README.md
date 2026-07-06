# Dati SPI SIAS — versione long & tidy

Dataset ricavati dai file grezzi in `data/raw/` (serie SPI SIAS aggiornate a 2026-05).
Formato long/tidy, valori numerici con separatore `.`, date in ISO 8601 (`YYYY-MM-DD`),
coordinate in WGS84 (EPSG:4326), valori mancanti come cella vuota (NA). **Nessun dato perso.**

Gli script che generano questi file sono in `../scripts/` (vedi sotto).

## Da dove vengono: struttura dei file in `data/raw/`

I dati grezzi hanno due formati Excel diversi, entrambi **wide** e con convenzioni
locali (virgola decimale, sentinella `-99`, nomi/date non standard):

1. **`raw/Serie_SPI_SIAS_2026-05/*.xlsx`** — 96 file, uno per stazione.
   - cella `A1` = nome stazione; riga 2 = header `date, spi3, spi6, spi12, spi24, spi48`;
     righe successive = serie **mensile** (1991-01 → 2026-05).
   - una colonna per scala SPI (accumulo a 3/6/12/24/48 mesi) → formato **wide**.
   - decimali con **virgola** (`-0,27`); `-99` = dato mancante.
   - il nome stazione nel file (es. `agr_mand`) è uno **slug** abbreviato, non il nome esteso.

2. **`raw/SPI_SICILIA_2026-05.xlsx`** — file aggregato regionale (**solo scala SPI-3**).
   - header = nomi stazione estesi; una colonna per stazione → formato **wide**.
   - 1ª riga dati = sigle **provincia**; colonna `date` = **seriale Excel** (es. `33239`);
     colonna `mese` = indice progressivo; colonna `MEDIA REGIONALE`.
   - decimali con **punto**.

3. **`raw/StazioniSias2013_shapefile_ED50/`** — shapefile delle stazioni (95 punti).
   - **senza `.prj`**: SRS non dichiarato. Coordinate UTM (campi `UTM_E`/`UTM_N`) →
     Sicilia, fuso 33N; il nome cartella indica il datum ED50 → **EPSG:23033**.
   - riproiettato in lat/lon WGS84 dentro `01_raw_to_long.sh` (via duckdb spatial, senza file intermedi).

## Come è stata cambiata e standardizzata la struttura

Trasformazioni applicate dai grezzi agli output (script `01_raw_to_long.sh`):

| aspetto | raw | output standardizzato |
|---|---|---|
| forma tabella | wide (una colonna per scala / per stazione) | **long/tidy**: 1 riga per stazione × mese × scala |
| unione file | 96 file separati + 1 aggregato | un'unica tabella `spi_sias_long.csv` |
| decimali | virgola (`-0,27`) | **punto** (`-0.27`) |
| valori mancanti | sentinella `-99` | cella **vuota** (NA) |
| date | seriale Excel / stringa | **ISO** `YYYY-MM-DD` (primo giorno del mese) |
| nome stazione | slug abbreviato (`agr_mand`) | nome esteso ufficiale (`Agrigento Mandrascava`) |
| provincia | riga a parte nel file aggregato | colonna `provincia` sulla riga |
| coordinate | shapefile UTM ED50 (`.shp`) | colonne `lat`/`lon` WGS84 nell'anagrafica |

Il passaggio da slug a nome esteso usa `../scripts/crosswalk.csv` (mappa costruita a
mano e validata: vedi sezione Verifica). Le coordinate provengono dallo shapefile,
riproiettate a WGS84 e unite tramite il nome stazione.

## `spi_sias_long.csv` — tabella principale
Una riga per stazione × mese × scala temporale SPI (200.635 righe, 96 stazioni,
serie mensili 1991-01 → 2026-05, scale 3/6/12/24/48 mesi).

| colonna | descrizione |
|---|---|
| `station` | nome stazione (chiave di join con l'anagrafica) |
| `station_slug` | slug del file grezzo di origine (es. `agr_mand`) |
| `provincia` | sigla provincia (RG, EN, AG, …) |
| `has_coords` | `true` se la stazione ha coordinate nell'anagrafica |
| `date` | primo giorno del mese di riferimento (ISO `YYYY-MM-DD`) |
| `timescale_months` | scala di accumulo SPI in mesi: 3, 6, 12, 24, 48 |
| `spi` | valore SPI (vuoto = dato non disponibile) |

## `anagrafica_stazioni.csv` — anagrafica stazioni (con coordinate)
Una riga per stazione (96). Contiene le coordinate lat/lon: **rende superfluo un file
GeoJSON separato**.

| colonna | descrizione |
|---|---|
| `station` | nome stazione (chiave di join con `spi_sias_long.csv`) |
| `station_slug` | slug del file grezzo |
| `provincia` | sigla provincia |
| `has_coords` | `true` se sono disponibili le coordinate (ora tutte le 96) |
| `lat` | latitudine WGS84 (EPSG:4326) |
| `lon` | longitudine WGS84 (EPSG:4326) |
| `nota` | note per stazione (vuoto per le 95 da shapefile); per Linguaglossa Etna Nord segnala che la coordinata è stimata per georeferenziazione dalla mappa ufficiale SIAS |

## `spi_sias_media_regionale.csv` — media regionale (SPI-3)
Serie della media regionale fornita nel file aggregato `SPI_SICILIA_2026-05.xlsx`
(disponibile solo per la scala a 3 mesi). Colonne: `date`, `timescale_months` (=3),
`spi_media_regionale`.

## Note su copertura
- Tutte le **96** stazioni hanno coordinate e serie SPI.
- `Linguaglossa Etna Nord` **non è nello shapefile 2013**: la sua coordinata
  (15,0341 E / 37,7903 N) è stata **georeferenziata dalle mappe ufficiali SIAS** —
  rilevando il puntino-stazione "orfano" e stimando la trasformazione pixel→lon/lat con
  le altre stazioni come punti di controllo (RANSAC affine, RMS 0,39 km; coordinata stabile
  a ~10 m su 4 mappe). Segnalata nel campo `nota` dell'anagrafica.
- `Pantelleria` è nelle serie e nello shapefile, ma **non** nel file aggregato regionale
  (provincia impostata a `TP`).

## Script (in `../scripts/`)
- `01_raw_to_long.sh` — genera i tre CSV di questa cartella dai grezzi; include la
  riproiezione delle coordinate dallo shapefile ED50 a WGS84 (duckdb spatial).
- `02_validate.sh` — controlli di qualità sugli output.
- `crosswalk.csv` — mappa slug-file → nome stazione (input di `02`).
- `03_build_map_animation.py` — mappa animata SPI spazializzato (HTML autonomo in
  `../viz/web/spi_sias_animata.html`). Spedisce solo i valori mensili delle stazioni
  (~150 KB): il browser ricostruisce la superficie con spline a base radiale (kernel
  lineare, più fedele alle mappe SIAS della thin-plate — scelto per confronto deterministico)
  e la disegna classificando per-pixel (bande lisce). Colori/legenda a 13
  classi della mappa ufficiale SPI-3. Deps via uv (numpy scipy shapely pillow).
- `tps_core.js` — core spline in JS (incluso nell'HTML), verificato vs scipy da `test_tps.js` (node).
- `_map_template.html` — template dell'HTML animato.

## Verifica
La corrispondenza `station_slug → station` è stata validata confrontando i valori
SPI-3 delle serie per stazione con le colonne del file aggregato regionale:
39.962 coppie (stazione, data) combaciano con **0 discordanze** di valore e di NA.
Eseguibile con `bash ../scripts/02_validate.sh`.
