"""Mappa animata della Sicilia (1951-2024): SOLO precipitazione annua (mm).

Un fotogramma per anno solare = pioggia totale caduta in quell'anno (somma dei
12 mesi, gennaio-dicembre), senza riferimenti ad anomalie o siccita'. Il browser
interpola tra un anno e il successivo per una transizione morbida; il contatore
mostra soltanto l'anno. Dati compressi gzip e decompressi via DecompressionStream.
Auto-altezza per iframe. Un solo file HTML autonomo.

Output: output/web/sicilia_precip_annua.html
"""
import sys, os, json, base64, gzip
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import pandas as pd
import common

OUTD = os.path.join(common.OUT, "web")
os.makedirs(OUTD, exist_ok=True)

TARGET_W = 140
CROP_LAT = (36.55, 38.95)
CROP_LON = (11.95, 15.72)

# Scala colore (mm di pioggia in un anno). Copre ~2°-98° percentile dei valori
# annuali per cella; sotto/sopra vengono tagliati agli estremi.
VMIN, VMAX = 300, 1300

pr = common.load_precip()
lat = pr.lat.values; lon = pr.lon.values
time = pd.DatetimeIndex(pr.time.values)
mask = common.build_province_mask(lat, lon) >= 0

# indici ritaglio
rows = np.where((lat >= CROP_LAT[0]) & (lat <= CROP_LAT[1]))[0]
cols = np.where((lon >= CROP_LON[0]) & (lon <= CROP_LON[1]))[0]
r0, r1, c0, c1 = rows.min(), rows.max()+1, cols.min(), cols.max()+1
land = mask[r0:r1, c0:c1]
H0, W0 = land.shape
f = max(1, int(np.ceil(W0 / TARGET_W)))
Hn, Wn = int(np.ceil(H0/f)), int(np.ceil(W0/f))

def crop(a):
    return a[..., r0:r1, c0:c1]

def block(a):                       # downsample (nanmean) su griglia ritagliata
    a = np.where(land[None] if a.ndim == 3 else land, a, np.nan)
    ph, pw = Hn*f - a.shape[-2], Wn*f - a.shape[-1]
    a = np.pad(a, [(0,0)]*(a.ndim-2)+[(0,ph),(0,pw)], constant_values=np.nan)
    a = a.reshape(*a.shape[:-2], Hn, f, Wn, f)
    with np.errstate(invalid="ignore"):
        return np.nanmean(a, axis=(-3, -1))

# maschera downsamplata (nord in alto)
landd = (~np.isnan(block(land.astype(float)))) & (block(land.astype(float)) > 0)
landd = landd[::-1, :]

# --- somma annuale per anno solare (gen-dic); tengo solo gli anni completi ---
annual = pr.groupby("time.year").sum("time", skipna=False)   # (year, lat, lon)
nmonths = pd.Series(1, index=time).groupby(time.year).sum()   # mesi disponibili per anno
full = [int(y) for y in annual.year.values if int(nmonths.get(int(y), 0)) == 12]
annual = annual.sel(year=full)
years = full
nF = len(years)

def to_frames_all(arr):             # (n, lat, lon) -> (n, Hn*Wn) downsamplato, nord in alto
    d = block(crop(arr.astype("float32")))            # (n, Hn, Wn)
    d = d[:, ::-1, :]
    return d.reshape(d.shape[0], -1)                  # (n, ncells)

def quantize(d, vmin, vmax):        # (nF,nLand) float -> uint8; NaN residui -> 127 (neutro)
    df = pd.DataFrame(d).ffill().bfill()
    q = np.clip((df.values - vmin)/(vmax - vmin), 0, 1)
    out = np.round(q*254).astype("uint8")
    out[~np.isfinite(df.values)] = 127
    return out

def delta_cellmajor(frames):        # (nF,nLand) uint8 -> delta per cella (gzip-friendly)
    # Prima colonna = valore assoluto (0..254); colonne successive = delta anno
    # su anno con codifica zigzag: gli scarti piccoli diventano numeri vicini a 0
    # e gzip li comprime molto meglio del complemento a 2.
    fm = frames.T.astype(np.int16)                       # (nLand, nF)
    out = np.empty_like(fm, dtype="uint8")
    out[:, 0] = fm[:, 0].astype("uint8")
    diff = np.clip(fm[:, 1:] - fm[:, :-1], -128, 127).astype(np.int16)
    out[:, 1:] = (((diff << 1) ^ (diff >> 15)) & 0xFF).astype("uint8")   # zigzag
    return out.reshape(-1)

