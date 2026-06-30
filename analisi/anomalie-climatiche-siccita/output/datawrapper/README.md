# Grafici Datawrapper — siccità e piogge in Sicilia (1951–2024)

Dati **corretti** (SPI ricalcolato secondo WMO + precipitazione ISPRA BIGBANG).
Ogni CSV è pronto per l'import diretto in Datawrapper.

> **Nota onesta da mettere SEMPRE in calce ai grafici sulla siccità:** lo SPI misura
> *solo la pioggia*. Non tiene conto del caldo e dell'evaporazione: il periodo
> recente può soffrire comunque di stress idrico per le alte temperature, qui non
> valutabili (dataset di temperatura non disponibile).

---

## A — `A_cronologia_siccita_sicilia.csv`
**Tipo:** Grafico a linee (*Line chart*).
**Assi:** x = `data` (Datawrapper la riconosce come data mensile); linee = SPI1/SPI2/SPI3.
**Consiglio:** evidenzia **SPI3** (siccità di lungo periodo), metti le altre due tenui.
Aggiungi una **linea di riferimento a 0** e una banda grigia sotto lo 0.
**Titolo:** "In Sicilia la siccità non è una novità"
**Sottotitolo:** "Indice di precipitazione SPI mediato sull'isola (media mobile 12 mesi): i tratti sotto lo zero sono periodi più secchi della norma 1951–2024."
**Da far notare:** i tuffi più profondi e prolungati sono tra gli anni '70 e i primi 2000; dopo il 2003 risale.

## B — `B_territorio_siccita_per_periodo.csv`  ⭐ il grafico-chiave
**Tipo:** Grafico a barre (*Bar chart* o *Column chart*).
**Dati:** 4 periodi; usa come valore principale la colonna *"territorio in siccità di
lungo periodo (%)"*. (La seconda colonna serve se vuoi barre raggruppate.)
**Titolo:** "Il periodo più secco è stato il 1969–1987, non gli anni 2000"
**Sottotitolo:** "Quota del territorio siciliano con deficit di pioggia (SPI a 3 mesi sotto lo zero) in media su ciascun periodo."
**Da far notare:** 1969–1987 → 93 % del territorio in deficit; 2006–2024 → solo 9 %.
Colora di rosso il 1969–1987 e di blu il 2006–2024.

## C — `C_anomalia_provincia_periodo.csv`
**Tipo (consigliato):** *Table* con celle colorate (heatmap), oppure **4 mappe
coropletiche** (basemap Datawrapper "Italy » Provinces", abbina con la colonna
`provincia` o `sigla`).
**Dati:** valore SPI3 medio per provincia in ciascuno dei 4 periodi (blu = umido,
rosso = secco; scala divergente centrata su 0).
**Titolo:** "Dove e quando è mancata la pioggia, provincia per provincia"
**Da far notare:** nel 1969–1987 tutte le province sono negative; nel 2006–2024 tornano tutte positive.

## D — `D_regime_piogge_sicilia.csv`
**Tipo:** Grafico a colonne (*Column chart*).
**Titolo:** "Il clima mediterraneo della Sicilia: inverni piovosi, estati aride"
**Sottotitolo:** "Pioggia media mensile sull'isola, 1951–2024."
**Da far notare:** luglio ~7 mm contro dicembre ~93 mm. Utile come grafico di contesto.

## E — `E_pioggia_annuale_sicilia.csv`
**Tipo:** Grafico a linee o a colonne (*Line/Column chart*).
**Assi:** x = `anno`; linea principale = "pioggia annua media (mm)"; aggiungi la
colonna "media 1951-2024 (mm)" come **linea di riferimento** orizzontale.
**Titolo:** "Quanto piove in Sicilia, anno per anno"
**Sottotitolo:** "Pioggia annua media sull'isola (mm). Media di lungo periodo: 576 mm."
**Da far notare:** nessun crollo netto del totale annuo, ma forte variabilità da un anno all'altro (es. 1951 ~780 mm, 1952 ~386 mm).

---

### Sequenza narrativa suggerita per l'articolo
1. **D** (contesto: com'è il clima delle piogge) → 2. **E** (le piogge totali non sono
crollate) → 3. **A** (ma la siccità va e viene: cronologia) → 4. **B** (il colpo di
scena: i decenni peggiori sono '70–'80) → 5. **C** (mappa: dove). Chiudi sempre con il
caveat sul caldo/temperatura.
