# Riproduzione delle analisi del report "Anomalie climatiche e siccità in Sicilia (1951–2024)"

Questo documento riassume la riproduzione dei dati e delle figure del report
`docs/report_amir.md` a partire dai dataset forniti in `data/`.

## 1. Dati disponibili vs dati richiesti dal report

| Variabile | File | Stato |
|---|---|---|
| Precipitazione mensile | `Sicily_ISPRA_precip_a1951_2024.nc` (var `precip`) | ✅ disponibile |
| SPI a 1 mese | `Sicily_SPI_1_predicted_1951_2024.nc.nc` (var `SPI_pred`) | ✅ disponibile (con bias, vedi §4) |
| SPI a 2 mesi | `Sicily_SPI_2_predicted_1951_2024.nc` (var `SPI_pred`) | ✅ disponibile |
| SPI a 3 mesi | `Sicily_SPI_3_predicted_1951_2024.nc.nc` (var `SPI_pred`) | ✅ disponibile |
| **Temperatura mensile** | — | ❌ **NON fornita** |
| DEM / elevazione | — | ❌ non fornito |
| Confini province | (ricavati) `data/sicilia_prov.geojson` | ✅ scaricati da ISTAT/confini-amministrativi.it |

Griglia comune: 382 (lat) × 348 (lon) ≈ 1 km, 888 passi mensili (gen 1951 – dic 2024),
estensione lat 35.50–38.96 N, lon 11.94–15.91 E. ~25.300 celle ricadono in Sicilia.

## 2. Figure riproducibili e corrispondenza con il report

| Figura | Contenuto | Riprodotta | File output |
|---|---|---|---|
| Fig. 1 | Mappa province (pannello destro) | ✅ | `fig01_province_map.png` |
| Fig. 1 | Elevazione Italia (pannello sinistro) | ❌ serve DEM esterno | — |
| Fig. 2 | Precipitazione mensile media + anomalie | ✅ | `fig02_precip_maps.png` |
| Fig. 3 | Densità precipitazione stagionale/provincia | ✅ | `fig03_precip_density.png` |
| Fig. 4 | Serie/anomalie precipitazione stagionale | ✅ | `fig04_precip_anomaly_ts.png` |
| Fig. 5 | Temperatura mensile media + anomalie | ❌ **no dati temperatura** | — |
| Fig. 6 | Densità temperatura stagionale | ❌ **no dati temperatura** | — |
| Fig. 7 | Anomalie temperatura stagionale | ❌ **no dati temperatura** | — |
| Fig. 8 | Mappe SPI 1/2/3 su 4 periodi | ✅ | `fig08_spi_maps.png` |
| Fig. 9 | Densità SPI 1/2/3 per provincia | ✅ | `fig09_spi_density.png` |
| Fig. 10 | Serie temporali SPI (media mobile) | ✅ | `fig10_spi_ts.png` |

**7 figure su 10 riprodotte.** Le 3 mancanti (Fig. 5–7) richiedono il dataset di
temperatura, che non è incluso tra i file forniti.

## 3. Metodologia

- **Province**: assegnazione di ogni cella della griglia a una delle 9 province
  tramite point-in-polygon (regionmask) sui confini ISTAT. Le serie provinciali
  sono medie spaziali delle celle interne alla provincia.
- **Stagioni** (meteorologiche): Inverno = DJF (dicembre assegnato all'anno
  successivo), Primavera = MAM, Estate = JJA, Autunno = SON.
- **Fig. 2 – anomalie spaziali**: per ogni mese, climatologia media per cella e
  anomalia relativa rispetto alla media regionale siciliana del mese,
  `anomalia% = (cella − media_regionale)/media_regionale`; i contorni 10–25%,
  25–50%, ≥50% evidenziano i massimi orografici (NE).
- **Fig. 4 – rilevamento anomalie**: punti che deviano oltre ±2σ dalla media
  stagionale 1951–2024 della provincia (etichettati con l'anno).
- **Fig. 8 – mappe SPI**: media dell'SPI su 4 periodi (1951‑68, 1969‑87,
  1988‑2005, 2006‑24); isolinea 0 = confine siccità/umidità.
- **Fig. 9/10**: KDE (gaussian) e media mobile a 12 mesi delle serie SPI provinciali.

## 4. Osservazioni importanti sui dati SPI

1. **Bias di SPI1.** Nel file fornito, SPI1 *non* è perfettamente standardizzato:
   media ≈ **−0.44**, σ ≈ 0.82 (un SPI corretto ha media 0, σ 1). SPI2 e SPI3
   sono invece regolari (media ≈ 0, σ ≈ 1). Per riprodurre l'aspetto delle figure
   del report (dove SPI1 è centrato su 0) SPI1 è stato **centrato per cella**
   (sottraendo la media temporale di ciascuna cella). SPI2/SPI3 sono usati grezzi.
   I dati grezzi restano accessibili con `load_spi(scale, center=False)`.