# --- pioggia annua per cella (somma gen-dic di ogni anno, in mm) ---
cube = to_frames_all(annual.values)
pr.close()

# --- la TERRA = celle con dati finiti in almeno un frame ---
from scipy import ndimage
valid = landd.reshape(-1).copy()
valid &= np.isfinite(cube).any(axis=0)
valid2d = valid.reshape(Hn, Wn)

# dilato la terra di qualche cella fino a coprire la costa; le nuove celle prendono
# il valore della cella valida piu' vicina (il disegno verra' poi ritagliato sul contorno)
DIL = 4
dil2d = ndimage.binary_dilation(valid2d, structure=np.ones((3, 3), bool), iterations=DIL)
ind = ndimage.distance_transform_edt(~valid2d, return_distances=False, return_indices=True)
near_flat = (ind[0] * Wn + ind[1]).reshape(-1)      # per ogni cella: indice valida + vicina

idx_land = np.where(dil2d.reshape(-1))[0]
nLand = int(idx_land.size)
maskflat = dil2d.reshape(-1).astype("uint8")
near = near_flat[idx_land]                            # sorgente (valida) per ogni cella dipinta

VAR = {"id": "precip", "name": "Pioggia annua (mm)",
       "vmin": VMIN, "vmax": VMAX, "lo": f"{VMIN} mm", "hi": f"≥{VMAX} mm"}
frames = cube[:, near]                                # valore della valida piu' vicina
blocks = [maskflat, delta_cellmajor(quantize(frames, VMIN, VMAX))]

buf = np.concatenate(blocks).astype("uint8").tobytes()
gz = gzip.compress(buf, 9)
b64 = base64.b64encode(gz).decode()

# --- proiezione lon/lat -> pixel griglia (per disegnare i confini) ---
dlon = float(lon[1] - lon[0]); dlat = float(lat[1] - lat[0])
proj = {"lon0": float(lon[c0] + (f-1)/2*dlon), "lonpx": float(f*dlon),
        "lat0": float(lat[r0] + ((Hn-1)*f + (f-1)/2)*dlat), "latpx": float(-f*dlat)}

# --- contorno della Sicilia (unione province -> poligono principale, semplificato) ---
import geopandas as gpd
g = gpd.read_file(common.GEOJSON)
uni = g.geometry.union_all() if hasattr(g.geometry, "union_all") else g.unary_union
polys = list(uni.geoms) if uni.geom_type == "MultiPolygon" else [uni]
coast = []
for p in sorted(polys, key=lambda p: p.area, reverse=True):
    if p.area < 0.01:       # solo isole abbastanza grandi (Sicilia + Pantelleria)
        break
    ring = [[round(x, 4), round(y, 4)] for x, y in p.simplify(0.004).exterior.coords]
    coast.append(ring)

meta = {"w": Wn, "h": Hn, "nF": nF, "nLand": nLand,
        "years": years, "var": VAR,
        "proj": proj, "coast": coast}
print(f"griglia {Wn}x{Hn}, frame {nF} (uno per anno: {years[0]}-{years[-1]}), celle terra {nLand}")
print(f"raw {len(buf)/1024:.0f} KB -> gzip {len(gz)/1024:.0f} KB -> base64 {len(b64)/1024:.0f} KB")

