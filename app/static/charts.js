/* Charts for NeoFold Edge. Plain SVG/canvas, no chart library, no CDN.
 *
 * Colour rules followed here:
 *   - PAE is a magnitude, so it gets ONE hue, light->dark (sequential).
 *     Near-zero error recedes into the dark surface; high error is bright.
 *     That deliberately makes the plot mostly empty when the model is
 *     confident, and makes problem regions the thing you notice.
 *   - Triage tiers are states, so they get the reserved status palette,
 *     always paired with a text label -- never colour alone.
 */

const SEQ = ['#0d366b','#104281','#184f95','#1c5cab','#256abf','#2a78d6',
             '#3987e5','#5598e7','#6da7ec','#86b6ef','#9ec5f4','#b7d3f6','#cde2fb'];
const STATUS = { good:'#0ca30c', warning:'#fab219', serious:'#ec835a',
                 critical:'#d03b3b', muted:'#8a8d8c' };
const INK = { primary:'#f6f6f6', secondary:'#9aa0a6', grid:'#3a3b3d', surface:'#1b1b1b' };

/* pLDDT bands. The THRESHOLDS and the hue order are AlphaFold's, sampled from
 * the AlphaFold DB legend and confirmed against molstar's plddt.ts. The exact
 * hexes are not, and the reason is measured rather than aesthetic.
 *
 * AlphaFold's palette is calibrated against a WHITE page. On our #1b1b1b card:
 *
 *   #0053D6  Very high (trust this)  ->   2.63:1   FAILS the 3:1 non-text floor
 *   #65CBF3  High                    ->   9.34:1
 *   #FFDB13  Low (do not trust)      ->  12.63:1   brightest thing on screen
 *   #FF7D45  Very low                ->   6.78:1
 *
 * That is an INVERTED encoding: the band meaning "this is reliable" is the
 * hardest to see, and the band meaning "this is not" dominates. Shipping the
 * canonical hexes on a dark ground would be cargo-culting the reference.
 *
 * So: same thresholds, same hue order, re-tuned for our background. Every band
 * now clears 6.2:1 and the spread is 1.7x rather than 4.8x. `afHex` keeps the
 * canonical value, for anyone rendering this on white.
 *
 * NOT the ColabFold values (#0D57D3/#6ACBF1/#FED936/#FD7D4D); those are close
 * enough to look like a typo of the canonical ones and are a different palette. */
export const PLDDT_BANDS = [
  { min:90, max:100, hex:'#6E9BF2', afHex:'#0053D6', label:'Very high', rule:'pLDDT > 90' },
  { min:70, max:90,  hex:'#7FD4F5', afHex:'#65CBF3', label:'High',      rule:'90 > pLDDT > 70' },
  { min:50, max:70,  hex:'#E5C33F', afHex:'#FFDB13', label:'Low',       rule:'70 > pLDDT > 50' },
  { min:0,  max:50,  hex:'#F2895A', afHex:'#FF7D45', label:'Very low',  rule:'pLDDT < 50' },
];
export function plddtBand(v){
  return PLDDT_BANDS.find(b => v >= b.min) || PLDDT_BANDS[PLDDT_BANDS.length - 1];
}

/* AlphaFold 3's own ipTM bands, verbatim from the AlphaFold Server FAQ. The
 * named GREY ZONE is the useful part: an officially sanctioned band that means
 * "we do not know", which is the honest reading of every ipTM we produce.
 *
 * Same dark-ground correction as above. The house diverging anchors
 * (#B2182B / #A8A9AC / #2166AC) measure 2.51 / 7.33 / 2.92 on our surface --
 * both DECIDED bands fail the floor while the UNDECIDED one is nearly 3x
 * brighter than either. "We don't know" should not be the loudest thing in
 * the component. Re-tuned to 5.5 / 5.1 / 6.3, a 1.2x spread. The grey zone
 * stays genuinely neutral in hue: the field's convention is that a provisional
 * state gets no semantic colour at all. */
export const IPTM_BANDS = [
  { lo:0,   hi:0.6, hex:'#D9737A', label:'likely failed' },
  { lo:0.6, hi:0.8, hex:'#8A8D8C', label:'grey zone' },
  { lo:0.8, hi:1.0, hex:'#6E9BF2', label:'confident' },
];

function seqColor(t){                      // t in [0,1] -> sequential step
  const i = Math.max(0, Math.min(SEQ.length - 1, Math.round(t * (SEQ.length - 1))));
  return SEQ[i];
}

function el(tag, attrs = {}, kids = []){
  const n = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  for (const k of [].concat(kids)) n.appendChild(k);
  return n;
}
function text(x, y, s, o = {}){
  return el('text', {x, y, fill:o.fill||INK.secondary, 'font-size':o.size||10,
    'text-anchor':o.anchor||'start', 'font-family':o.mono?'ui-monospace,monospace':'inherit',
    'font-weight':o.weight||400, ...(o.extra||{})}, [Object.assign(
      document.createTextNode(s))]);
}

/* ------------------------------------------------------------------ PAE */
// Fixed display ceiling. Measured distribution on a good pMHC prediction:
// median 1.3 A, 75th pct 2.0, 95th 4.0, but a handful of terminal residues
// reach 21. Scaling to the true max would spend the whole ramp on 2.5% of the
// cells and render everything else a flat mid-blue. Clip instead, and say so.
const PAE_CEILING = 8;

