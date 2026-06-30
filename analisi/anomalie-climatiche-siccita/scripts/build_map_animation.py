"""Mappa animata della Sicilia (1951-2024) come singolo file HTML autonomo.
Variabili selezionabili: Pioggia (anomalia %), SPI-1, SPI-3 (tutte a media mobile
12 mesi). Fotogrammi trimestrali + interpolazione nel browser = animazione fluida.
Dati compressi gzip e decompressi via DecompressionStream. Auto-altezza per iframe.
Output: output/web/sicilia_siccita.html
"""
import sys, os, json, base64, gzip
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import pandas as pd
import xarray as xr
import common

OUTD = os.path.join(common.OUT, "web")
os.makedirs(OUTD, exist_ok=True)

TARGET_W = 140
CROP_LAT = (36.55, 38.95)
CROP_LON = (11.95, 15.72)
STRIDE = 6          # un fotogramma ogni 6 mesi; l'interpolazione lo rende fluido
ROLL = 12          # media mobile 12 mesi

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
maskflat = landd.reshape(-1).astype("uint8")
# fotogrammi temporali (semestrali, scartando i bordi senza media mobile completa)
fr_idx = np.arange(ROLL-1, len(time), STRIDE)
years = [int(time[i].year) for i in fr_idx]
months = [int(time[i].month) for i in fr_idx]
nF = len(fr_idx)

def to_frames_all(cube):            # (time,lat,lon) -> (nF, Hn*Wn) downsamplato, nord in alto
    d = block(crop(cube.values.astype("float32")))    # (time,Hn,Wn)
    d = d[:, ::-1, :]
    return d.reshape(d.shape[0], -1)[fr_idx]           # (nF, ncells)

def quantize(d, vmin, vmax):        # (nF,nLand) float -> uint8; NaN residui -> 127 (neutro)
    df = pd.DataFrame(d).ffill().bfill()
    q = np.clip((df.values - vmin)/(vmax - vmin), 0, 1)
    out = np.round(q*254).astype("uint8")
    out[~np.isfinite(df.values)] = 127
    return out

def delta_cellmajor(frames):        # (nF,nLand) uint8 -> delta per cella (gzip-friendly)
    fm = frames.T.astype(np.int16)
    d = np.empty_like(fm)
    d[:, 0] = fm[:, 0]
    d[:, 1:] = fm[:, 1:] - fm[:, :-1]
    d = np.clip(d, -128, 127)
    return (d & 0xFF).astype("uint8").reshape(-1)

# --- calcolo i cubi grezzi (tutte le celle) per le 3 variabili ---
roll12 = pr.rolling(time=ROLL, min_periods=ROLL).sum()
clim = roll12.mean("time")
panom = (roll12 - clim) / clim * 100.0
cubes = {"precip": to_frames_all(panom)}
pr.close()
for k in (1, 2, 3):
    da = common.load_spi_recomputed(k).load()
    cubes[f"spi{k}"] = to_frames_all(da.rolling(time=ROLL, center=True, min_periods=6).mean())
    da.close()

# --- la TERRA = celle valide (dati finiti in almeno un frame) in TUTTE le variabili ---
from scipy import ndimage
valid = landd.reshape(-1).copy()
for c in cubes.values():
    valid &= np.isfinite(c).any(axis=0)
valid2d = valid.reshape(Hn, Wn)

# dilato la terra di qualche cella fino a coprire la costa; le nuove celle prendono
# il valore della cella valida più vicina (il disegno verrà poi ritagliato sul contorno)
DIL = 4
dil2d = ndimage.binary_dilation(valid2d, structure=np.ones((3, 3), bool), iterations=DIL)
ind = ndimage.distance_transform_edt(~valid2d, return_distances=False, return_indices=True)
near_flat = (ind[0] * Wn + ind[1]).reshape(-1)      # per ogni cella: indice valida + vicina

idx_land = np.where(dil2d.reshape(-1))[0]
nLand = int(idx_land.size)
maskflat = dil2d.reshape(-1).astype("uint8")
near = near_flat[idx_land]                            # sorgente (valida) per ogni cella dipinta

