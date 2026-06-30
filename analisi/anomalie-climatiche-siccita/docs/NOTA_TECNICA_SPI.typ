#set page(paper: "a4", margin: (x: 2.2cm, y: 2.2cm), numbering: "1")
#set text(font: ("Liberation Sans", "DejaVu Sans"), size: 10pt, lang: "it")
#set par(justify: true, leading: 0.62em)
#show heading: set block(above: 1.1em, below: 0.6em)
#set heading(numbering: none)
#show heading.where(level: 1): set text(size: 14pt)
#show heading.where(level: 2): set text(size: 11.5pt, fill: rgb("#1f3b66"))

#align(center)[
  #text(size: 16pt, weight: "bold")[Nota tecnica — Verifica e correzione degli indici SPI]
  #linebreak()
  #text(size: 12pt)[Report sulla siccità in Sicilia (1951–2024)]
  #linebreak()
  #v(2pt)
  #text(size: 9pt, fill: luma(90))[Controllo di qualità dei dataset SPI e ricalcolo secondo la definizione standard]
]

#v(4pt)
#line(length: 100%, stroke: 0.5pt + luma(160))

#block(fill: luma(244), inset: 10pt, radius: 4pt, width: 100%)[
  *Sintesi.* I file SPI forniti (`Sicily_SPI_{1,2,3}_predicted`) *non sono indici
  standardizzati corretti*: conservano un marcato ciclo stagionale (che lo SPI, per
  definizione, deve rimuovere) e, per SPI1, presentano un bias negativo e valori non
  fisici. Ricalcolando lo SPI dalla precipitazione secondo McKee et al. (1993) e le
  linee guida WMO (2012) si ottengono indici corretti e verificati (media $approx 0$,
  deviazione standard $approx 1$ per ogni mese). Con gli indici corretti, *il periodo
  più secco risulta il 1969–1987 e il 2006–2024 il più umido* dei quattro analizzati,
  in contrasto con la tesi del report secondo cui la siccità diventa dominante dopo il
  2006. La conclusione vale per la sola precipitazione: la componente termica non è
  valutabile perché il dataset di temperatura non è stato fornito.
]

== 1. Dati e ambito

Dataset (griglia ~1 km, mensile, gen 1951 – dic 2024): precipitazione mensile
(`Sicily_ISPRA_precip`, integra, usata come riferimento) e SPI a 1/2/3 mesi.
*Non* è stato fornito il dataset di temperatura: le figure termiche del report non
sono verificabili né riproducibili.

== 2. Il problema: gli SPI forniti non sono standardizzati

Lo SPI è, per costruzione, una variabile normale standard calcolata *separatamente
per ogni mese di calendario*: ciò rimuove il ciclo stagionale, così che un valore di
$-1$ a gennaio e uno ad agosto indichino la stessa severità relativa. Media e
deviazione standard devono quindi valere $0$ e $1$ in ogni mese. I file forniti
violano questa proprietà: la media dell'indice sull'isola, per mese, mostra un
evidente ciclo stagionale residuo.

#figure(
  image("../output/verify_ciclo_stagionale_confronto.png", width: 100%),
  caption: [Media dello SPI per mese di calendario. A sinistra i file forniti
  (ciclo stagionale residuo da $+1$ a $-1.5$); a destra lo SPI ricalcolato,
  correttamente piatto a 0. In un indice corretto entrambi i pannelli dovrebbero
  essere piatti.],
)

Inoltre: *SPI1* ha media globale $-0.44$ e $sigma = 0.82$ (anziché 0 e 1), spostato
verso il secco e con varianza compressa; compaiono *valori non fisici* (fino a $+12$
per SPI1), mentre lo SPI reale resta quasi sempre entro $plus.minus 3$. L'effetto è
che l'indice fornito *confonde la normale stagionalità con la siccità*. Il report non
documenta né il metodo di calcolo né questa anomalia.

== 3. Correzione e verifica