export function drawPae(container, data, tip){
  const pae = data.pae, n = pae.length, max = PAE_CEILING;
  container.innerHTML = '';

  const size = Math.min(container.clientWidth || 330, 330);
  const pad = 34;
  const plot = size - pad - 8;

  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = n;                // 1 cell = 1 device px
  canvas.style.cssText =
    `width:${plot}px;height:${plot}px;position:absolute;left:${pad}px;top:0;` +
    `image-rendering:pixelated;border:1px solid ${INK.grid};border-radius:3px`;
  const ctx = canvas.getContext('2d');
  const img = ctx.createImageData(n, n);
  for (let i = 0; i < n; i++){
    for (let j = 0; j < n; j++){
      const hex = seqColor(Math.min(1, pae[i][j] / max));
      const p = (i * n + j) * 4;
      img.data[p]   = parseInt(hex.slice(1,3),16);
      img.data[p+1] = parseInt(hex.slice(3,5),16);
      img.data[p+2] = parseInt(hex.slice(5,7),16);
      img.data[p+3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);

  const wrap = document.createElement('div');
  wrap.style.cssText = `position:relative;height:${plot + 26}px`;
  wrap.appendChild(canvas);

  // Chain bands along both axes, so the block structure is readable.
  const svg = el('svg', {width:size, height:plot + 26,
                         style:'position:absolute;left:0;top:0;overflow:visible'});
  const scale = v => pad + (v / n) * plot;
  for (const c of data.chains){
    const a = scale(c.start), b = scale(c.end + 1);
    svg.appendChild(el('rect', {x:a, y:plot + 4, width:Math.max(1, b - a), height:4,
                                fill: c.id === 'C' ? '#ffa657' : INK.secondary,
                                opacity: c.id === 'C' ? 1 : .45, rx:2}));
    svg.appendChild(el('rect', {x:pad - 8, y:a - pad + 0, width:4,
                                height:Math.max(1, b - a),
                                fill: c.id === 'C' ? '#ffa657' : INK.secondary,
                                opacity: c.id === 'C' ? 1 : .45, rx:2}));
    if (c.length > 40)
      svg.appendChild(text((a + b) / 2, plot + 20, c.id, {anchor:'middle', size:9}));
  }
  // AFDB labels these axes; unlabelled, the plot is just a pretty square.
  svg.appendChild(text(pad + plot / 2, plot + 24, 'scored residue',
                       {anchor:'middle', size:9}));
  const ay = plot / 2, ax = pad - 24;
  svg.appendChild(text(ax, ay, 'aligned residue',
                       {anchor:'middle', size:9,
                        extra:{transform:`rotate(-90 ${ax} ${ay})`}}));
  wrap.appendChild(svg);
  container.appendChild(wrap);

  // Colour key. Without it "dark is good" is just an assertion.
  const key = document.createElement('div');
  key.style.cssText = 'display:flex;align-items:center;gap:7px;margin:8px 0 0 ' +
                      `${pad}px;font-size:9.5px;color:${INK.secondary}`;
  const ramp = SEQ.map(c => `<span style="flex:1;height:8px;background:${c}"></span>`).join('');
  key.innerHTML = `<span>0 Å</span>
    <span style="display:flex;flex:1;max-width:150px;border-radius:2px;overflow:hidden">${ramp}</span>
    <span>${PAE_CEILING}+ Å</span><span style="opacity:.75">lower is better</span>`;
  container.appendChild(key);

  // Hover: report the actual pair, because "which two residues" is the question.
  canvas.addEventListener('mousemove', ev => {
    const r = canvas.getBoundingClientRect();
    const j = Math.floor((ev.clientX - r.left) / r.width * n);
    const i = Math.floor((ev.clientY - r.top) / r.height * n);
    if (i < 0 || j < 0 || i >= n || j >= n) return;
    const name = k => (data.chains.find(c => k >= c.start && k <= c.end) || {}).label || '?';
    const idx = k => { const c = data.chains.find(c => k >= c.start && k <= c.end);
                       return c ? k - c.start + 1 : k; };
    // PAE is asymmetric: (x,y) != (y,x). Say which is which.
    tip(ev, `scored ${name(j)} ${idx(j)} · aligned on ${name(i)} ${idx(i)}`
          + `<b>${pae[i][j].toFixed(1)} Å</b>`
          + `<i>expected error in the scored residue's position when the two `
          + `structures are superposed on the aligned one</i>`);
  });
  canvas.addEventListener('mouseleave', () => tip(null));
}

/* --------------------------------------------------------------- pLDDT */
export function drawPlddt(container, data, tip){
  const v = data.plddt, n = v.length;
  container.innerHTML = '';
  const w = container.clientWidth || 330, h = 86, padL = 30, padB = 16;
  const pw = w - padL - 6, ph = h - padB - 6;
  const x = i => padL + (i / (n - 1)) * pw;
  const y = t => 6 + (1 - (t - 50) / 50) * ph;      // 50..100 band

  const svg = el('svg', {width:w, height:h, style:'display:block'});

  // We were already drawing gridlines at 50/70/90/100 -- the exact AlphaFold
  // band edges -- and then filling the area a flat blue. Paint the bands.
  for (const b of PLDDT_BANDS){
    const top = y(Math.min(100, b.max)), bot = y(Math.max(50, b.min));
    if (bot <= top) continue;
    svg.appendChild(el('rect', {x:padL, y:top, width:w - 6 - padL,
                                height:bot - top, fill:b.hex, opacity:.10}));
  }
  for (const g of [50, 70, 90, 100]){
    svg.appendChild(el('line', {x1:padL, x2:w - 6, y1:y(g), y2:y(g),
                                stroke:INK.grid, 'stroke-width':1, opacity:.7}));
    svg.appendChild(text(padL - 5, y(g) + 3, g, {anchor:'end', size:9}));
  }
  let d = `M ${x(0)} ${y(v[0])}`;
  for (let i = 1; i < n; i++) d += ` L ${x(i)} ${y(v[i])}`;
  svg.appendChild(el('path', {d:`${d} L ${x(n-1)} ${y(50)} L ${x(0)} ${y(50)} Z`,
                              fill:PLDDT_BANDS[0].hex, opacity:.10}));
  // Segment the stroke by band, so the trace and the Mol* cartoon above it are
  // the same colours for the same reason.
  for (let i = 1; i < n; i++){
    const b = plddtBand(Math.min(v[i], v[i-1]));
    svg.appendChild(el('line', {x1:x(i-1), y1:y(v[i-1]), x2:x(i), y2:y(v[i]),
                                stroke:b.hex, 'stroke-width':2,
                                'stroke-linecap':'round'}));
  }

  for (const c of data.chains){
    const a = x(c.start), b = x(c.end);
    svg.appendChild(el('rect', {x:a, y:h - 8, width:Math.max(2, b - a), height:3,
                                rx:1.5, fill:c.id === 'C' ? '#ffa657' : INK.secondary,
                                opacity:c.id === 'C' ? 1 : .45}));
  }
  // The peptide is 9 of 383 residues -- call it out or it vanishes.
  const pep = data.chains.find(c => c.id === 'C');
  if (pep){
    svg.appendChild(el('rect', {x:x(pep.start) - 1, y:4, width:Math.max(3, x(pep.end) - x(pep.start) + 2),
                                height:ph + 4, fill:'#ffa657', opacity:.12}));
    // The peptide is the last 9 of 383 residues, so the label would run off
    // the right edge: anchor it to the end instead.
    svg.appendChild(text(x(pep.start) - 4, 14, 'peptide',
                         {size:9, fill:'#ffa657', anchor:'end'}));
  }
  container.appendChild(svg);

  svg.addEventListener('mousemove', ev => {
    const r = svg.getBoundingClientRect();
    const i = Math.round(((ev.clientX - r.left) - padL) / pw * (n - 1));
    if (i < 0 || i >= n) return;
    const c = data.chains.find(c => i >= c.start && i <= c.end);
    const b = plddtBand(v[i]);
    tip(ev, `${c ? c.label : ''} residue ${c ? i - c.start + 1 : i}`
          + `<b>pLDDT ${v[i].toFixed(1)}</b>`
          + `<i style="color:${b.hex}">${b.label} (${b.rule})</i>`);
  });
  svg.addEventListener('mouseleave', () => tip(null));
}

/* ----------------------------------------------------- screening scatter */
export function drawLandscape(container, rows, tip, onPick){
  container.innerHTML = '';
  const pts = rows.filter(r => isFinite(r.affinity_nm) && isFinite(r.dai)
                            && r.dai > 0);
  if (!pts.length) return;

  const w = container.clientWidth || 380, h = 240, padL = 44, padB = 34;
  const pw = w - padL - 14, ph = h - padB - 14;
  const lx = v => Math.log10(Math.max(1, v));
  const ly = v => Math.log10(Math.max(0.05, v));
  const xs = pts.map(p => lx(p.affinity_nm)), ys = pts.map(p => ly(p.dai));
  const x0 = Math.min(...xs), x1 = Math.max(...xs);
  const y0 = Math.min(...ys), y1 = Math.max(...ys);
  const X = v => padL + (lx(v) - x0) / (x1 - x0 || 1) * pw;
  const Y = v => 14 + (1 - (ly(v) - y0) / (y1 - y0 || 1)) * ph;

  const svg = el('svg', {width:w, height:h, style:'display:block;overflow:visible'});

  // Threshold lines ARE the triage rule, drawn.
  svg.appendChild(el('line', {x1:X(500), x2:X(500), y1:14, y2:14 + ph,
                              stroke:INK.grid, 'stroke-width':1, 'stroke-dasharray':'3 3'}));
  svg.appendChild(text(X(500) - 4, 12, '500 nM', {anchor:'end', size:9}));
  svg.appendChild(el('line', {x1:padL, x2:padL + pw, y1:Y(10), y2:Y(10),
                              stroke:INK.grid, 'stroke-width':1, 'stroke-dasharray':'3 3'}));
  svg.appendChild(text(padL + pw, Y(10) - 4, 'DAI ≥ 10 — reference only, not a gate',
                       {anchor:'end', size:9}));

  for (const v of [1, 10, 100, 1000, 10000])
    if (lx(v) >= x0 && lx(v) <= x1)
      svg.appendChild(text(X(v), h - 18, v >= 1000 ? `${v/1000}k` : v,
                           {anchor:'middle', size:9}));
  for (const v of [0.1, 1, 10, 100])
    if (ly(v) >= y0 && ly(v) <= y1)
      svg.appendChild(text(padL - 7, Y(v) + 3, `${v}×`, {anchor:'end', size:9}));

  svg.appendChild(text(padL + pw / 2, h - 4, 'predicted affinity (nM, lower = stronger)',
                       {anchor:'middle', size:9.5}));

  const colour = t => t === 'investigate' ? STATUS.good
                    : t === 'not tumour-specific' ? STATUS.warning
                    : t === 'weak presentation' ? STATUS.serious : STATUS.muted;

  for (const p of pts.slice().reverse()){
    const investigate = p.tier === 'investigate';
    // Deprioritised points were drawn at r=3, opacity .5, in a grey barely
    // above the panel: the plot read as empty. But the POINT of the chart is
    // that the shortlist is a tiny corner of a crowded field, so the crowd has
    // to be visible. Smaller radius, much higher opacity: a dense fog of small
    // visible dots beats a sparse scatter of grey smudges.
    const c = el('circle', {cx:X(p.affinity_nm), cy:Y(p.dai),
      r: investigate ? 5.5 : 2.4, fill:colour(p.tier),
      opacity: investigate ? 1 : .82,
      stroke: investigate ? INK.surface : 'none', 'stroke-width':2,
      style:'cursor:pointer'});
    c.addEventListener('mousemove', ev => tip(ev,
      `<b>${p.peptide}</b>${p.candidate_id.split('-').slice(0,2).join(' ')}`
      + `${p.affinity_nm.toFixed(0)} nM · DAI ${p.dai.toFixed(1)}`
      + `<i>${p.tier}</i>`));
    c.addEventListener('mouseleave', () => tip(null));
    if (onPick) c.addEventListener('click', () => onPick(p));
    svg.appendChild(c);
  }
  container.appendChild(svg);
}

export const TIER_COLOURS = STATUS;

/* ------------------------------------------------- measured vs projected */
export function drawScaling(container, b, tip){
  container.innerHTML = '';
  const nodes = b.projected.nodes;
  const w = container.clientWidth || 380, h = 190, padL = 46, padB = 34;
  const pw = w - padL - 16, ph = h - padB - 18;
  const maxY = Math.max(...nodes.map(n => n.candidates_per_hour)) * 1.15;
  const X = i => padL + (i + 0.5) * (pw / nodes.length);
  const Y = v => 18 + (1 - v / maxY) * ph;

  const svg = el('svg', {width:w, height:h, style:'display:block;overflow:visible'});
  for(const g of [0, maxY/2, maxY]){
    svg.appendChild(el('line', {x1:padL, x2:padL+pw, y1:Y(g), y2:Y(g),
                                stroke:INK.grid, 'stroke-width':1}));
    svg.appendChild(text(padL-6, Y(g)+3, Math.round(g), {anchor:'end', size:9}));
  }

  const bw = Math.min(56, pw / nodes.length - 16);
  nodes.forEach((n, i) => {
    const measured = n.measured;
    const x = X(i) - bw/2, y = Y(n.candidates_per_hour);
    // Measured bars are solid; projections are hollow with a dashed outline,
    // so the distinction survives a photograph of a slide.
    const r = el('rect', {x, y, width:bw, height:Y(0)-y, rx:4,
      fill: measured ? '#2a78d6' : 'none',
      stroke: measured ? 'none' : '#2a78d6',
      'stroke-width': measured ? 0 : 2,
      'stroke-dasharray': measured ? '' : '5 3', style:'cursor:pointer'});
    r.addEventListener('mousemove', ev => tip(ev,
      `<b>${n.candidates_per_hour} candidates/hour</b>${n.label || (n.nodes+' Nano')}`
      + `<i>${measured ? 'measured on hardware' : 'projected from measured single-node throughput'}</i>`));
    r.addEventListener('mouseleave', () => tip(null));
    svg.appendChild(r);
    const lbl = n.label || `${n.nodes} node${n.nodes>1?'s':''}`;
    lbl.split(', ').forEach((part, k) =>
      svg.appendChild(text(X(i), Y(0)+15+k*11, part, {anchor:'middle', size:9.5})));
    svg.appendChild(text(X(i), y-6, n.candidates_per_hour,
                         {anchor:'middle', size:11, weight:600,
                          fill: measured ? INK.primary : INK.secondary, mono:true}));
  });
  svg.appendChild(text(padL, 10, 'candidates / hour', {size:9.5}));
  container.appendChild(svg);
}

/* ------------------------------------------------------- MD contact traces */
export function drawMdTraces(container, md, tip, key = 'contacts'){
  container.innerHTML = '';
  const groups = [['mutant', '#0ca30c'], ['wild_type', '#fab219']];
  const all = groups.flatMap(([g]) => (md.traces[g] || []).flatMap(r => r[key]));
  if (!all.length) return;

  const w = container.clientWidth || 380, h = 180, padL = 40, padB = 30;
  const pw = w - padL - 14, ph = h - padB - 16;
  const maxT = Math.max(...groups.flatMap(([g]) =>
    (md.traces[g] || []).flatMap(r => r.t)));
  const lo = key === 'contacts' ? 0 : 0;
  const hi = key === 'contacts' ? 1 : Math.max(4, Math.max(...all) * 1.1);
  const X = t => padL + (t / maxT) * pw;
  const Y = v => 16 + (1 - (v - lo) / (hi - lo)) * ph;

  const svg = el('svg', {width:w, height:h, style:'display:block;overflow:visible'});
  for (const g of [lo, (lo+hi)/2, hi]){
    svg.appendChild(el('line', {x1:padL, x2:padL+pw, y1:Y(g), y2:Y(g),
                                stroke:INK.grid, 'stroke-width':1}));
    svg.appendChild(text(padL-6, Y(g)+3, g.toFixed(key==='contacts'?1:0),
                         {anchor:'end', size:9}));
  }
  for (const [g, colour] of groups){
    for (const run of (md.traces[g] || [])){
      const pts = run[key].map((v,i) => `${X(run.t[i])},${Y(v)}`).join(' ');
      svg.appendChild(el('polyline', {points:pts, fill:'none', stroke:colour,
                                      'stroke-width':1.6, opacity:.75,
                                      'stroke-linejoin':'round'}));
    }
  }
  svg.appendChild(text(padL + pw/2, h - 4, 'simulated time (ps)',
                       {anchor:'middle', size:9.5}));
  svg.appendChild(text(padL, 10,
    key === 'contacts' ? 'fraction of starting peptide–HLA contacts retained'
                       : 'peptide RMSD from starting pose (Å)', {size:9.5}));
  container.appendChild(svg);
}

/* --------------------------------------------- precision at depth vs base */
export function drawPrecisionAtK(container, series, baseRate, tip){
  container.innerHTML = '';
  const ks = [10,25,50,100];
  const w = container.clientWidth || 380, h = 200, padL = 40, padB = 34;
  const pw = w - padL - 14, ph = h - padB - 18;
  const maxY = Math.max(baseRate*1.2, ...series.flatMap(s => s.points.map(p => p.precision))) * 1.15;
  const X = (i, n, j) => padL + (i + 0.5)*(pw/ks.length) - (n-1)*7 + j*14;
  const Y = v => 18 + (1 - v/maxY)*ph;

  const svg = el('svg', {width:w, height:h, style:'display:block;overflow:visible'});
  for(const g of [0, maxY/2, maxY]){
    svg.appendChild(el('line', {x1:padL, x2:padL+pw, y1:Y(g), y2:Y(g),
                                stroke:INK.grid, 'stroke-width':1}));
    svg.appendChild(text(padL-6, Y(g)+3, `${(g*100).toFixed(0)}%`, {anchor:'end', size:9}));
  }
  // The base rate is the line everything is judged against.
  svg.appendChild(el('line', {x1:padL, x2:padL+pw, y1:Y(baseRate), y2:Y(baseRate),
                              stroke:STATUS.critical, 'stroke-width':1.5, 'stroke-dasharray':'4 3'}));
  svg.appendChild(text(padL+pw, Y(baseRate)-5, `base rate ${(baseRate*100).toFixed(1)}%`,
                       {anchor:'end', size:9, fill:STATUS.critical}));

  ks.forEach((k, i) => {
    series.forEach((s, j) => {
      const pt = s.points.find(p => p.k === k);
      if(!pt) return;
      const x = X(i, series.length, j), y = Y(pt.precision);
      const bw = 12;
      const r = el('rect', {x:x-bw/2, y, width:bw, height:Y(0)-y, rx:3,
                            fill:s.colour, style:'cursor:pointer'});
      r.addEventListener('mousemove', ev => tip(ev,
        `<b>${(pt.precision*100).toFixed(0)}% precision</b>${s.label} · top ${k}`
        + `<i>${pt.hits}/${k} true responders · ${(pt.precision/baseRate).toFixed(1)}× base rate</i>`));
      r.addEventListener('mouseleave', () => tip(null));
      svg.appendChild(r);
    });
    svg.appendChild(text(X(i, 1, 0), Y(0)+15, `top ${k}`, {anchor:'middle', size:9.5}));
  });
  svg.appendChild(text(padL, 10, 'precision = fraction that are true T-cell responders', {size:9.5}));
  container.appendChild(svg);
}

/* --------------------------------------------------------------- ROC */
/* AUC is one number and one number hides the shape. A rule can reach 0.75 by
 * being excellent on the top 5% and useless after, or mediocre throughout --
 * different tools, same summary statistic. The curve shows which.
 *
 * It also makes the DAI failure visible rather than asserted: a curve hugging
 * the diagonal, and on TESLA crossing BELOW it, is an argument no bar makes. */
export function drawRoc(container, block, tip, opts = {}){
  container.innerHTML = '';
  const w = Math.min(container.clientWidth || 360, opts.max || 400);
  const padL = 40, padB = 34, padT = 14, padR = 12;
  const side = Math.min(w - padL - padR, 260);
  const h = side + padB + padT;
  const X = v => padL + v * side;
  const Y = v => padT + (1 - v) * side;

  const svg = el('svg', {width:w, height:h, style:'display:block;overflow:visible'});

  // Shade below the diagonal. A curve entering it is worse than guessing, and
  // that should look wrong before anyone reads the legend.
  svg.appendChild(el('path', {
    d:`M ${X(0)} ${Y(0)} L ${X(1)} ${Y(0)} L ${X(1)} ${Y(1)} Z`,
    fill:STATUS.critical, opacity:.055}));
  svg.appendChild(text(X(.97), Y(.10), 'worse than chance',
                       {anchor:'end', size:9, fill:STATUS.critical, extra:{opacity:.8}}));

  for (const g of [0, .25, .5, .75, 1]){
    svg.appendChild(el('line', {x1:X(0), x2:X(1), y1:Y(g), y2:Y(g),
                                stroke:INK.grid, 'stroke-width':1, opacity:.55}));
    svg.appendChild(el('line', {x1:X(g), x2:X(g), y1:Y(0), y2:Y(1),
                                stroke:INK.grid, 'stroke-width':1, opacity:.35}));
    svg.appendChild(text(padL - 6, Y(g) + 3, g.toFixed(g % 1 ? 2 : 0),
                         {anchor:'end', size:9}));
    svg.appendChild(text(X(g), Y(0) + 14, g.toFixed(g % 1 ? 2 : 0),
                         {anchor:'middle', size:9}));
  }
  svg.appendChild(el('line', {x1:X(0), x2:X(1), y1:Y(0), y2:Y(1),
                              stroke:INK.secondary, 'stroke-width':1,
                              'stroke-dasharray':'4 4', opacity:.7}));

  for (const s of block.series){
    if (!s.points || s.points.length < 2) continue;
    const d = s.points.map((p, i) =>
      `${i ? 'L' : 'M'} ${X(p[0]).toFixed(1)} ${Y(p[1]).toFixed(1)}`).join(' ');
    const path = el('path', {d, fill:'none', stroke:s.colour,
      'stroke-width': s.ours ? 2.4 : 1.8,
      'stroke-linejoin':'round', 'stroke-linecap':'round',
      'stroke-dasharray': s.ours ? '' : '5 3',
      opacity: s.ours ? 1 : .85, style:'cursor:pointer'});
    path.addEventListener('mousemove', ev => tip(ev,
      `<b>AUC ${s.auc.toFixed(3)}</b>${s.label}`
      + `<i>${s.ours ? 'our prediction' : 'reference metric'}`
      + `${s.auc < 0.5 ? ' — below random' : ''}</i>`));
    path.addEventListener('mouseleave', () => tip(null));
    svg.appendChild(path);
  }

  svg.appendChild(text(padL + side / 2, h - 3, 'false positive rate',
                       {anchor:'middle', size:9.5}));
  svg.appendChild(text(padL, 9, 'true positive rate', {size:9.5}));
  container.appendChild(svg);

  // Legend carries the AUC, so the curve and its summary are never separated.
  const leg = document.createElement('div');
  leg.style.cssText = 'display:flex;flex-direction:column;gap:4px;margin:8px 0 0 ' +
                      `${padL}px;font-size:11px;color:${INK.secondary}`;
  leg.innerHTML = block.series.map(s => `
    <span style="display:flex;align-items:center;gap:7px">
      <span style="width:16px;height:0;border-top:${s.ours ? 2.4 : 1.8}px ${s.ours ? 'solid' : 'dashed'} ${s.colour};flex:none"></span>
      <span style="flex:1">${s.label}</span>
      <span style="font-family:ui-monospace,monospace;color:${
        s.auc < 0.5 ? STATUS.critical : INK.primary};font-weight:600">${s.auc.toFixed(3)}</span>
    </span>`).join('');
  container.appendChild(leg);
}

/* --------------------------------- confidence vs measured error (holdout) */
/* The project's central finding, drawn. Every prediction sits in a narrow band
 * of confidence while its ACTUAL error varies by a factor of two. If the score
 * were informative the cloud would slope down to the right; it does not. */
export function drawConfidenceVsError(container, rows, tip){
  container.innerHTML = '';
  const pts = rows.filter(r => isFinite(r.iptm) && isFinite(r.bb));
  if (pts.length < 3) return;

  const w = container.clientWidth || 380, h = 250, padL = 44, padB = 36, padT = 16;
  const pw = w - padL - 16, ph = h - padB - padT;

  // Confidence axis is deliberately NOT zoomed to the data: 0.97-0.99 stretched
  // across the panel would manufacture a spread that is not there. Show the
  // top tenth of the scale and let the clustering be the message.
  const x0 = 0.90, x1 = 1.0;
  const y1 = Math.max(2.0, Math.max(...pts.map(p => p.bb)) * 1.1);
  const X = v => padL + (v - x0) / (x1 - x0) * pw;
  const Y = v => padT + (1 - v / y1) * ph;

  const svg = el('svg', {width:w, height:h, style:'display:block;overflow:visible'});
  for (const g of [0, 0.5, 1, 1.5, 2].filter(g => g <= y1)){
    svg.appendChild(el('line', {x1:padL, x2:padL + pw, y1:Y(g), y2:Y(g),
                                stroke:INK.grid, 'stroke-width':1, opacity:.6}));
    svg.appendChild(text(padL - 6, Y(g) + 3, g.toFixed(1), {anchor:'end', size:9}));
  }
  for (const g of [0.90, 0.925, 0.95, 0.975, 1.0])
    svg.appendChild(text(X(g), h - 20, g.toFixed(3).replace(/0+$/,'').replace(/\.$/,''),
                         {anchor:'middle', size:9}));

  // The 2 A line: below it, a prediction is useful for our purpose.
  if (y1 >= 2){
    svg.appendChild(el('line', {x1:padL, x2:padL + pw, y1:Y(2), y2:Y(2),
                                stroke:STATUS.warning, 'stroke-width':1,
                                'stroke-dasharray':'4 3', opacity:.7}));
    svg.appendChild(text(padL + pw, Y(2) - 5, '2 Å', {anchor:'end', size:9,
                                                      fill:STATUS.warning}));
  }

  // The span the confidence score actually occupies -- the whole point.
  const ix = pts.map(p => p.iptm);
  const lo = Math.min(...ix), hi = Math.max(...ix);
  svg.appendChild(el('rect', {x:X(lo), y:padT, width:Math.max(2, X(hi) - X(lo)),
                              height:ph, fill:'#2a78d6', opacity:.07}));
  svg.appendChild(text((X(lo) + X(hi)) / 2, padT - 4,
                       `every prediction lands in ${(hi - lo).toFixed(3)} of ipTM`,
                       {anchor:'middle', size:9, fill:INK.secondary}));

  for (const p of pts){
    const held = !!p.post;
    const c = el('circle', {cx:X(p.iptm), cy:Y(p.bb), r:held ? 5 : 4.5,
      fill: held ? '#2a78d6' : 'none',
      stroke: held ? INK.surface : INK.secondary,
      'stroke-width': held ? 1.5 : 1.5,
      'stroke-dasharray': held ? '' : '3 2',
      opacity: held ? .95 : .8, style:'cursor:pointer'});
    c.addEventListener('mousemove', ev => tip(ev,
      `<b>${p.pdb}</b>${p.pep} · deposited ${p.dep}`
      + `ipTM ${p.iptm.toFixed(3)} · backbone RMSD ${p.bb.toFixed(2)} Å`
      + `<i>${held ? 'held out — after the training cutoff'
                   : 'before the 2023-06-01 cutoff; may be memorised'}</i>`));
    c.addEventListener('mouseleave', () => tip(null));
    svg.appendChild(c);
  }

  svg.appendChild(text(padL + pw / 2, h - 4,
                       'model confidence (ipTM) — higher should mean better',
                       {anchor:'middle', size:9.5}));
  svg.appendChild(text(padL, 10, 'measured error vs crystal (Å)', {size:9.5}));
  container.appendChild(svg);
}

/* ------------------------------------------------------- peptide track */
/* One box per residue. Which positions the T-cell can actually see is the
 * single most load-bearing fact about a candidate, and a sequence string does
 * not carry it. Anchors point INTO the groove; the receptor never sees them. */
export function drawPeptideTrack(container, peptide, wt, mutOffset){
  container.innerHTML = '';
  const n = peptide.length;
  if (!n) return;
  const wrap = document.createElement('div');
  wrap.style.cssText = 'display:flex;gap:3px;align-items:flex-end;flex-wrap:nowrap';

  for (let i = 0; i < n; i++){
    const anchor = (i === 1 || i === n - 1);
    const mutated = (i === mutOffset);
    const changed = wt && wt[i] && wt[i] !== peptide[i];
    const cell = document.createElement('div');
    cell.style.cssText = 'flex:1;min-width:0;text-align:center';
    const face = mutated || changed ? '#ffa657' : anchor ? '#6e7681' : INK.primary;
    const bg = mutated || changed ? 'rgba(255,166,87,.14)'
             : anchor ? 'rgba(110,118,129,.12)' : 'transparent';
    cell.innerHTML = `
      <div style="font-size:8.5px;color:${INK.secondary};letter-spacing:.04em">${
        i === 0 ? 'P1' : i === n - 1 ? 'PΩ' : 'P' + (i + 1)}</div>
      <div style="font-family:ui-monospace,monospace;font-size:15px;font-weight:650;
                  color:${face};background:${bg};border:1px solid ${
        mutated || changed ? '#7a4a20' : anchor ? INK.grid : 'transparent'};
                  border-radius:5px;padding:5px 0;margin-top:2px">${peptide[i]}</div>
      ${wt && changed ? `<div style="font-family:ui-monospace,monospace;font-size:10px;
                  color:${INK.secondary};margin-top:2px">${wt[i]}</div>` : ''}
      <div style="font-size:7.5px;color:${anchor ? '#6e7681' : '#3f8f5f'};
                  margin-top:3px;letter-spacing:.03em">${
        anchor ? 'anchor' : 'TCR'}</div>`;
    wrap.appendChild(cell);
  }
  container.appendChild(wrap);
}

/* ------------------------------------------------ ipTM band slider (RCSB idiom) */
/* Three bare mono numbers cannot answer "is that good?". The wwPDB validation
 * slider answers it by putting the value against a named reference scale with
 * the poles labelled. AlphaFold 3 supplies the bands; this draws them.
 *
 * The grey zone is labelled with AlphaFold's own words, because "we do not
 * know" is the honest reading of nearly every ipTM this project produces. */
export function drawIptmBand(container, value, opts = {}){
  container.innerHTML = '';
  const w = container.clientWidth || 300, h = 46, padL = 4, padR = 4;
  const bw = w - padL - padR, trackY = 14, trackH = 9;
  const X = v => padL + v * bw;

  const svg = el('svg', {width:w, height:h, style:'display:block;overflow:visible'});
  for (const b of IPTM_BANDS){
    svg.appendChild(el('rect', {x:X(b.lo), y:trackY, width:X(b.hi) - X(b.lo),
                                height:trackH, fill:b.hex, opacity:.42}));
    if (X(b.hi) - X(b.lo) > 46)
      svg.appendChild(text((X(b.lo) + X(b.hi)) / 2, trackY - 4, b.label,
                           {anchor:'middle', size:8.5,
                            fill: b.label === 'grey zone' ? INK.primary : INK.secondary,
                            weight: b.label === 'grey zone' ? 600 : 400}));
  }
  for (const g of [0, 0.6, 0.8, 1.0]){
    svg.appendChild(el('line', {x1:X(g), x2:X(g), y1:trackY, y2:trackY + trackH + 3,
                                stroke:INK.grid, 'stroke-width':1}));
    svg.appendChild(text(X(g), trackY + trackH + 13, g.toFixed(1),
                         {anchor: g === 0 ? 'start' : g === 1 ? 'end' : 'middle', size:8.5}));
  }
  const v = Math.max(0, Math.min(1, value));
  // Marker is a notch through the track, not a dot on it: at 0.99 a dot would
  // sit half outside the bar.
  svg.appendChild(el('rect', {x:X(v) - 1.5, y:trackY - 3, width:3, height:trackH + 6,
                              rx:1.5, fill:INK.primary}));
  if (opts.note)
    svg.appendChild(text(padL, h - 1, opts.note, {size:8.5, fill:INK.secondary}));
  container.appendChild(svg);
}

/* --------------------------------------- pLDDT distribution (AFDB pattern) */
/* A mean confidence alone is a lie of omission. AlphaFold DB prints the mean
 * and then, immediately under it, the four-band breakdown behind it. Four
 * lines, and the mean stops being a lie. */
export function drawPlddtDistribution(container, values){
  container.innerHTML = '';
  const v = values.filter(x => isFinite(x));
  if (!v.length) return;
  const counts = PLDDT_BANDS.map(b => ({
    band: b, n: v.filter(x => x >= b.min && (b.max >= 100 ? true : x < b.max)).length }));

  const wrap = document.createElement('div');
  wrap.style.cssText = 'display:flex;flex-direction:column;gap:3px';
  wrap.innerHTML = counts.filter(c => c.n).map(c => {
    const pct = 100 * c.n / v.length;
    return `<span style="display:flex;align-items:center;gap:7px;font-size:11px;
                         color:${INK.secondary}">
      <span style="width:9px;height:9px;border-radius:2px;background:${c.band.hex};flex:none"></span>
      <span style="font-family:ui-monospace,monospace;color:${INK.primary};
                   font-variant-numeric:tabular-nums;min-width:44px;text-align:right">${pct.toFixed(1)}%</span>
      <span>${c.band.label}</span>
      <span style="opacity:.6;font-size:10px">${c.band.rule}</span>
    </span>`; }).join('');
  container.appendChild(wrap);
}

/* ------------------------------------------------------------- the funnel */
/* Five equal boxes reading 50 / 1,890 / 13 / 22 / 5 do not encode that 98.8%
 * of candidates were removed -- and a removal count sitting in a row of
 * survivor counts reads as if the sequence were 1,890 -> 13 -> 22.
 *
 * So: survivors get a log-width bar, removals get an inset negative treatment
 * and a minus sign, and the attrition is printed between steps. */
export function drawFunnel(container, steps){
  container.innerHTML = '';
  const survivors = steps.filter(s => !s.cut);
  const top = Math.max(...survivors.map(s => s.n), 1);
  const wrap = document.createElement('div');
  wrap.style.cssText = 'display:flex;flex-direction:column;gap:5px';

  let prev = null;
  for (const s of steps){
    const row = document.createElement('div');
    if (!s.cut && prev !== null && prev > 0 && s.n < prev){
      const drop = 100 * (1 - s.n / prev);
      const d = document.createElement('div');
      d.style.cssText = `font-size:10px;color:${STATUS.critical};padding:0 0 0 10px;
                         letter-spacing:.02em;opacity:.9`;
      d.textContent = `↓ −${drop.toFixed(drop >= 99 ? 1 : 0)}%`;
      wrap.appendChild(d);
    }
    // Log width: 1,890 against 5 on a linear scale renders the shortlist as
    // a hairline, which is true but unreadable.
    const frac = s.cut ? 0.22
               : Math.max(0.06, Math.log10(Math.max(1, s.n) + 1) / Math.log10(top + 1));
    row.style.cssText = 'position:relative;border-radius:6px;overflow:hidden;' +
      `border:1px solid ${s.cut ? 'rgba(208,59,59,.35)' : 'rgba(255,255,255,.10)'};` +
      `background:${s.cut ? 'rgba(208,59,59,.07)' : 'rgba(255,255,255,.03)'}`;
    row.innerHTML = `
      <div style="position:absolute;inset:0 auto 0 0;width:${(frac * 100).toFixed(1)}%;
                  background:${s.cut ? 'rgba(208,59,59,.13)'
                                     : s.final ? 'rgba(12,163,12,.16)' : 'rgba(42,120,214,.16)'}"></div>
      <div style="position:relative;display:flex;align-items:baseline;gap:9px;padding:7px 11px">
        <span style="font-family:ui-monospace,monospace;font-size:17px;font-weight:650;
                     font-variant-numeric:tabular-nums;letter-spacing:-.02em;
                     min-width:5ch;text-align:right;
                     color:${s.cut ? STATUS.critical : s.final ? STATUS.good : INK.primary}">${
        s.cut ? '−' : ''}${s.n.toLocaleString()}</span>
        <span style="font-size:11.5px;color:${INK.secondary}">${s.label}</span>
        ${s.note ? `<span style="margin-left:auto;font-size:10.5px;color:${INK.secondary};
                                 opacity:.8">${s.note}</span>` : ''}
      </div>`;
    wrap.appendChild(row);
    if (!s.cut) prev = s.n;
  }
  container.appendChild(wrap);
}

/* ---------------------------------------------------- filter enrichment */
/* Every triage rule we considered, measured against the 2.72% base rate on
 * 1,947 peptides with real assay outcomes. 1.0x is the line that matters: a
 * rule to its left is worse than picking at random.
 *
 * Our first shipped filter, DAI >= 2, lands at 0.965x. Drawing it is a better
 * argument than writing it down, which is why this chart exists. */
export function drawEnrichment(container, rules, tip){
  container.innerHTML = '';
  const rows = rules.filter(r => !/^random/.test(r.rule));
  if (!rows.length) return;

  const w = container.clientWidth || 380;
  const rowH = 22, padL = 232, padR = 46, padT = 18;
  const h = padT + rows.length * rowH + 22;
  const pw = Math.max(80, w - padL - padR);
  const hi = Math.max(2.4, ...rows.map(r => r.enrichment)) * 1.04;
  const X = v => padL + (v / hi) * pw;

  const svg = el('svg', {width:w, height:h, style:'display:block;overflow:visible'});

  // Everything left of 1.0x is worse than chance. Shade it, so a bar that
  // ends inside it looks wrong before the label is read.
  svg.appendChild(el('rect', {x:padL, y:padT - 4, width:X(1) - padL,
                              height:rows.length * rowH + 4,
                              fill:STATUS.critical, opacity:.06}));
  for (const g of [0, 1, 2].filter(g => g <= hi)){
    svg.appendChild(el('line', {x1:X(g), x2:X(g), y1:padT - 4,
                                y2:padT + rows.length * rowH,
                                stroke: g === 1 ? STATUS.critical : INK.grid,
                                'stroke-width': g === 1 ? 1.5 : 1,
                                'stroke-dasharray': g === 1 ? '4 3' : '',
                                opacity: g === 1 ? .85 : .5}));
    svg.appendChild(text(X(g), h - 8, g === 1 ? '1.0× — random' : `${g}×`,
                         {anchor:'middle', size:9,
                          fill: g === 1 ? STATUS.critical : INK.secondary}));
  }

  rows.forEach((r, i) => {
    const y = padT + i * rowH;
    const ours = /^OURS/.test(r.rule);
    const bad = r.enrichment < 1;
    const label = r.rule.replace(/^OURS:\s*/, '');
    const bw = Math.max(1, X(r.enrichment) - padL);
    const g = el('g', {style:'cursor:pointer'});
    g.appendChild(el('rect', {x:0, y:y - 2, width:w, height:rowH - 2,
                              fill: ours ? 'rgba(168,199,250,.07)' : 'transparent'}));
    g.appendChild(text(padL - 8, y + 12, label,
                       {anchor:'end', size:10.5,
                        fill: ours ? INK.primary : bad ? STATUS.critical : INK.secondary,
                        weight: ours ? 600 : 400}));
    g.appendChild(el('rect', {x:padL, y:y + 3, width:bw, height:11, rx:2,
                              fill: bad ? STATUS.critical : ours ? '#a8c7fa' : '#2a78d6',
                              opacity: bad ? .85 : ours ? 1 : .7}));
    g.appendChild(text(X(r.enrichment) + 5, y + 12, `${r.enrichment.toFixed(2)}×`,
                       {size:10, mono:true,
                        fill: bad ? STATUS.critical : INK.primary, weight:600}));
    g.addEventListener('mousemove', ev => tip(ev,
      `<b>${r.enrichment.toFixed(2)}× enrichment</b>${label}`
      + `<i>keeps ${r.kept.toLocaleString()} of 1,947 and finds ${r.found} of 53 `
      + `responders — ${(r.recall*100).toFixed(0)}% recall at `
      + `${(r.precision*100).toFixed(1)}% precision`
      + `${bad ? '. WORSE THAN RANDOM.' : ''}</i>`));
    g.addEventListener('mouseleave', () => tip(null));
    svg.appendChild(g);
  });
  container.appendChild(svg);
}