SPEC = [("spi1", "Siccità SPI-1", -1.5, 1.5, "−1.5", "+1.5"),
        ("spi2", "Siccità SPI-2", -1.5, 1.5, "−1.5", "+1.5"),
        ("spi3", "Siccità SPI-3", -1.5, 1.5, "−1.5", "+1.5"),
        ("precip", "Pioggia (anomalia)", -50, 50, "−50%", "+50%")]
VARS = []
blocks = [maskflat]
for vid, name, vmin, vmax, lo, hi in SPEC:
    frames = cubes[vid][:, near]                      # valore della valida più vicina
    blocks.append(delta_cellmajor(quantize(frames, vmin, vmax)))
    VARS.append({"id": vid, "name": name, "vmin": vmin, "vmax": vmax, "lo": lo, "hi": hi})

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
        "years": years, "months": months, "vars": VARS,
        "proj": proj, "coast": coast}
print(f"griglia {Wn}x{Hn}, frame {nF} (trimestrali), celle terra {nLand}, "
      f"variabili {len(VARS)}")
print(f"raw {len(buf)/1024:.0f} KB -> gzip {len(gz)/1024:.0f} KB -> base64 {len(b64)/1024:.0f} KB")

HTML = r"""<!doctype html><html lang="it"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Siccità in Sicilia 1951–2024</title>
<style>
  :root{--bg:#fbfbf9;--ink:#1d2630;--muted:#6b7682;}
  *{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
  html,body{margin:0;background:var(--bg);color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
  .wrap{max-width:680px;margin:0 auto;padding:14px 16px 16px}
  .title{font-size:19px;font-weight:700;letter-spacing:-.01em;margin:0}
  .sub{font-size:12.5px;color:var(--muted);margin:4px 0 10px;line-height:1.35}
  .tabs{display:flex;gap:6px;margin-bottom:10px;flex-wrap:wrap}
  .tab{font-size:12.5px;font-weight:600;padding:7px 12px;border-radius:999px;border:1px solid #e1e5e9;
    background:#fff;color:var(--ink);cursor:pointer;transition:.12s}
  .tab[aria-selected=true]{background:var(--ink);color:#fff;border-color:var(--ink)}
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
  input[type=range]{flex:1;width:100%;accent-color:#c0392b;height:24px}
  .legend{display:flex;align-items:center;gap:8px;margin-top:12px;font-size:11.5px;color:var(--muted)}
  .bar{flex:1;height:10px;border-radius:6px;
    background:linear-gradient(90deg,#67001f,#d6604d,#f7efe8,#4393c3,#053061)}
  .foot{font-size:11px;color:var(--muted);margin-top:10px;line-height:1.4}
  .err{font-size:13px;color:#b03a2e;padding:30px 10px;text-align:center}
</style></head><body>
<div class="wrap">
  <h1 class="title">In Sicilia la siccità va e viene</h1>
  <p class="sub">Media mobile a 12 mesi, dal 1951 al 2024.
     <b style="color:#b03a2e">Rosso</b> = più secco del normale,
     <b style="color:#1f6aa5">blu</b> = più umido.</p>
  <div class="tabs" id="tabs"></div>
  <div class="stage">
    <canvas id="cv"></canvas>
    <div class="year" id="yr"></div>
    <div class="mon" id="mo"></div>
  </div>
  <div class="controls">
    <button class="play" id="play" aria-label="play/pausa">❚❚</button>
    <input id="sl" type="range" min="0" max="0" step="0.001" value="0">
  </div>
  <div class="legend"><span id="lo">secco</span><div class="bar"></div><span id="hi">umido</span></div>
  <p class="foot" id="foot"></p>
</div>
<script>
const META=__META__, DATA="__DATA__";
const MONNAMES=["","gen","feb","mar","apr","mag","giu","lug","ago","set","ott","nov","dic"];
const W=META.w,H=META.h,NF=META.nF,NL=META.nLand,VARS=META.vars;
const STOPS=[[103,0,31],[178,24,43],[214,96,77],[244,165,130],[247,239,232],
             [146,197,222],[67,147,195],[33,102,172],[5,48,97]];
function lut(t){const x=Math.max(0,Math.min(1,t))*(STOPS.length-1);
  const i=Math.floor(x),f=x-i,a=STOPS[i],b=STOPS[Math.min(i+1,STOPS.length-1)];
  return [a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f,a[2]+(b[2]-a[2])*f];}
let bin=null,landIdx=[],FM=[];   // FM[v] = fotogrammi ricostruiti (frame-major)
function s8(b){return b<128?b:b-256;}
const off=document.createElement('canvas');off.width=W;off.height=H;
const octx=off.getContext('2d');const img=octx.createImageData(W,H);
const cv=document.getElementById('cv'),ctx=cv.getContext('2d');
let pos=0,playing=true,last=0,curVar=0;const SPEED=1.0; // frame/sec (semestri) ~0.5 anni/s
async function gunzip(b64){
  const raw=Uint8Array.from(atob(b64),c=>c.charCodeAt(0));
  const ds=new DecompressionStream('gzip');
  const ab=await new Response(new Blob([raw]).stream().pipeThrough(ds)).arrayBuffer();
  return new Uint8Array(ab);}
function frame(v,fr){const base=fr*NL;return FM[v].subarray(base,base+NL);}
const BG=[238,241,243];   // colore mare = sfondo (evita aloni neri ai bordi)
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
  render(frame(curVar,i),frame(curVar,j),t);
  const r=Math.round(p);
  document.getElementById('yr').textContent=META.years[r];
  document.getElementById('mo').textContent=MONNAMES[META.months[r]]+" (media 12 mesi)";}
function resize(){const r=cv.parentElement.getBoundingClientRect();
  const dpr=Math.min(window.devicePixelRatio||1,2);
  cv.width=Math.round(r.width*dpr);cv.height=Math.round(r.width*dpr*H/W);
  cv.style.height=(r.width*H/W)+'px';ctx.imageSmoothingEnabled=true;
  ctx.imageSmoothingQuality='high';if(bin)draw(pos);postH();}
function setVar(v){curVar=v;const o=VARS[v];
  document.getElementById('lo').textContent=o.lo;
  document.getElementById('hi').textContent=o.hi;
  [...document.querySelectorAll('.tab')].forEach((t,i)=>t.setAttribute('aria-selected',i==v));
  if(bin)draw(pos);}
function tick(ts){if(!last)last=ts;const dt=(ts-last)/1000;last=ts;
  if(playing&&bin){pos+=dt*SPEED;if(pos>=NF-1)pos=0;
    document.getElementById('sl').value=pos;draw(pos);}
  requestAnimationFrame(tick);}
function postH(){try{if(window.parent!==window)
  parent.postMessage({type:'sicilia-embed-height',height:document.body.scrollHeight},'*');}catch(e){}}
(async function(){
  // tabs
  const tabsEl=document.getElementById('tabs');
  VARS.forEach((o,i)=>{const b=document.createElement('button');b.className='tab';
    b.textContent=o.name;b.setAttribute('aria-selected',i===0);b.onclick=()=>setVar(i);
    tabsEl.appendChild(b);});
  document.getElementById('foot').textContent=
    "Nota: tutte le misure mostrate (anomalia di pioggia e indici SPI 1, 2 e 3) si basano "+
    "solo sulla pioggia; la temperatura, qui non disponibile, può aggravare la siccità anche "+
    "con piogge normali. Per leggibilità i valori sono mostrati come media mobile a 12 mesi, "+
    "rispetto al periodo 1951–2024.";
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
  // ricostruzione delta cell-major -> frame-major per ogni variabile
  let b=W*H;
  for(let v=0;v<VARS.length;v++){
    const fm=new Uint8Array(NF*NL);
    for(let k=0;k<NL;k++){let acc=bin[b+k*NF];fm[k]=acc;
      for(let fr=1;fr<NF;fr++){acc=(acc+s8(bin[b+k*NF+fr]))&255;fm[fr*NL+k]=acc;}}
    FM.push(fm);b+=NL*NF;}
  setVar(0);resize();requestAnimationFrame(tick);
})();
</script></body></html>"""

html = HTML.replace("__META__", json.dumps(meta)).replace("__DATA__", b64)
out = os.path.join(OUTD, "sicilia_siccita.html")
with open(out, "w") as fh:
    fh.write(html)
print("scritto", out, f"({os.path.getsize(out)/1024:.0f} KB)")
