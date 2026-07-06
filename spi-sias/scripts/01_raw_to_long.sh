#!/usr/bin/env bash
# 01 - Da raw (Excel SIAS) a dataset long/tidy standardizzati (CSV)
#
# INPUT:
#   data/raw/Serie_SPI_SIAS_2026-05/*.xlsx  (96 file, uno per stazione)
#       layout: A1 = nome stazione; riga 2 = header (date, spi3, spi6, spi12,
#       spi24, spi48); righe successive = serie mensile. Decimali con VIRGOLA,
#       -99 = dato mancante.
#   data/raw/SPI_SICILIA_2026-05.xlsx       (file aggregato, sola scala SPI-3)
#       layout: header = nomi stazione; 1a riga dati = sigle provincia;
#       colonna "date" = seriale Excel; colonna "MEDIA REGIONALE". Decimali PUNTO.
#   scripts/crosswalk.csv                   (mappa slug-file -> nome stazione)
#   data/raw/StazioniSias2013_shapefile_ED50/StazioniSias2013.shp (coordinate stazioni)
#       shapefile senza .prj: coordinate UTM ED50 fuso 33N (EPSG:23033), riproiettate
#       a WGS84 (EPSG:4326) qui via duckdb spatial. Nessun file intermedio.
#
# OUTPUT (tutti standardizzati: decimali con PUNTO, date ISO YYYY-MM-DD, NA = vuoto):
#   data/spi_sias_long.csv              tabella principale long/tidy
#   data/spi_sias_media_regionale.csv   media regionale SPI-3
#   data/anagrafica_stazioni.csv        anagrafica stazioni con lat/lon
#
# Standardizzazioni applicate rispetto ai raw:
#   - unione dei 96 file in un'unica tabella + unpivot delle 5 scale SPI
#     (wide -> long: una riga per stazione x mese x scala);
#   - decimali: virgola -> punto;
#   - sentinella -99 -> valore mancante (cella vuota / NULL);
#   - date: seriale Excel / stringa -> ISO YYYY-MM-DD;
#   - nomi stazione allineati al nome ufficiale (via crosswalk.csv);
#   - coordinate lat/lon dallo shapefile ED50 riproiettate a WGS84 (in anagrafica).
set -euo pipefail
cd "$(dirname "$0")/.."

SRC=data/raw/Serie_SPI_SIAS_2026-05
AGG=data/raw/SPI_SICILIA_2026-05.xlsx
CW=scripts/crosswalk.csv
SHP=data/raw/StazioniSias2013_shapefile_ED50/StazioniSias2013.shp
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# 1) Stack dei 96 file per-stazione in formato long (unpivot delle 5 scale).
#    Lo slug della stazione e' ricavato dal nome file; il range parte da A2 per
#    saltare la cella A1 (nome stazione) e usare la riga 2 come header.
{
  echo "LOAD excel;"
  echo "COPY ("
  first=1
  for f in "$SRC"/*.xlsx; do
    slug="$(basename "$f" _2026-05_SPI_M_03_06_12_24_48.xlsx)"
    [ "$first" -eq 0 ] && echo "UNION ALL"
    first=0
    printf "SELECT '%s' AS station_slug, \"date\" AS date_raw, ts, val FROM (SELECT * FROM read_xlsx('%s', all_varchar=true, range='A2:F1048576', header=true)) UNPIVOT (val FOR ts IN (spi3, spi6, spi12, spi24, spi48))\n" "$slug" "$f"
  done
  echo ") TO '$TMP/stacked.csv' (HEADER, DELIMITER ',');"
} | duckdb

# 2) Pulizia, join con provincia (file aggregato) e coordinate (shapefile), output CSV.
duckdb <<SQL
LOAD excel; LOAD spatial;

CREATE TABLE cw     AS SELECT * FROM read_csv('$CW', header=true);
CREATE TABLE agg    AS SELECT * FROM read_xlsx('$AGG', all_varchar=true);
-- coordinate: dallo shapefile ED50 (EPSG:23033) -> WGS84 (EPSG:4326), riproiettate qui
-- (always_xy: lon=x, lat=y); piu' le coordinate stimate per stazioni assenti dallo
-- shapefile, definite inline (finiscono nell'anagrafica con la relativa nota).
CREATE TABLE coords AS
  SELECT STAZIONE AS station,
         round(ST_Y(ST_Transform(geom, 'EPSG:23033', 'EPSG:4326', always_xy := true)), 6) AS lat,
         round(ST_X(ST_Transform(geom, 'EPSG:23033', 'EPSG:4326', always_xy := true)), 6) AS lon,
         NULL AS nota
  FROM ST_Read('$SHP')
  UNION ALL
  SELECT * FROM (VALUES
    ('Linguaglossa Etna Nord', 37.7903, 15.0341,
     'coordinata stimata per georeferenziazione dalla mappa ufficiale SIAS (stazione assente nello shapefile 2013)')
  ) AS t(station, lat, lon, nota);
CREATE TABLE stk    AS SELECT * FROM read_csv('$TMP/stacked.csv', header=true, all_varchar=true);

-- province: la riga delle sigle e' l'unica con "date" NULL nel file aggregato
CREATE TABLE prov AS
  SELECT station, provincia FROM (
    SELECT * FROM agg WHERE "date" IS NULL LIMIT 1
  ) UNPIVOT (provincia FOR station IN (COLUMNS(* EXCLUDE ("date","mese","MEDIA REGIONALE"))));

CREATE TABLE long AS
SELECT
  cw.station,
  s.station_slug,
  p.provincia,
  (c.station IS NOT NULL) AS has_coords,
  CAST(s.date_raw AS DATE)                              AS date,
  CAST(regexp_replace(s.ts,'spi','') AS INTEGER)        AS timescale_months,
  CASE WHEN replace(s.val,',','.') = '-99' THEN NULL
       ELSE CAST(replace(s.val,',','.') AS DOUBLE) END  AS spi
FROM stk s
JOIN cw USING (station_slug)
LEFT JOIN prov   p ON p.station = cw.station
LEFT JOIN coords c ON c.station = cw.station;

-- Pantelleria e' assente dal file aggregato (niente provincia): impostata a TP
UPDATE long SET provincia='TP' WHERE station='Pantelleria' AND provincia IS NULL;

COPY (SELECT * FROM long ORDER BY station, timescale_months, date)
  TO 'data/spi_sias_long.csv' (HEADER, DELIMITER ',');

-- anagrafica: una riga per stazione, con provincia e coordinate lat/lon
COPY (
  SELECT DISTINCT l.station, l.station_slug, l.provincia, l.has_coords, c.lat, c.lon, c.nota
  FROM long l LEFT JOIN coords c ON c.station = l.station
  ORDER BY l.station
) TO 'data/anagrafica_stazioni.csv' (HEADER, DELIMITER ',');

-- media regionale (solo SPI-3): seriale Excel -> data ISO
COPY (
  SELECT CAST(DATE '1899-12-30' + CAST("date" AS INTEGER) * INTERVAL 1 DAY AS DATE) AS date,
         3 AS timescale_months,
         CASE WHEN "MEDIA REGIONALE"='-99' THEN NULL
              ELSE CAST("MEDIA REGIONALE" AS DOUBLE) END AS spi_media_regionale
  FROM agg WHERE TRY_CAST("date" AS INTEGER) IS NOT NULL
  ORDER BY date
) TO 'data/spi_sias_media_regionale.csv' (HEADER, DELIMITER ',');
SQL

echo "OK -> data/spi_sias_long.csv, data/spi_sias_media_regionale.csv, data/anagrafica_stazioni.csv"
