# Nota tecnica — Verifica e correzione degli indici SPI nel report sulla siccità in Sicilia (1951–2024)

**Oggetto:** controllo di qualità dei dataset SPI utilizzati nel report *"Valutazione dei cambiamenti climatici e rilevamento delle anomalie nella regione siciliana (1951–2024)"* e ricalcolo degli indici secondo la definizione standard.

---

## Sintesi

I file SPI forniti (`Sicily_SPI_{1,2,3}_predicted`) **non sono indici standardizzati corretti**: conservano un marcato ciclo stagionale (che lo SPI, per definizione, deve rimuovere) e, per SPI1, presentano un bias negativo e valori non fisici. Ricalcolando lo SPI dalla precipitazione secondo McKee et al. (1993) e le linee guida WMO (2012) si ottengono indici corretti e verificati (media ≈ 0, deviazione standard ≈ 1 per ogni mese). Con gli indici corretti, **il periodo più secco risulta il 1969–1987 e il 2006–2024 il più umido** dei quattro analizzati: ciò contraddice la tesi del report secondo cui la siccità diventa dominante dopo il 2006. La conclusione vale per la sola precipitazione; non è stato possibile valutare la componente termica perché il dataset di temperatura non è stato fornito.

---

## 1. Dati e ambito

Dataset utilizzati (griglia ~1 km, mensile, gen 1951 – dic 2024):

- `Sicily_ISPRA_precip_a1951_2024.nc` — precipitazione mensile (integra, usata come riferimento);
- `Sicily_SPI_{1,2,3}_predicted_1951_2024.nc` — SPI a 1, 2, 3 mesi.

**Non** è stato fornito il dataset di temperatura, quindi le figure del report basate sulla temperatura (mappe e serie termiche) non sono verificabili né riproducibili.

## 2. Il problema: gli SPI forniti non sono standardizzati

Lo SPI è, per costruzione, una variabile normale standard **calcolata separatamente per ogni mese di calendario**: questo serve a rimuovere il ciclo stagionale, cosicché un valore di −1 a gennaio e uno ad agosto indichino la stessa severità relativa. Ne consegue che la media e la deviazione standard dello SPI devono valere **0 e 1 in ogni mese**.

I file forniti violano questa proprietà. La media dell'indice sull'isola, calcolata mese per mese, mostra un evidente ciclo stagionale residuo:

| Mese | SPI1 fornito | SPI2 fornito | SPI3 fornito |
|---|---|---|---|
| Gennaio | −0.0 | +0.87 | +0.97 |
| Aprile | −0.57 | +0.27 | +0.44 |
| Giugno | −1.19 | −0.64 | −0.43 |
| Agosto | −0.70 | −1.48 | −1.47 |
| Dicembre | +0.07 | +0.87 | +0.75 |

In un indice corretto questa colonna sarebbe piatta a 0. Inoltre:

- **SPI1** ha media globale **−0.44** e σ **0.82** (anziché 0 e 1): è sistematicamente spostato verso il "secco" e con varianza compressa;
- compaiono **valori non fisici** (fino a **+12** per SPI1, −7 per SPI2), mentre lo SPI reale resta quasi sempre entro ±3.

L'effetto pratico è che l'indice fornito **confonde la normale stagionalità con la siccità** (es.: 22 mm di pioggia a luglio a Enna, che per un luglio è un valore *umido*, vengono classificati come "secchi" perché in estate piove poco). Il report non documenta né il metodo di calcolo né questa anomalia.

## 3. Correzione: ricalcolo dello SPI standard e verifica

Lo SPI è stato **ricalcolato dalla precipitazione** secondo la procedura standard:

1. accumulo della precipitazione su finestra mobile di *k* mesi;
2. per ogni cella e ogni mese di calendario: fit di una distribuzione **Gamma** (stimatore di Thom, 1958) sui valori positivi, distribuzione mista per gli zeri `H(x) = q + (1−q)·Γ(x)`;
3. trasformazione alla normale standard `SPI = Φ⁻¹(H(x))`. Periodo di riferimento: 1951–2024.

**Verifiche superate:**

- media e deviazione standard **per ogni mese di calendario** pari a ≈ 0 e ≈ 1 (10–12 mesi su 12). L'unica deviazione è in piena estate per SPI1 (luglio: media 0.43, σ 0.62), dovuta all'eccesso di mesi con pioggia ≈ 0: è un **limite intrinseco e documentato** dello SPI a breve scala in clima arido, non un errore di metodo;
- frequenza delle classi di siccità in accordo con le probabilità teoriche della N(0,1) (siccità estrema 1.6–1.9 % osservato contro 2.3 % teorico);
- deviazione standard per cella compresa tra 0.94 (SPI1) e 1.00 (SPI3).

Output: `data/Sicily_SPI_{1,2,3}_recomputed_1951_2024.nc`.

## 4. Conseguenza sui risultati: il 2006–2024 non è il periodo più secco

Confrontando i quattro periodi del report con lo SPI ricalcolato (media spaziale sull'isola; % di territorio con SPI medio di periodo < 0):

| Indice | metrica | 1951–68 | 1969–87 | 1988–2005 | 2006–24 |
|---|---|---|---|---|---|
| SPI3 | media isola | +0.07 | **−0.12** | −0.06 | **+0.12** |
| SPI3 | % territorio in deficit | 25 % | **92 %** | 75 % | **9 %** |
| SPI2 | media isola | +0.07 | **−0.09** | −0.02 | **+0.10** |

Il periodo **più secco è il 1969–1987** (fino al 92 % del territorio in deficit), mentre il **2006–2024 è il più umido** dei quattro (circa 9 % in deficit). Questo **contraddice** l'affermazione del report ("dopo il 2006 la siccità diventa la condizione dominante, con SPI3 su oltre il 70 % del territorio"). Lo stesso segnale, in forma attenuata, è presente anche nei file forniti.

## 5. Avvertenza importante

Lo SPI quantifica **esclusivamente la precipitazione**. Il fatto che la pioggia non indichi il 2006–2024 come il periodo più secco **non esclude** una siccità agricola o idrologica nel periodo recente, che può essere guidata dall'aumento delle temperature e dell'evapotraspirazione. Questa componente **non è stata verificabile** in assenza del dataset di temperatura. Indici che includono la domanda evapotraspirativa (es. SPEI) sarebbero più adatti a cogliere questo aspetto.

## 6. Raccomandazioni

1. **Non utilizzare** i file `SPI_predicted` così come sono: sostituirli con gli SPI ricalcolati e verificati.
2. **Aggiornare** le Figure 8–10 e il testo correlato con gli indici corretti; rivedere la narrazione sull'intensificazione della siccità dopo il 2006, che i dati di precipitazione non supportano.
3. **Documentare** nel report il metodo di calcolo dello SPI e il periodo di riferimento.
4. **Reperire il dataset di temperatura** per (a) riprodurre le figure termiche e (b) valutare la siccità con un indice tipo SPEI, che combina pioggia e domanda evaporativa.

---

### Riferimenti

- McKee, T. B., Doesken, N. J., & Kleist, J. (1993). *The relationship of drought frequency and duration to time scales*. 8th Conf. on Applied Climatology.
- Thom, H. C. S. (1958). *A note on the gamma distribution*. Monthly Weather Review, 86(4).
- World Meteorological Organization (2012). *Standardized Precipitation Index User Guide* (WMO-No. 1090).
