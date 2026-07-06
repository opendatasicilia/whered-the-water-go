#!/usr/bin/env bash
# 02 - Controlli di qualita' sugli output prodotti da 01_raw_to_long.sh
#
# Verifica che:
#   - non ci siano decimali con virgola ne' date non-ISO negli output;
#   - il crosswalk sia completo (96 slug <-> 96 file);
#   - i valori SPI-3 per stazione combacino con il file aggregato regionale
#     (validazione empirica della mappa slug -> nome: 0 discordanze attese).
set -euo pipefail
cd "$(dirname "$0")/.."

duckdb <<'SQL'
LOAD excel;

-- formato: decimali con punto, date ISO
SELECT 'spi con virgola (atteso 0)' AS check,
       COUNT(*)::VARCHAR AS val
FROM read_csv('data/spi_sias_long.csv', all_varchar=true) WHERE spi LIKE '%,%'
UNION ALL
SELECT 'date non-ISO (atteso 0)',
       COUNT(*)::VARCHAR
FROM read_csv('data/spi_sias_long.csv', all_varchar=true)
WHERE date NOT SIMILAR TO '\d{4}-\d{2}-\d{2}'
UNION ALL
SELECT 'stazioni distinte (atteso 96)',
       COUNT(DISTINCT station)::VARCHAR FROM read_csv('data/spi_sias_long.csv')
UNION ALL
SELECT 'anagrafica: righe (atteso 96)',
       COUNT(*)::VARCHAR FROM read_csv('data/anagrafica_stazioni.csv')
UNION ALL
SELECT 'anagrafica: con coordinate (atteso 96)',
       COUNT(*)::VARCHAR FROM read_csv('data/anagrafica_stazioni.csv') WHERE lat IS NOT NULL
UNION ALL
SELECT 'coords: lat fuori Sicilia 36-39 (atteso 0)',
       COUNT(*)::VARCHAR FROM read_csv('data/anagrafica_stazioni.csv')
       WHERE lat IS NOT NULL AND lat NOT BETWEEN 36 AND 39
UNION ALL
SELECT 'coords: lon fuori Sicilia 11-16 (atteso 0)',
       COUNT(*)::VARCHAR FROM read_csv('data/anagrafica_stazioni.csv')
       WHERE lon IS NOT NULL AND lon NOT BETWEEN 11 AND 16;

-- validazione empirica crosswalk: SPI-3 per stazione vs file aggregato
CREATE TABLE agg AS SELECT * FROM read_xlsx('data/raw/SPI_SICILIA_2026-05.xlsx', all_varchar=true);
CREATE TABLE agg2 AS
  SELECT (DATE '1899-12-30' + CAST("date" AS INTEGER) * INTERVAL 1 DAY) AS date, *
  EXCLUDE("date") FROM agg WHERE TRY_CAST("date" AS INTEGER) IS NOT NULL;
CREATE TABLE agg_long AS
  SELECT date, station, CASE WHEN val='-99' THEN NULL ELSE CAST(val AS DOUBLE) END AS spi
  FROM agg2 UNPIVOT (val FOR station IN (COLUMNS(* EXCLUDE(date, mese, "MEDIA REGIONALE"))));
CREATE TABLE mine AS
  SELECT station, date, spi FROM read_csv('data/spi_sias_long.csv') WHERE timescale_months=3;

SELECT 'coppie SPI-3 confrontate' AS check, COUNT(*)::VARCHAR AS val
FROM agg_long a JOIN mine m ON a.station=m.station AND a.date=m.date
UNION ALL
SELECT 'discordanze di valore (atteso 0)',
       COUNT(*)::VARCHAR
FROM agg_long a JOIN mine m ON a.station=m.station AND a.date=m.date
WHERE a.spi IS NOT NULL AND m.spi IS NOT NULL AND abs(a.spi-m.spi)>0.001
UNION ALL
SELECT 'discordanze NA (atteso 0)',
       COUNT(*)::VARCHAR
FROM agg_long a JOIN mine m ON a.station=m.station AND a.date=m.date
WHERE (a.spi IS NULL) != (m.spi IS NULL);
SQL
