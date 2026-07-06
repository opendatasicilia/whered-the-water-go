// Verifica che la TPS in JS (tps_core.js) coincida con il riferimento Python
// (scripts/_ref_tps.json, prodotto da 03_build_map_animation.py).
const fs = require("fs");
const path = require("path");
const { solveTPS, evalTPS } = require("./tps_core.js");

const ref = JSON.parse(fs.readFileSync(path.join(__dirname, "_ref_tps.json")));
const kx = ref.kx;
const X = ref.lon.map(l => l * kx), Y = ref.lat.slice(), V = ref.V.slice();
const { w, poly } = solveTPS(X, Y, V);

let maxd = 0;
ref.G.forEach((g, i) => {
  const gx = g[0] * kx, gy = g[1];
  const val = evalTPS(X, Y, w, poly, gx, gy);
  maxd = Math.max(maxd, Math.abs(val - ref.ref[i]));
});
console.log("n stazioni:", V.length, "| punti test:", ref.G.length);
console.log("max |JS - Python|:", maxd.toExponential(3));
process.exit(maxd < 1e-4 ? 0 : 1);
