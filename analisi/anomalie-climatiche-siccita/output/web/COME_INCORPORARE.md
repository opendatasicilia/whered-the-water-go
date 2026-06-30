# Come incorporare la mappa animata

Il file `sicilia_siccita.html` è **autosufficiente**: contiene dati, stile e codice in
un unico file (~1.35 MB, nessuna dipendenza esterna, nessuna chiamata di rete). Per
incorporarlo basta metterlo online e puntarci un `<iframe>`.

## 1. Mettilo online (hosting)

Carica `sicilia_siccita.html` su un qualsiasi hosting statico, ad esempio:
- **GitHub Pages**, **Netlify**, **Cloudflare Pages** (gratuiti)
- lo spazio media del tuo CMS / sito
- un bucket **S3 / Google Cloud Storage** pubblico

Ottieni un URL pubblico, es. `https://tuosito.it/widget/sicilia_siccita.html`.

> Suggerimento: servilo con compressione (gzip/brotli) e cache lunga
> (`Cache-Control: public, max-age=31536000, immutable`): il file non cambia.

## 2. Incorporamento base (altezza fissa)

```html
<iframe
  src="https://tuosito.it/widget/sicilia_siccita.html"
  title="Siccità in Sicilia 1951–2024"
  style="width:100%;max-width:680px;height:760px;border:0;display:block;margin:auto"
  loading="lazy"
  sandbox="allow-scripts allow-same-origin"
  referrerpolicy="no-referrer-when-downgrade">
</iframe>
```

- `width:100%` → si adatta alla colonna dell'articolo; `max-width:680px` evita che diventi enorme su desktop.
- `loading="lazy"` → l'iframe si carica solo quando entra nello schermo (meglio per le pagine lunghe).
- `sandbox="allow-scripts allow-same-origin"` → permessi minimi (gli serve solo eseguire JS).
- L'altezza fissa va bene, ma su mobile (colonna stretta) la mappa è più alta: vedi sotto.

## 3. Incorporamento responsive con altezza automatica (consigliato)

Il widget **comunica da solo la propria altezza** alla pagina ospite via `postMessage`
(come fanno Datawrapper/Flourish). Aggiungi questo piccolo script nella pagina che
contiene l'iframe e l'altezza si adatterà da sola (desktop, mobile, rotazione schermo):

```html
<iframe id="mappaSicilia"
  src="https://tuosito.it/widget/sicilia_siccita.html"
  title="Siccità in Sicilia 1951–2024"
  style="width:100%;max-width:680px;height:760px;border:0;display:block;margin:auto"
  loading="lazy" sandbox="allow-scripts allow-same-origin"></iframe>

<script>
  window.addEventListener('message', function(e){
    if(e.data && e.data.type === 'sicilia-embed-height'){
      var f = document.getElementById('mappaSicilia');
      if(f) f.style.height = e.data.height + 'px';
    }
  });
</script>
```

Il widget invia `{type:'sicilia-embed-height', height:<px>}` al caricamento e a ogni
ridimensionamento: la pagina ospite imposta l'altezza esatta → niente barra di scorrimento interna.

## 4. WordPress / CMS

- **WordPress**: usa il blocco *HTML personalizzato* e incolla il codice del punto 2 o 3.
  (Se il tema rimuove gli `<iframe>`, usa un plugin tipo "embed iframe" o carica il file
  nei media e linkalo.)
- **Editor che bloccano gli script** (es. alcuni CMS): usa la versione a **altezza fissa**
  (punto 2), che non richiede script nella pagina ospite.

## 5. Note tecniche

- **Performance**: tutto è disegnato su `<canvas>` con i dati compressi (gzip) e
  decompressi nel browser; gira a 60 fps anche su mobile. Richiede un browser moderno
  (Chrome/Edge ≥ 80, Safari ≥ 16.4, Firefox ≥ 113); su browser molto vecchi mostra un
  messaggio invece di rompersi.
- **Retina**: il canvas si adatta alla densità dello schermo (nitido su display HiDPI).
- **Accessibilità**: pulsanti con `aria-label`; i colori seguono una scala divergente
  rosso–blu con legenda testuale "secco / umido".

## 6. Da personalizzare facilmente

Nel sorgente (rigenerabile con `scripts/build_map_animation.py`) puoi cambiare:
- `SPEED` → velocità dell'animazione;
- `TARGET_W` / `STRIDE` → risoluzione e numero di fotogrammi (qualità vs peso);
- palette colori (`STOPS`), titoli e testi.
