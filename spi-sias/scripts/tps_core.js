/* tps_core.js - spline a base radiale con kernel LINEARE (phi(r)=r) in JS.
   Stessa formulazione di scipy RBFInterpolator(kernel="linear", smoothing=0),
   con parte polinomiale di grado 1. Kernel piu' locale della thin-plate: riproduce
   meglio le mappe ufficiali SIAS (verificato deterministicamente). Verificato vs
   scipy a ~1e-13 con node (scripts/test_tps.js). Coordinate GIA' in spazio scalato
   (X=lon*kx, Y=lat). phi2 riceve r^2 e ritorna phi(r)=r=sqrt(r^2). */
function phi2(r2){ return Math.sqrt(r2); }

// Risolve i pesi TPS per n stazioni. Ritorna {w:[n], poly:[a0,a1,a2]}.
function solveTPS(X, Y, V){
  const n = X.length, m = n + 3;
  const A = new Float64Array(m * m), b = new Float64Array(m);
  for (let i = 0; i < n; i++){
    for (let j = 0; j < n; j++){
      const dx = X[i]-X[j], dy = Y[i]-Y[j];
      A[i*m+j] = phi2(dx*dx + dy*dy);
    }
    A[i*m + n]   = 1;   A[i*m + n+1] = X[i]; A[i*m + n+2] = Y[i];
    A[(n)*m + i]   = 1; A[(n+1)*m + i] = X[i]; A[(n+2)*m + i] = Y[i];
    b[i] = V[i];
  }
  // eliminazione di Gauss con pivot parziale
  const idx = Array.from({length:m}, (_,k)=>k);
  for (let c = 0; c < m; c++){
    let piv = c, best = Math.abs(A[idx[c]*m+c]);
    for (let r = c+1; r < m; r++){ const val = Math.abs(A[idx[r]*m+c]); if (val>best){best=val;piv=r;} }
    if (piv !== c){ const t = idx[c]; idx[c] = idx[piv]; idx[piv] = t; }
    const pr = idx[c], pv = A[pr*m+c];
    for (let r = c+1; r < m; r++){
      const rr = idx[r], f = A[rr*m+c] / pv;
      if (f === 0) continue;
      for (let k = c; k < m; k++) A[rr*m+k] -= f * A[pr*m+k];
      b[rr] -= f * b[pr];
    }
  }
  const x = new Float64Array(m);
  for (let c = m-1; c >= 0; c--){
    const rr = idx[c]; let s = b[rr];
    for (let k = c+1; k < m; k++) s -= A[rr*m+k] * x[k];
    x[c] = s / A[rr*m+c];
  }
  return { w: Array.from(x.subarray(0, n)), poly: [x[n], x[n+1], x[n+2]] };
}

// Valuta la superficie in (gx,gy) [spazio scalato].
function evalTPS(X, Y, w, poly, gx, gy){
  let s = poly[0] + poly[1]*gx + poly[2]*gy;
  for (let i = 0; i < X.length; i++){
    const dx = gx-X[i], dy = gy-Y[i];
    s += w[i] * phi2(dx*dx + dy*dy);
  }
  return s;
}

if (typeof module !== "undefined" && module.exports){ module.exports = { phi2, solveTPS, evalTPS }; }