Lo SPI è stato ricalcolato dalla precipitazione: (1) accumulo su finestra di $k$ mesi;
(2) per ogni cella e ogni mese, fit di una distribuzione *Gamma* (stimatore di Thom,
1958) sui valori positivi, distribuzione mista per gli zeri
$H(x) = q + (1-q) dot Gamma(x)$; (3) trasformazione $"SPI" = Phi^(-1)(H(x))$.
Periodo di riferimento: 1951–2024. Verifiche superate:

- media e deviazione standard *per ogni mese* pari a $approx 0$ e $approx 1$ (10–12
  mesi su 12). L'unica deviazione è in piena estate per SPI1 (luglio: media 0.43,
  $sigma$ 0.62), per l'eccesso di mesi a pioggia $approx 0$: limite *intrinseco e
  documentato* dello SPI a breve scala, non un errore;
- frequenza delle classi di siccità in accordo con la $N(0,1)$ teorica (siccità
  estrema 1.6–1.9 % osservato vs 2.3 % teorico);
- deviazione standard per cella tra 0.94 (SPI1) e 1.00 (SPI3).

== 4. Conseguenza: il 2006–2024 non è il periodo più secco

#figure(
  table(
    columns: (auto, auto, auto, auto, auto, auto),
    align: (left, left, center, center, center, center),
    stroke: 0.4pt + luma(180),
    inset: 6pt,
    table.header([*Indice*], [*Metrica*], [*1951–68*], [*1969–87*], [*1988–2005*], [*2006–24*]),
    [SPI3], [media isola], [+0.07], [*−0.12*], [−0.06], [*+0.12*],
    [SPI3], [% terr. in deficit], [25 %], [*92 %*], [75 %], [*9 %*],
    [SPI2], [media isola], [+0.07], [*−0.09*], [−0.02], [*+0.10*],
  ),
  caption: [Siccità per periodo con lo SPI ricalcolato (media spaziale sull'isola e
  quota di territorio con SPI medio di periodo $< 0$).],
)

Il periodo *più secco è il 1969–1987* (fino al 92 % del territorio in deficit),
mentre il *2006–2024 è il più umido* dei quattro (~9 % in deficit). Ciò *contraddice*
l'affermazione del report ("dopo il 2006 la siccità diventa dominante, con SPI3 su
oltre il 70 % del territorio"). Lo stesso segnale, attenuato, è presente anche nei
file forniti.

#figure(
  image("../output/fig08_spi_maps_CORRETTO.png", width: 92%),
  caption: [Mappe SPI 1/2/3 (righe) per i quattro periodi (colonne) con lo SPI
  ricalcolato. Blu = umido, rosso = secco rispetto alla media 1951–2024. Il periodo
  recente (ultima colonna) è prevalentemente umido.],
)

== 5. Avvertenza

Lo SPI quantifica *solo la precipitazione*. Il fatto che la pioggia non indichi il
2006–2024 come il più secco *non esclude* una siccità agricola o idrologica recente
guidata dall'aumento delle temperature e dell'evapotraspirazione, componente *non
verificabile* senza il dataset di temperatura. Un indice come lo SPEI, che include la
domanda evaporativa, sarebbe più adatto.

== 6. Raccomandazioni

+ *Non utilizzare* i file `SPI_predicted`: sostituirli con gli SPI ricalcolati e
  verificati.
+ *Aggiornare* le Figure 8–10 e il testo; rivedere la narrazione sull'intensificazione
  della siccità dopo il 2006, che la precipitazione non supporta.
+ *Documentare* nel report il metodo di calcolo dello SPI e il periodo di riferimento.
+ *Reperire la temperatura* per riprodurre le figure termiche e valutare la siccità con
  un indice tipo SPEI.

#v(6pt)
#line(length: 100%, stroke: 0.5pt + luma(160))
#text(size: 8.5pt, fill: luma(90))[
  *Riferimenti.* McKee, Doesken & Kleist (1993), _The relationship of drought
  frequency and duration to time scales_, 8th Conf. Applied Climatology. ·
  Thom (1958), _A note on the gamma distribution_, Monthly Weather Review 86(4). ·
  WMO (2012), _Standardized Precipitation Index User Guide_ (WMO-No. 1090).
]
