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
                 critical:'#d03b3b', muted:'#6e7681' };
const INK = { primary:'#e6edf3', secondary:'#8b949e', grid:'#30363d', surface:'#161b22' };

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
    tip(ev, `${name(i)} ${idx(i)} ↔ ${name(j)} ${idx(j)}`
          + `<b>${pae[i][j].toFixed(1)} Å</b> predicted aligned error`);
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
  for (const g of [50, 70, 90, 100]){
    svg.appendChild(el('line', {x1:padL, x2:w - 6, y1:y(g), y2:y(g),
                                stroke:INK.grid, 'stroke-width':1}));
    svg.appendChild(text(padL - 5, y(g) + 3, g, {anchor:'end', size:9}));
  }
  let d = `M ${x(0)} ${y(v[0])}`;
  for (let i = 1; i < n; i++) d += ` L ${x(i)} ${y(v[i])}`;
  svg.appendChild(el('path', {d:`${d} L ${x(n-1)} ${y(50)} L ${x(0)} ${y(50)} Z`,
                              fill:'#3987e5', opacity:.16}));
  svg.appendChild(el('path', {d, fill:'none', stroke:'#3987e5', 'stroke-width':2,
                              'stroke-linejoin':'round'}));

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
    tip(ev, `${c ? c.label : ''} residue ${c ? i - c.start + 1 : i}`
          + `<b>pLDDT ${v[i].toFixed(1)}</b>`);
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
  svg.appendChild(text(padL + pw, Y(10) - 4, 'DAI ≥ 10 (Rech 2018)', {anchor:'end', size:9}));

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
    const c = el('circle', {cx:X(p.affinity_nm), cy:Y(p.dai),
      r: investigate ? 5 : 3, fill:colour(p.tier),
      opacity: investigate ? .95 : .5,
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