2. **Il periodo 2006–2024 non è il più secco in media regionale.** La media
   spaziale siciliana di SPI2/SPI3 per periodo è:

   | Indice | 1951‑68 | 1969‑87 | 1988‑2005 | 2006‑24 |
   |---|---|---|---|---|
   | SPI2 | −0.04 | −0.07 | −0.05 | **+0.02** |
   | SPI3 | −0.04 | −0.07 | −0.08 | **+0.02** |

   I dati mostrano che, *in media sull'intera isola*, il 2006–2024 è leggermente
   più umido dei decenni centrali. Il segnale di siccità del periodo recente è
   **confinato all'interno e al SW** (Enna, Caltanissetta, Agrigento), mentre il
   NE (Messina, Etna) resta marcatamente umido e compensa la media (vedi Fig. 8).
   La narrazione del report ("siccità dominante su >70% del territorio dopo il
   2006") va quindi letta come pattern spaziale interno, non come deficit medio
   regionale: su quest'ultimo punto i dati forniti sono più sfumati del testo.

## 4-bis. SPI RICALCOLATO secondo la definizione standard

Poiché i file `SPI_predicted` non sono SPI propriamente standardizzati (vedi §4 e
sotto), lo SPI è stato **ricalcolato dalla precipitazione** seguendo McKee et al.
(1993) e le linee guida WMO (2012):

- accumulo a *k* mesi (rolling sum);
- per **ogni cella e ogni mese di calendario** separatamente: fit Gamma sui valori
  positivi con lo stimatore di Thom (1958), distribuzione mista per gli zeri
  `H(x)=q+(1−q)·Γ(x)`, trasformazione `SPI=Φ⁻¹(H(x))`;
- periodo di riferimento 1951–2024.

Output NetCDF: `data/Sicily_SPI_{1,2,3}_recomputed_1951_2024.nc` (var `SPI`).
Script: `scripts/compute_spi.py`. Figure: `fig08/09/10_..._CORRETTO.png`.

**Verifica di correttezza** (`scripts/verify_spi.py`, CSV `verify_A..D`):

- media e std **per ogni mese di calendario** ≈ 0 e ≈ 1 (10–12 mesi su 12); unica
  deviazione attesa: estate per SPI1 (Lug media 0.43, std 0.62) per l'eccesso di
  mesi a pioggia ≈ 0 — limite intrinseco e noto dello SPI a breve scala, non un
  errore di metodo;
- frequenza delle classi di siccità ≈ alle probabilità teoriche N(0,1)
  (siccità estrema 1.6–1.9 % osservato vs 2.3 % teorico);
- per-cella: std mediana 0.94 (SPI1) → 1.00 (SPI3), media mediana ≈ 0.

**Differenza con i file forniti** (`verify_ciclo_stagionale_confronto.png`): lo SPI
fornito ha un forte **ciclo stagionale residuo** (media +1 in inverno, −1.5 in
estate) che uno SPI corretto **non deve avere**; lo SPI ricalcolato è piatto a 0.
Tabelle dimostrative su pochi punti: `tab1/2/3_*_Enna.csv`.

## 4-ter. Risultato chiave: il 2006–2024 NON è il periodo più secco

Con lo SPI **ricalcolato** (`scripts/analisi_periodi.py`,
`analisi_periodi_siccita.csv`), media spaziale sull'isola e % di territorio in
deficit (SPI medio < 0) per periodo:

| Indice | metrica | 1951‑68 | 1969‑87 | 1988‑2005 | 2006‑24 |
|---|---|---|---|---|---|
| SPI3 | media isola | +0.07 | **−0.125** | −0.06 | **+0.12** |
| SPI3 | % terr. in deficit | 25 % | **92 %** | 75 % | **9 %** |
| SPI2 | media isola | +0.07 | **−0.089** | −0.02 | **+0.10** |

→ Il periodo **più secco è il 1969–1987** (fino al 92 % del territorio in deficit);
il **2006–2024 è il più umido** dei quattro (solo ~9 % in deficit). Questo
**contraddice** la tesi del report ("dopo il 2006 la siccità diventa dominante,
SPI3 su >70 % del territorio"). Lo stesso emerge, in forma più sfumata, anche dai
file forniti.

**Caveat onesto:** lo SPI misura **solo la precipitazione**. Il periodo recente può
comunque soffrire di stress idrico per via delle **temperature più alte**
(maggiore evapotraspirazione), che però **non possiamo verificare** perché il
dataset di temperatura non è stato fornito. Quindi: la *pioggia* non mostra il
2006–2024 come il più secco, ma ciò non esclude una siccità agricola/idrologica
guidata dal caldo.

## 5. Dati tabellari esportati (`output/data/`)

Precipitazione:
- `precip_mensile_provincia_mm.csv` — serie mensile precip media per provincia
- `precip_stagionale_provincia.csv` — totali stagionali per anno/provincia (base Fig. 3/4)
- `precip_climatologia_mensile_provincia.csv` — climatologia mensile per provincia

SPI (file forniti):
- `spi_mensile_provincia.csv`, `spi_medie_periodo_provincia.csv`,
  `spi_statistiche_siccita_provincia.csv`

SPI ricalcolato / diagnostica:
- `verify_A_media_std_per_mese.csv` — media/std SPI ricalcolato per mese (≈0, ≈1)
- `verify_B_riepilogo_globale.csv` — ricalcolato vs fornito
- `verify_C_per_cella.csv` — distribuzione di media/std tra le celle
- `verify_D_classi_siccita.csv` — frequenze classi vs teoria N(0,1)
- `analisi_periodi_siccita.csv` — siccità per periodo (il risultato chiave)
- `tab1/2/3_*_Enna.csv` — esempi a pochi punti del problema dei file forniti

## 6. Come rieseguire

```bash
# ambiente (uv)
uv venv /tmp/climenv --python 3.12
VIRTUAL_ENV=/tmp/climenv uv pip install numpy pandas xarray netCDF4 matplotlib scipy geopandas shapely regionmask

# figure
for s in 01_province_map 02_precip_maps 03_precip_density 04_precip_anomaly_ts \
         08_spi_maps 09_spi_density 10_spi_ts; do
  /tmp/climenv/bin/python3 scripts/fig$s.py
done
/tmp/climenv/bin/python3 scripts/export_data.py
```
