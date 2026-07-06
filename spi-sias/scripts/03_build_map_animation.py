#!/usr/bin/env python3
"""03 - Mappa animata SPI spazializzato (serie SIAS 1991-2026), HTML autonomo.

Approccio "leggero e liscio": NON spedisce una griglia di pixel, ma solo i valori
mensili delle ~95 stazioni SIAS (~150 KB). Il browser ricostruisce la superficie
con spline a base radiale (kernel lineare, stessa matematica di scipy, verificata)
e la disegna classificando PER PIXEL -> bande continue, non pixelate, come l'ufficiale.

Colori/legenda a 13 classi presi dalla mappa ufficiale SIAS (SPI3).
Il core numerico e' scripts/tps_core.js (testato con node in scripts/test_tps.js).

Dipendenze (via uv): numpy scipy shapely pillow
  uv run --with numpy --with scipy --with shapely --with pillow \
      python scripts/04_build_map_animation.py
Output: output/web/spi_sias_animata.html  (+ scripts/_ref_tps.json, fixture per test_tps.js)
"""
import os, json, gzip, base64, csv, math
import numpy as np
from scipy.spatial.distance import cdist
from shapely.geometry import shape, box
from shapely.ops import unary_union
import shapely

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LONG = os.path.join(ROOT, "data", "spi_sias_long.csv")
ANAG = os.path.join(ROOT, "data", "anagrafica_stazioni.csv")
GEOJSON = os.path.join(ROOT, "data", "sicilia_prov.geojson")
OUTD = os.path.join(ROOT, "output", "web")
SCRATCH = os.path.dirname(HERE)  # ref json accanto agli script? no: in output
os.makedirs(OUTD, exist_ok=True)

CROP_LON = (12.35, 15.72)
CROP_LAT = (36.55, 38.35)
TIMESCALES = [3, 6, 12, 24, 48]
VMIN, VMAX = -3.5, 3.5
MIN_STA = 6
WG = 100                       # griglia di valutazione (il liscio viene dal per-pixel)
CLASS_COLORS = ["#d7181b","#e44933","#f17b47","#fdae61","#fdc981","#fff0b2",
                "#eff9b2","#c3e588","#a6d968","#77c45c","#47ae50","#1a9640","#1a8041"]
CLASS_LABELS = [">-2,5","-2,5–-2","-2–-1,5","-1,5–-1","-1–-0,5","-0,5–0",
                "0–0,5","0,5–1","1–1,5","1,5–2","2–2,5","2,5–3",">3"]
THRESH = [-2.5,-2,-1.5,-1,-0.5,0,0.5,1,1.5,2,2.5,3]

lat0 = (CROP_LAT[0]+CROP_LAT[1])/2
kx = math.cos(math.radians(lat0))

# --- anagrafica: solo stazioni con coordinate ---
anag = {}
for r in csv.DictReader(open(ANAG, newline="")):
    if r["lat"] and r["lon"]:
        anag[r["station"]] = {"prov": r["provincia"], "lon": float(r["lon"]), "lat": float(r["lat"])}
STA = sorted(anag)                              # ordine fisso stazioni
nSta = len(STA)
sidx = {s: i for i, s in enumerate(STA)}

# --- valori SPI: cube[var, month, station] ---
dates_set = set(); raw = {k: {} for k in TIMESCALES}
for r in csv.DictReader(open(LONG, newline="")):
    k = int(r["timescale_months"])
    if k not in raw or r["station"] not in anag or r["spi"] == "":
        continue
    dates_set.add(r["date"])
    raw[k].setdefault(r["date"], {})[r["station"]] = float(r["spi"])
DATES = sorted(dates_set)
NF = len(DATES); years = [int(d[:4]) for d in DATES]; months = [int(d[5:7]) for d in DATES]
print(f"stazioni: {nSta} | mesi: {NF} ({DATES[0]}..{DATES[-1]})")

cube = np.full((len(TIMESCALES), NF, nSta), -32768, dtype=np.int16)
for vi, k in enumerate(TIMESCALES):
    for mi, d in enumerate(DATES):
        for s, v in raw[k].get(d, {}).items():
            cube[vi, mi, sidx[s]] = int(round(v*100))
present = (cube != -32768).sum(2)
for vi, k in enumerate(TIMESCALES):
    print(f"  SPI{k}: mesi con >= {MIN_STA} stazioni: {(present[vi]>=MIN_STA).sum()}/{NF}")