HTML = r"""<!doctype html><html lang="it"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Quanta pioggia cade in Sicilia 1951–2024</title>
<style>
  :root{--bg:#fbfbf9;--ink:#1d2630;--muted:#6b7682;}
  *{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
  html,body{margin:0;background:var(--bg);color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
  .wrap{max-width:680px;margin:0 auto;padding:14px 16px 16px}
  .title{font-size:19px;font-weight:700;letter-spacing:-.01em;margin:0}
  .sub{font-size:12.5px;color:var(--muted);margin:4px 0 10px;line-height:1.35}
  .stage{position:relative;width:100%;border-radius:14px;overflow:hidden;background:#eef1f3;
    box-shadow:0 1px 0 rgba(0,0,0,.04),0 8px 24px -12px rgba(0,0,0,.18)}
  canvas{display:block;width:100%;height:auto}
  .year{position:absolute;left:14px;top:10px;font-weight:800;font-size:clamp(30px,9vw,52px);
    line-height:1;color:#0d1620;letter-spacing:-.02em;text-shadow:0 1px 0 rgba(255,255,255,.55)}
  .mon{position:absolute;left:16px;top:calc(12px + clamp(30px,9vw,52px));font-size:12.5px;
    font-weight:600;color:var(--muted)}
  .controls{display:flex;align-items:center;gap:12px;margin-top:12px}
  .play{flex:0 0 auto;width:42px;height:42px;border-radius:50%;border:0;cursor:pointer;
    background:var(--ink);color:#fff;font-size:15px;display:grid;place-items:center}
  .play:active{transform:scale(.92)}
  input[type=range]{flex:1;width:100%;accent-color:#1d91c0;height:24px}
  .legend{display:flex;align-items:center;gap:8px;margin-top:12px;font-size:11.5px;color:var(--muted)}
  .bar{flex:1;height:10px;border-radius:6px;
    background:linear-gradient(90deg,#ffffd9,#edf8b1,#c7e9b4,#7fcdbb,#41b6c4,#1d91c0,#225ea8,#253494,#081d58)}
  .foot{font-size:11px;color:var(--muted);margin-top:10px;line-height:1.4}
  .err{font-size:13px;color:#b03a2e;padding:30px 10px;text-align:center}
</style></head><body>
<div class="wrap">
  <h1 class="title">Quanta pioggia cade in Sicilia</h1>
  <p class="sub">Pioggia totale caduta in ogni anno, per ogni punto dell'isola,
     dal 1951 al 2024. Più il colore è <b style="color:#1d5ea8">blu</b>, più piove;
     più è <b style="color:#b59a2e">giallo</b>, meno.</p>
  <div class="stage">
    <canvas id="cv"></canvas>
    <div class="year" id="yr"></div>
    <div class="mon" id="mo"></div>
  </div>
  <div class="controls">
    <button class="play" id="play" aria-label="play/pausa">❚❚</button>
    <input id="sl" type="range" min="0" max="0" step="0.001" value="0">
  </div>
  <div class="legend"><span id="lo">300 mm</span><div class="bar"></div><span id="hi">≥1300 mm</span></div>
  <p class="foot" id="foot"></p>
</div>
<script>
const META=__META__, DATA="__DATA__";
const W=META.w,H=META.h,NF=META.nF,NL=META.nLand,VAR=META.var;
// Scala sequenziale YlGnBu (ColorBrewer): giallo chiaro (poca pioggia) -> blu scuro (molta)
const STOPS=[[255,255,217],[237,248,177],[199,233,180],[127,205,187],[65,182,196],
             [29,145,192],[34,94,168],[37,52,148],[8,29,88]];
function lut(t){const x=Math.max(0,Math.min(1,t))*(STOPS.length-1);
  const i=Math.floor(x),f=x-i,a=STOPS[i],b=STOPS[Math.min(i+1,STOPS.length-1)];
  return [a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f,a[2]+(b[2]-a[2])*f];}
let bin=null,landIdx=[],FM=null;   // FM = fotogrammi ricostruiti (frame-major)
function unzig(z){return (z>>>1)^(-(z&1));}   // zigzag -> delta con segno
const off=document.createElement('canvas');off.width=W;off.height=H;
const octx=off.getContext('2d');const img=octx.createImageData(W,H);
const cv=document.getElementById('cv'),ctx=cv.getContext('2d');
let pos=0,playing=true,last=0;const SPEED=0.8; // anni/sec (un fotogramma = un anno)
async function gunzip(b64){
  const raw=Uint8Array.from(atob(b64),c=>c.charCodeAt(0));
  const ds=new DecompressionStream('gzip');
  const ab=await new Response(new Blob([raw]).stream().pipeThrough(ds)).arrayBuffer();
  return new Uint8Array(ab);}
function frame(fr){const base=fr*NL;return FM.subarray(base,base+NL);}
const BG=[238,241,243];   // colore mare = sfondo (evita aloni ai bordi)
function render(fa,fb,t){const d=img.data;
  for(let i=0;i<W*H;i++){const p=i*4;d[p]=BG[0];d[p+1]=BG[1];d[p+2]=BG[2];d[p+3]=255;}
  for(let k=0;k<NL;k++){const v=fa[k]+(fb[k]-fa[k])*t;const c=lut(v/254);
    const p=landIdx[k]*4;d[p]=c[0];d[p+1]=c[1];d[p+2]=c[2];d[p+3]=255;}
  octx.putImageData(img,0,0);const cw=cv.width,ch=cv.height;ctx.clearRect(0,0,cw,ch);
  const path=coastPath(cw,ch);
  if(path){ctx.save();ctx.clip(path);ctx.drawImage(off,0,0,cw,ch);ctx.restore();}
  else ctx.drawImage(off,0,0,cw,ch);
  drawCoast(path);}
const PROJ=META.proj,COAST=META.coast||[];
function coastPath(cw,ch){if(!COAST.length)return null;const p=new Path2D();
  for(const ring of COAST){for(let i=0;i<ring.length;i++){
    const gx=(ring[i][0]-PROJ.lon0)/PROJ.lonpx,gy=(ring[i][1]-PROJ.lat0)/PROJ.latpx;
    const x=(gx+0.5)/W*cw,y=(gy+0.5)/H*ch;
    if(i===0)p.moveTo(x,y);else p.lineTo(x,y);}p.closePath();}return p;}
function drawCoast(path){if(!path)return;const cw=cv.width;
  ctx.lineJoin='round';ctx.lineCap='round';
  ctx.lineWidth=Math.max(1,cw/W*0.45);ctx.strokeStyle='rgba(38,52,62,.6)';ctx.stroke(path);}
function draw(p){const i=Math.min(NF-1,Math.floor(p)),j=Math.min(NF-1,i+1),t=p-i;
  render(frame(i),frame(j),t);   // morphing morbido tra un anno e il successivo
  document.getElementById('yr').textContent=META.years[Math.min(NF-1,Math.round(p))];}
function resize(){const r=cv.parentElement.getBoundingClientRect();
  const dpr=Math.min(window.devicePixelRatio||1,2);
  cv.width=Math.round(r.width*dpr);cv.height=Math.round(r.width*dpr*H/W);
  cv.style.height=(r.width*H/W)+'px';ctx.imageSmoothingEnabled=true;
  ctx.imageSmoothingQuality='high';if(bin)draw(pos);postH();}
function tick(ts){if(!last)last=ts;const dt=(ts-last)/1000;last=ts;
  if(playing&&bin){pos+=dt*SPEED;if(pos>=NF-1)pos=0;
    document.getElementById('sl').value=pos;draw(pos);}
  requestAnimationFrame(tick);}
function postH(){try{if(window.parent!==window)
  parent.postMessage({type:'sicilia-embed-height',height:document.body.scrollHeight},'*');}catch(e){}}
(async function(){
  document.getElementById('lo').textContent=VAR.lo;
  document.getElementById('hi').textContent=VAR.hi;
  document.getElementById('mo').textContent="pioggia caduta nell'anno";
  document.getElementById('foot').textContent=
    "Fonte: dati ISPRA di precipitazione (griglia, 1951–2024). Ogni fotogramma è un "+
    "anno solare: mostra la pioggia totale caduta in quell'anno, punto per punto. Un "+
    "valore alto significa un anno piovoso, uno basso un anno asciutto. I confini "+
    "seguono la costa della Sicilia.";
  const sl=document.getElementById('sl');sl.max=NF-1;
  const btn=document.getElementById('play');
  btn.onclick=()=>{playing=!playing;btn.textContent=playing?'❚❚':'►';last=0;};
  sl.oninput=()=>{playing=false;btn.textContent='►';pos=parseFloat(sl.value);draw(pos);};
  window.addEventListener('resize',resize);
  if(!('DecompressionStream'in window)){
    document.querySelector('.stage').innerHTML=
      '<div class="err">Il tuo browser è troppo vecchio per questa animazione.</div>';return;}
  try{bin=await gunzip(DATA);}catch(e){
    document.querySelector('.stage').innerHTML='<div class="err">Errore nel caricamento dei dati.</div>';return;}
  for(let i=0;i<W*H;i++) if(bin[i]) landIdx.push(i);
  // ricostruzione delta cell-major -> frame-major
  let b=W*H;
  FM=new Uint8Array(NF*NL);
  for(let k=0;k<NL;k++){let acc=bin[b+k*NF];FM[k]=acc;
    for(let fr=1;fr<NF;fr++){acc=(acc+unzig(bin[b+k*NF+fr]))&255;FM[fr*NL+k]=acc;}}
  resize();requestAnimationFrame(tick);
})();
</script></body></html>"""

html = HTML.replace("__META__", json.dumps(meta)).replace("__DATA__", b64)
out = os.path.join(OUTD, "sicilia_precip_annua.html")
with open(out, "w") as fh:
    fh.write(html)
print("scritto", out, f"({os.path.getsize(out)/1024:.0f} KB)")