# --- geometria: costa (isola maggiore) + confini provinciali ---
gj = json.load(open(GEOJSON))
provs = [shape(f["geometry"]) for f in gj["features"]]
union = unary_union(provs)
main = max(union.geoms, key=lambda p: p.area) if union.geom_type == "MultiPolygon" else union
bbox = box(*[CROP_LON[0], CROP_LAT[0], CROP_LON[1], CROP_LAT[1]])
def rings_of(geom, simp=0.003):
    geom = geom.intersection(bbox).simplify(simp)
    polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    out = []
    for p in polys:
        if p.is_empty or p.area < 1e-4: continue
        out.append([[round(x,4), round(y,4)] for x,y in p.exterior.coords])
    return out
coast = rings_of(main)
prov_rings = []
for g in provs: prov_rings += rings_of(g)
print(f"anelli costa {len(coast)} | province {len(prov_rings)}")

# --- meta stazioni (per solve + tooltip + disegno) ---
stations = [{"n": s, "p": anag[s]["prov"], "lon": round(anag[s]["lon"],5),
             "lat": round(anag[s]["lat"],5)} for s in STA]

span_x = (CROP_LON[1]-CROP_LON[0])*kx; span_y = (CROP_LAT[1]-CROP_LAT[0])
HG = int(round(WG*span_y/span_x))

# --- spline kernel LINEARE (identica a tps_core.js) per verifica PNG + ref node ---
def phi(r2):
    return np.sqrt(r2)
def solve_eval(XY, V, G):
    n = len(V)
    A = phi(cdist(XY, XY)**2); P = np.hstack([np.ones((n,1)), XY])
    M = np.block([[A, P],[P.T, np.zeros((3,3))]]); rhs = np.concatenate([V, np.zeros(3)])
    sol = np.linalg.solve(M, rhs); w = sol[:n]; poly = sol[n:]
    return phi(cdist(G, XY)**2)@w + poly[0]+poly[1]*G[:,0]+poly[2]*G[:,1]

# reference per il test node (JS<->Python), scritto accanto al test in scripts/
day = raw[3]["2026-05-01"]
XY = np.array([[anag[s]["lon"]*kx, anag[s]["lat"]] for s in day])
Vv = np.array([day[s] for s in day])
loncc = CROP_LON[0] + (np.arange(WG)+0.5)*(CROP_LON[1]-CROP_LON[0])/WG
latcc = CROP_LAT[1] - (np.arange(HG)+0.5)*(CROP_LAT[1]-CROP_LAT[0])/HG
GX, GY = np.meshgrid(loncc*kx, latcc)
field = solve_eval(XY, Vv, np.column_stack([GX.ravel(), GY.ravel()])).reshape(HG, WG)
ref = {"kx": kx, "lon": [anag[s]["lon"] for s in day], "lat": [anag[s]["lat"] for s in day],
       "V": [day[s] for s in day],
       "G": [[float(loncc[c]), float(latcc[r])] for r in (10,30,50) for c in (20,50,80)],
       "ref": [float(field[r, c]) for r in (10,30,50) for c in (20,50,80)]}
json.dump(ref, open(os.path.join(HERE, "_ref_tps.json"), "w"))

# --- payload: cube int16 gzip base64 ---
gz = gzip.compress(cube.tobytes(), 9); b64 = base64.b64encode(gz).decode()
print(f"cube {cube.nbytes/1024:.0f} KB -> gzip {len(gz)/1024:.0f} KB -> base64 {len(b64)/1024:.0f} KB")

meta = {"crop": [CROP_LON[0], CROP_LON[1], CROP_LAT[0], CROP_LAT[1]], "kx": kx,
        "wg": WG, "hg": HG, "nF": NF, "nSta": nSta, "minSta": MIN_STA,
        "years": years, "months": months,
        "vars": [{"id": f"spi{k}", "name": f"SPI-{k}", "months": k} for k in TIMESCALES],
        "stations": stations, "coast": coast, "prov": prov_rings,
        "colors": CLASS_COLORS, "labels": CLASS_LABELS, "thresh": THRESH,
        "vmin": VMIN, "vmax": VMAX}

TPS_JS = open(os.path.join(HERE, "tps_core.js")).read()
HTML = open(os.path.join(HERE, "_map_template.html")).read()
html = (HTML.replace("/*__TPS__*/", TPS_JS)
            .replace("__META__", json.dumps(meta))
            .replace("__DATA__", b64))
out = os.path.join(OUTD, "spi_sias_animata.html")
open(out, "w").write(html)
print("scritto", out, f"({os.path.getsize(out)/1024:.0f} KB)")
