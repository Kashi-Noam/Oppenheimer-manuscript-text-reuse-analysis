/* synoptic.js: split a comparison of N witnesses into synoptic rows.
 *
 * Used by the explorer ("בדיקת השוואות" → "תצוגה סינופטית בשורות") and by tests/synoptic_test.js.
 * Pure functions, no DOM access; works as a browser global (window.Synoptic) and as a CommonJS module.
 *
 * How it works
 *  1. Alignment. The pivot witness (Oppenheim) gives the first sequence of columns. Each other witness is
 *     aligned into it by dynamic programming (an order-preserving alignment). ACT's word alignment to the pivot
 *     (`anchors`) scores highest. Next come word similarities with any witness already in the column: identical,
 *     same consonant skeleton without ו/י, abbreviation as prefix (אמ/אמר, שנ/שנאמר), or a small edit distance.
 *     Normalisation is used only for this computation; the displayed text is never changed.
 *  2. Weak islands. Groups of at most two matched columns with no ACT anchor are dropped, so short common
 *     words do not glue unrelated passages together.
 *  3. Rows. Consecutive columns with the same set of witnesses form a run. Short runs are merged into a
 *     neighbouring run: under 4 words if only one witness has text, under 2 if several do. Small variants,
 *     additions and omissions therefore stay inside the shared row, while longer additions get a row of their own.
 *  4. Long rows are split at a likely boundary, with markers such as דבר אחר / דא / אמר ר' / מפני מה / על שם /
 *     שנאמר / דכתיב, keeping both parts readable.
 *  5. Order changes. Each witness keeps its own order. Rows that have no witness in common but contain similar
 *     text are linked as a probable transposition ("↕"). The tool shows the link and does not re-align them.
 *  check() verifies, for every witness, that the rows hold every word of its window exactly once and in order.
 */
(function (root) {
  'use strict';

  const OPT = { minSingle: 4, minShared: 2, minPartial: 5, maxRow: 22, strongCut: 2.5, strongSide: 6, strongRow: 12, isolate: 4, minSplit: 5, moveSim: 0.6, moveMin: 4 };

  // ---------- word normalisation and similarity (computation only) ----------
  const FIN = { 'ך': 'כ', 'ם': 'מ', 'ן': 'נ', 'ף': 'פ', 'ץ': 'צ' };
  const norm = w => String(w == null ? '' : w).replace(/[^א-ת]/g, '').replace(/[ךםןףץ]/g, c => FIN[c]);
  const skel = n => (n.length > 2 ? n[0] + n.slice(1).replace(/[וי]/g, '') : n);
  const info = t => { const n = norm(t); return { n, s: skel(n) }; };

  function lev(a, b) {
    if (a === b) return 0;
    const m = a.length, n = b.length;
    if (!m) return n; if (!n) return m;
    let p = new Array(n + 1), q = new Array(n + 1);
    for (let j = 0; j <= n; j++) p[j] = j;
    for (let i = 1; i <= m; i++) {
      q[0] = i;
      for (let j = 1; j <= n; j++) q[j] = Math.min(p[j] + 1, q[j - 1] + 1, p[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      const t = p; p = q; q = t;
    }
    return p[n];
  }

  function sim(x, y) {
    if (!x.n || !y.n) return 0;
    if (x.n === y.n) return 1;
    if (x.s === y.s) return 0.9;
    const a = x.n, b = y.n;
    if (Math.min(a.length, b.length) >= 2 && (a.startsWith(b) || b.startsWith(a))) return 0.75;
    const L = Math.max(x.s.length, y.s.length);
    if (L < 4) return 0;
    const r = 1 - lev(x.s, y.s) / L;
    return r >= 0.7 ? r * 0.9 : 0;
  }

  function simScore(x, y) {
    const s = sim(x, y);
    if (!s) return 0;
    let sc = s >= 0.9 ? 2 : s >= 0.75 ? 1.4 : 0.9;
    if (Math.min(x.n.length, y.n.length) <= 2) sc *= 0.5; // particles and abbreviations weigh less
    return sc;
  }

  // ---------- 1. progressive alignment ----------
  // cols: [{t:[tokenIndex|null per witness], anc:bool}], each witness's indices strictly increasing along cols.
  function alignInto(cols, W, w, pivot) {
    const B = W[w].idx, anchors = W[w].anchors || {};
    const m = cols.length, n = B.length, N1 = n + 1;
    const dp = new Float64Array((m + 1) * N1), bk = new Uint8Array((m + 1) * N1); // 1 diag, 2 up (col only), 3 left (B only)
    const scoreAt = (c, k) => {
      const col = cols[c], j = B[k];
      const pi = col.t[pivot];
      if (pi != null && anchors[pi] && anchors[pi][0] === j) return [3, true];
      let best = 0;
      for (let v = 0; v < col.t.length; v++) {
        const iv = col.t[v];
        if (iv == null || v === w) continue;
        const sc = simScore(W[v].info[iv], W[w].info[j]);
        if (sc > best) best = sc;
      }
      return [best, false];
    };
    const anc = new Uint8Array((m + 1) * N1);
    for (let a = 0; a <= m; a++) {
      for (let b = 0; b <= n; b++) {
        const id = a * N1 + b;
        if (!a && !b) continue;
        let best = -1, mv = 0;
        if (b > 0) { const v = dp[id - 1]; if (v > best) { best = v; mv = 3; } }          // B-only, preferred on ties
        if (a > 0) { const v = dp[id - N1]; if (v > best) { best = v; mv = 2; } }
        if (a > 0 && b > 0) {
          const [sc, an] = scoreAt(a - 1, b - 1);
          if (sc > 0) { const v = dp[id - N1 - 1] + sc; if (v > best) { best = v; mv = 1; anc[id] = an ? 1 : 0; } }
        }
        dp[id] = best; bk[id] = mv;
      }
    }
    const out = [];
    let a = m, b = n;
    while (a > 0 || b > 0) {
      const id = a * N1 + b, mv = bk[id];
      if (mv === 1) { const col = { t: cols[a - 1].t.slice(), anc: cols[a - 1].anc || !!anc[id] }; col.t[w] = B[b - 1]; out.push(col); a--; b--; }
      else if (mv === 2) { out.push(cols[a - 1]); a--; }
      else { const t = W.map(() => null); t[w] = B[b - 1]; out.push({ t, anc: false }); b--; }
    }
    return out.reverse();
  }

  const present = col => col.t.reduce((k, x) => k + (x != null ? 1 : 0), 0);

  // ---------- 2. drop weak islands of matches ----------
  // An island is isolated when at least OPT.isolate unmatched columns (or the window edge) lie on each side.
  function isolated(cols, i, last) {
    let l = 0, r = 0;
    for (let c = i - 1; c >= 0 && present(cols[c]) < 2; c--) l++;
    for (let c = last + 1; c < cols.length && present(cols[c]) < 2; c++) r++;
    const atL = i - l === 0, atR = last + 1 + r === cols.length;
    return (l >= OPT.isolate || atL) && (r >= OPT.isolate || atR);
  }
  function demote(cols) {
    const out = [];
    let i = 0;
    while (i < cols.length) {
      if (present(cols[i]) < 2) { out.push(cols[i]); i++; continue; }
      // a group of match columns, allowing gaps shorter than OPT.isolate columns inside
      let j = i, last = i, nm = 0;
      while (j < cols.length) {
        if (present(cols[j]) >= 2) { nm++; last = j; j++; continue; }
        let g = j; while (g < cols.length && present(cols[g]) < 2) g++;
        if (g < cols.length && g - j < OPT.isolate) j = g; else break;
      }
      const grp = cols.slice(i, last + 1);
      if (nm <= 3 && isolated(cols, i, last)) {
        grp.forEach(col => col.t.forEach((x, v) => { if (x != null) { const t = col.t.map(() => null); t[v] = x; out.push({ t, anc: false }); } }));
      } else grp.forEach(c => out.push(c));
      i = last + 1;
    }
    return out;
  }

  // Inside each stretch without matches, put each witness's words together (witness order, own word order kept),
  // so that dropped islands and DP tie-breaking do not leave the witnesses interleaved.
  function regroup(cols) {
    const out = [];
    let i = 0;
    while (i < cols.length) {
      if (present(cols[i]) >= 2) { out.push(cols[i]); i++; continue; }
      let j = i; while (j < cols.length && present(cols[j]) < 2) j++;
      const reg = cols.slice(i, j), wit = col => col.t.findIndex(x => x != null);
      reg.map((c, k) => [wit(c), k, c]).sort((a, b) => a[0] - b[0] || a[1] - b[1]).forEach(x => out.push(x[2]));
      i = j;
    }
    return out;
  }

  // ---------- 3. runs and rows ----------
  const maskOf = col => col.t.reduce((m, x, v) => (x != null ? m | (1 << v) : m), 0);
  const bits = m => { let k = 0; while (m) { k += m & 1; m >>= 1; } return k; };
  function weight(cols, a, b, nW) {
    let best = 0;
    for (let v = 0; v < nW; v++) { let k = 0; for (let c = a; c < b; c++) { const x = cols[c].t[v]; if (x != null) k += cols.W[v].info[x].n.length > 1 ? 1 : 0.34; } if (k > best) best = k; }
    return best;
  }

  function segment(cols, nW) {
    let runs = [];
    cols.forEach((col, c) => {
      const m = maskOf(col), r = runs[runs.length - 1];
      if (r && r.mask === m) r.b = c + 1; else runs.push({ a: c, b: c + 1, mask: m });
    });
    const sup = (x, r) => x && (x.mask & r.mask) === r.mask && x.mask !== r.mask;
    // too small: a lone witness under minSingle words; a shared run under minShared; or a shared run under minPartial
    // words that lacks a witness its neighbour has (it reads as a variant inside that neighbour's row)
    const tooSmall = (r, k) => {
      const w = weight(cols, r.a, r.b, nW);
      if (bits(r.mask) === 1) return w < OPT.minSingle;
      return w < OPT.minShared || (w < OPT.minPartial && (sup(runs[k - 1], r) || sup(runs[k + 1], r)));
    };
    for (let guard = 0; guard < 10000 && runs.length > 1; guard++) {
      let k = -1, kw = Infinity;
      runs.forEach((r, i) => { if (tooSmall(r, i)) { const w = weight(cols, r.a, r.b, nW); if (w < kw) { kw = w; k = i; } } });
      if (k < 0) break;
      const r = runs[k], L = runs[k - 1], R = runs[k + 1];
      let into;
      if (!L) into = k + 1; else if (!R) into = k - 1;
      else {
        const cover = x => (x.mask & r.mask) === r.mask;
        if (cover(L) !== cover(R)) into = cover(L) ? k - 1 : k + 1;
        else {
          // a short run that opens with a strong marker (דבר אחר, מפני מה …) starts the next row; otherwise it ends the previous one
          let mk = 0; cols[r.a].t.forEach((x, v) => { if (x != null) mk = Math.max(mk, markerAt(cols.W, v, x)); });
          into = mk >= 3 ? k + 1 : k - 1;
        }
      }
      const t = runs[into];
      const merged = { a: Math.min(t.a, r.a), b: Math.max(t.b, r.b), mask: t.mask | r.mask };
      runs.splice(Math.min(k, into), 2, merged);
      // coalesce equal neighbours
      runs = runs.reduce((acc, x) => { const p = acc[acc.length - 1]; if (p && p.mask === x.mask) p.b = x.b; else acc.push(x); return acc; }, []);
    }
    return runs;
  }

  // ---------- 4. split long rows at likely boundaries ----------
  const QUOTE = new Set(['שנאמר', 'שנ', 'שנאמ', 'שנא', 'דכתיב', 'דכת', 'דכתי', 'דכתוב', 'כתיב', 'כת', 'כתוב', 'הדא', 'הדה', 'וכתיב']);
  const SAY = new Set(['אמר', 'אמ', 'אר', 'ואמר', 'ואמ']);
  const RABBI = new Set(['ר', 'רבי', 'רב', 'רבנ', 'רבננ']);
  // Word pairs that open a repeated formula in a witness's window (anaphora: נתת שלוה …, מפני מה ברא …):
  // they occur three or more times, and the word before them varies (so they are not the middle of a formula).
  // pair key: first three consonants of each word without ו/י (נתת שלוה = נתתה שלווה)
  const pk = (w, i) => (w.info[i] ? w.info[i].s.slice(0, 3) : '') + ' ' + (w.info[i + 1] ? w.info[i + 1].s.slice(0, 3) : '');
  function anaphora(W) {
    W.forEach(w => {
      const cnt = new Map();
      for (let k = 0; k + 1 < w.idx.length; k++) {
        const b = pk(w, w.idx[k]), pv = k ? w.info[w.idx[k - 1]].s.slice(0, 3) : '^';
        const e = cnt.get(b) || { n: 0, prev: new Set() }; e.n++; e.prev.add(pv); cnt.set(b, e);
      }
      let rep = new Set([...cnt].filter(([b, e]) => e.n >= 3 && e.prev.size / e.n >= 0.75 && b.split(' ').every(x => x.length > 1)).map(([b]) => b));
      const pairAt = k => pk(w, w.idx[k]);
      const inner = new Set();
      rep.forEach(b => {
        let occ = 0, after = 0;
        for (let k = 0; k + 1 < w.idx.length; k++) {
          if (pairAt(k) !== b) continue;
          occ++;
          for (let d = 1; d <= 5 && k - d >= 0; d++) { const q = pairAt(k - d); if (q !== b && rep.has(q)) { after++; break; } }
        }
        if (after * 2 >= occ) inner.add(b);
      });
      w.rep = new Set([...rep].filter(b => !inner.has(b)));
    });
  }
  function markerAt(W, v, i) {
    const tk = W[v].info, n = tk[i] ? tk[i].n : '', nx = tk[i + 1] ? tk[i + 1].n : '', pv = i > 0 && tk[i - 1] ? tk[i - 1].n : '';
    if ((n === 'דבר' && nx === 'אחר') || n === 'דא') return 3;
    if (n === 'מפני' && nx === 'מה') return 3;
    if (n === 'תנו' && RABBI.has(nx)) return 3;
    if (n === 'על' && nx === 'שמ') return 2.5;
    if (n === 'תניא' || n === 'מעשה' || n === 'משל' || n === 'כיצד') return 2;
    if (n === 'הא' && (nx === 'למדת' || nx === 'למדנו')) return 2;
    if (n === 'ואומר' || n === 'ואומ') return 1.5;
    if ((SAY.has(n) || n === 'א') && RABBI.has(nx)) return 3;
    if (SAY.has(n)) return 2;
    if (RABBI.has(n) && !SAY.has(pv) && pv !== 'א' && pv !== 'בשמ' && pv !== 'בר' && pv !== 'בנ') return 1.5;
    if (W[v].rep && W[v].rep.has(pk(W[v], i))) {
      // not when the same pair opened just before (a doubled verse: יספת לגוי יי יספת לגוי)
      for (let d = 1; d <= 4 && i - d >= 0; d++) if (pk(W[v], i - d) === pk(W[v], i)) return 0;
      return 2.5;
    }
    if (QUOTE.has(n)) return 1;
    return 0;
  }

  function splitLong(runs, cols, W) {
    const nW = W.length, out = [];
    const rec = r => {
      const w = weight(cols, r.a, r.b, nW);
      if (w < OPT.strongRow) { out.push(r); return; }
      const long = w > OPT.maxRow;
      let best = null;
      for (let c = r.a + 1; c < r.b; c++) {
        const lw = weight(cols, r.a, c, nW), rw = weight(cols, c, r.b, nW);
        if (Math.min(lw, rw) < Math.min(OPT.minSplit, 4)) continue;
        if (long && (lw < OPT.minSplit || rw < OPT.minSplit)) continue;
        let mk = 0;
        cols[c].t.forEach((x, v) => { if (x != null) mk = Math.max(mk, markerAt(W, v, x)); });
        // cut only before a matched column, or before a strong marker that opens a gap right after a match
        const single = bits(r.mask) === 1;
        if (!(single ? mk >= 1 : present(cols[c]) >= 2 || (mk >= 2 && present(cols[c - 1]) >= 2))) continue;
        const clean = present(cols[c]) >= 2 && present(cols[c - 1]) >= 2 ? 0.4 : 0;
        const side = mk >= 3 ? 4 : OPT.strongSide;
        if (!long && (mk < OPT.strongCut || lw < side || rw < side)) continue;
        const sc = mk + clean - (mk ? 0 : 1) - 1.5 * Math.abs(lw - rw) / (lw + rw);
        if (!best || sc > best.sc) best = { c, sc };
      }
      if (!best || (best.sc < -0.6 && w <= OPT.maxRow * 1.5)) { out.push(r); return; }
      rec({ a: r.a, b: best.c, mask: r.mask });
      rec({ a: best.c, b: r.b, mask: r.mask });
    };
    runs.forEach(rec);
    return out;
  }

  // ---------- 5. probable transpositions ----------
  function seqSim(W, v, xs, w, ys) {
    if (!xs.length || !ys.length) return 0;
    const m = xs.length, n = ys.length, L = Array.from({ length: m + 1 }, () => new Uint16Array(n + 1));
    for (let i = 1; i <= m; i++) for (let j = 1; j <= n; j++)
      L[i][j] = sim(W[v].info[xs[i - 1]], W[w].info[ys[j - 1]]) >= 0.9 ? L[i - 1][j - 1] + 1 : Math.max(L[i - 1][j], L[i][j - 1]);
    return L[m][n] / Math.min(m, n);
  }

  // ---------- build ----------
  /** spec: {pivot:0, witnesses:[{key,name,ref,tokens:[...], lo, hi, anchors?:{pivotIdx:[idx,exact]}, cls?:fn(idx)->string}]} */
  function build(spec, opt) {
    Object.assign(OPT, opt || {});
    const pivot = spec.pivot || 0;
    const W = spec.witnesses.map(w => {
      const idx = [];
      for (let i = Math.max(0, w.lo); i < Math.min(w.tokens.length, w.hi); i++) idx.push(i);
      return Object.assign({}, w, { idx, info: w.tokens.map(info) });
    });
    let cols = W[pivot].idx.map(i => ({ t: W.map((_, v) => (v === pivot ? i : null)), anc: false }));
    W.forEach((_, w) => { if (w !== pivot) cols = alignInto(cols, W, w, pivot); });
    cols = regroup(demote(cols));
    cols.W = W;
    anaphora(W);
    const runs = splitLong(segment(cols, W.length), cols, W);
    const firstShared = runs.findIndex(r => bits(r.mask) > 1);
    let lastShared = -1; runs.forEach((r, i) => { if (bits(r.mask) > 1) lastShared = i; });
    const rows = runs.map((r, i) => {
      const cells = W.map((_, v) => { const a = []; for (let c = r.a; c < r.b; c++) if (cols[c].t[v] != null) a.push(cols[c].t[v]); return a; });
      const mask = cells.reduce((m, a, v) => (a.length ? m | (1 << v) : m), 0);
      let matched = 0; for (let c = r.a; c < r.b; c++) if (present(cols[c]) >= 2) matched++;
      const wgt = Math.max(...cells.map(a => a.length));
      const kind = bits(mask) === 1 && (firstShared < 0 || i < firstShared) ? 'before' : bits(mask) === 1 && i > lastShared ? 'after' : '';
      return { n: i + 1, cells, mask, matched, weight: wgt, kind, uncertain: bits(mask) > 1 && matched / wgt < 0.3, moved: [] };
    });
    // link rows that share no witness but hold similar text (probable change of order)
    for (let i = 0; i < rows.length; i++) for (let j = i + 1; j < rows.length; j++) {
      const A = rows[i], Bq = rows[j];
      if (A.mask & Bq.mask) continue;
      let s = 0;
      A.cells.forEach((xs, v) => {
        if (xs.length < OPT.moveMin) return;
        Bq.cells.forEach((ys, w) => {
          if (ys.length < OPT.moveMin || Math.min(xs.length, ys.length) / Math.max(xs.length, ys.length) < 0.3) return;
          s = Math.max(s, seqSim(W, v, xs, w, ys));
        });
      });
      if (s >= OPT.moveSim) { A.moved.push(Bq.n); Bq.moved.push(A.n); }
    }
    return { witnesses: W.map(w => ({ key: w.key, name: w.name, ref: w.ref, role: w.role, roleWhy: w.roleWhy, lo: w.idx.length ? w.idx[0] : w.lo, hi: w.idx.length ? w.idx[w.idx.length - 1] + 1 : w.lo, total: w.tokens.length, idx: w.idx })), rows, spec: { witnesses: W } };
  }

  // ---------- integrity check ----------
  function check(res) {
    const per = res.witnesses.map((w, v) => {
      const seq = res.rows.flatMap(r => r.cells[v]);
      const exp = new Set(w.idx), seen = new Set(), dup = [];
      seq.forEach(x => { if (seen.has(x)) dup.push(x); seen.add(x); });
      const lost = w.idx.filter(x => !seen.has(x)), added = seq.filter(x => !exp.has(x));
      let ordered = true; for (let k = 1; k < seq.length; k++) if (seq[k] <= seq[k - 1]) { ordered = false; break; }
      return { key: w.key, name: w.name, words: w.idx.length, got: seq.length, lost: lost.length, added: added.length, dup: dup.length, ordered };
    });
    return { ok: per.every(p => !p.lost && !p.added && !p.dup && p.ordered), per };
  }

  // ---------- labels and output ----------
  function rowLabel(res, r, short) {
    const names = res.witnesses.map(w => short ? short(w) : w.name);
    const has = names.filter((_, v) => r.mask & (1 << v));
    let s = has.length === res.witnesses.length ? 'בכל העדים' : has.length === 1 ? 'רק ב' + has[0] : has.join(' + ');
    if (r.kind === 'before') s += ' · לפני הקטע המקביל';
    if (r.kind === 'after') s += ' · אחרי הקטע המקביל';
    return s;
  }
  function rowNotes(r) {
    const a = [];
    if (r.moved.length) a.push('↕ שינוי סדר? ראו שורה ' + r.moved.join(', '));
    if (r.uncertain) a.push('יישור לא ודאי');
    return a;
  }
  const escH = s => String(s == null ? '' : s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  function cellText(res, r, v, withEll) {
    const w = res.witnesses[v], xs = r.cells[v], toks = res.spec.witnesses[v].tokens;
    if (!xs.length) return '';
    let s = xs.map(i => toks[i]).join(' ');
    if (withEll && xs[0] === w.lo && w.lo > 0) s = '… ' + s;
    if (withEll && xs[xs.length - 1] === w.hi - 1 && w.hi < w.total) s += ' …';
    return s;
  }

  function tableHTML(res, opt) {
    opt = opt || {};
    const esc = opt.esc || escH, W = res.spec.witnesses;
    const head = res.witnesses.map(w => `<th>${esc(w.name)}${w.role ? ` <span class="syn-role" title="${esc(w.roleWhy || '')}">${esc(w.role)}</span>` : ''}${w.ref ? `<span class="syn-ref" dir="ltr">${esc(w.ref)}</span>` : ''}</th>`).join('');
    const body = res.rows.map(r => {
      const tds = r.cells.map((xs, v) => {
        if (!xs.length) return '<td class="syn-empty" title="אין רצף מקביל בחלון המוצג"></td>';
        const w = res.witnesses[v], cls = W[v].cls || (() => '');
        let h = xs[0] === w.lo && w.lo > 0 ? '<span class="ell">… </span>' : '';
        h += xs.map(i => { const c = cls(i); return c ? `<span class="${c}">${esc(W[v].tokens[i])}</span>` : esc(W[v].tokens[i]); }).join(' ');
        if (xs[xs.length - 1] === w.hi - 1 && w.hi < w.total) h += '<span class="ell"> …</span>';
        return `<td title="מילים ${xs[0] + 1}–${xs[xs.length - 1] + 1}">${h}</td>`;
      }).join('');
      const cl = [r.kind ? 'syn-ctx' : '', r.moved.length ? 'syn-moved' : '', r.uncertain ? 'syn-unc' : ''].filter(Boolean).join(' ');
      const nh = (r.moved.length ? [`↕ שינוי סדר? ראו שורה ${r.moved.map(n => `<a class="syn-jump" href="#syn-r${n}" data-r="${n}">${n}</a>`).join(', ')}`] : []).concat(r.uncertain ? ['יישור לא ודאי'] : []);
      return `<tr id="syn-r${r.n}"${cl ? ` class="${cl}"` : ''}><td class="syn-n"><b>${r.n}</b><span class="syn-k">${esc(rowLabel(res, r, opt.short))}</span>${nh.map(x => `<span class="syn-note">${x}</span>`).join('')}</td>${tds}</tr>`;
    }).join('');
    return `<div class="syn-scroll"><table class="syn"><colgroup><col class="syn-cn">${res.witnesses.map(() => '<col>').join('')}</colgroup><thead><tr><th class="syn-n">#</th>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
  }

  function checkText(rep) {
    if (rep.ok) return 'בדיקת שלמות: עברה. ' + rep.per.map(p => `${p.name}: ${p.words} מילים`).join(' · ') + '. אף מילה לא אבדה, נוספה או הוכפלה, וסדר המילים בכל עד נשמר.';
    return 'בדיקת שלמות: נכשלה. ' + rep.per.map(p => `${p.name}: חסרות ${p.lost}, נוספו ${p.added}, כפולות ${p.dup}${p.ordered ? '' : ', סדר שונה'}`).join(' · ');
  }

  function toTSV(res, opt) {
    const clean = s => String(s).replace(/[\t\r\n]+/g, ' ');
    const head = ['#', 'סוג'].concat(res.witnesses.map(w => clean(w.name + (w.ref ? ' (' + w.ref + ')' : ''))), ['הערות']);
    const lines = [head.join('\t')];
    res.rows.forEach(r => lines.push([r.n, clean(rowLabel(res, r, opt && opt.short))].concat(r.cells.map((_, v) => clean(cellText(res, r, v, true))), [clean(rowNotes(r).join('; '))]).join('\t')));
    return '﻿' + lines.join('\r\n') + '\r\n';
  }

  const EXPORT_CSS = `:root{color-scheme:light;--bg:#f7f6f2;--surface:#fff;--surface-2:#f1efea;--line:#ddd9d0;--ink:#272522;--ink-3:#817b71;--via:#2f6fb0;--via-soft:#dbe8f6;--dir:#b5651d;--dir-soft:#f6e3cf;--om:#d9d4c8;--accent:#2b5d8a}
*{box-sizing:border-box}html{direction:rtl}body{font:15px/1.75 "Noto Sans Hebrew","Segoe UI",Arial,sans-serif;color:var(--ink);background:var(--bg);margin:0 auto;max-width:1600px;padding:24px 16px 60px}
h1{font-size:22px;margin:0 0 4px}p{color:var(--ink-3);font-size:13px;margin:0 0 10px;max-width:1100px}
.legend{display:flex;flex-wrap:wrap;gap:12px;font-size:12px;color:var(--ink-3);margin:8px 0 12px}.legend i{display:inline-block;width:18px;height:10px;margin-inline-end:4px;vertical-align:middle}`;
  const TABLE_CSS = `.syn-scroll{overflow:auto;max-height:75vh;border:1px solid var(--line);border-radius:9px;background:var(--surface)}
table.syn{border-collapse:separate;border-spacing:0;table-layout:fixed;width:100%;min-width:720px}
.syn col.syn-cn{width:96px}
.syn th{position:sticky;top:0;z-index:2;background:var(--surface-2);text-align:right;padding:9px 11px;border-bottom:2px solid var(--line);font-size:14px}
.syn .syn-ref{display:block;font-weight:400;font-size:11px;color:var(--ink-3)}
.syn .syn-role{font-weight:400;font-size:11px;border:1px solid var(--line);border-radius:999px;padding:0 6px;color:var(--ink-3)}
.syn .a-x{border-bottom:2px solid var(--accent)}
.syn td{vertical-align:top;padding:9px 11px;border-bottom:1px solid var(--line);border-inline-start:1px solid var(--line);line-height:2;font-size:15px;overflow-wrap:anywhere}
.syn td.syn-n{border-inline-start:0;font-size:12px;line-height:1.4;color:var(--ink-3)}
.syn td.syn-n b{display:block;color:var(--ink);font-size:13px}
.syn .syn-k{display:block;margin-top:2px}.syn .syn-note{display:block;margin-top:4px;color:var(--accent)}
.syn td.syn-empty{background:var(--surface-2)}
.syn tr.syn-ctx td:not(.syn-empty){color:var(--ink-3)}
.syn tr.syn-moved td.syn-n{box-shadow:inset -3px 0 0 var(--accent)}
.syn tr:target td,.syn tr.syn-flash td{background:var(--via-soft)}
.syn tbody tr{scroll-margin-top:56px}
.syn a.syn-jump{color:inherit;font-weight:700}
.syn span{border-radius:3px}.syn .ell{color:var(--ink-3)}
.syn .a-o{border-bottom:2px solid var(--dir)}.syn .a-n{text-decoration:underline 2px var(--via);text-underline-offset:6px}
.syn .e-o{background:var(--dir-soft)}.syn .e-n{background:var(--via-soft)}.syn .om{background:var(--om);text-decoration:line-through;text-decoration-color:var(--ink-3)}
@media print{.syn-scroll{overflow:visible;max-height:none;border:0}.syn th{position:static}.syn tr{break-inside:avoid}.syn td{font-size:12px;line-height:1.6;padding:6px}}
@media (max-width:760px){.syn td{font-size:13px;padding:6px}}`;

  function standaloneHTML(res, opt) {
    opt = opt || {};
    const esc = escH, rep = check(res);
    const legend = opt.legend || '';
    return `<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(opt.title || 'השוואה סינופטית')}</title><style>${EXPORT_CSS}\n${TABLE_CSS}</style></head><body>
<h1>${esc(opt.title || 'השוואה סינופטית')}</h1>
<p>${esc(opt.subtitle || '')}</p>
<p>החלוקה לשורות הופקה אוטומטית מנתוני היישור של הסייר. הנוסח לא שונה: שיבושי HTR וקיצורים נשמרו. תא ריק פירושו שאין רצף מקביל בחלון המוצג, ולא בהכרח היעדר מן המסורת. "…" מסמן שהעד ממשיך מעבר לחלון. "↕" מסמן שורות שאין להן עד משותף אבל הטקסט בהן דומה: ייתכן שינוי סדר.</p>
<p>${esc(checkText(rep))}</p>
${legend ? `<div class="legend">${legend}</div>` : ''}
${tableHTML(res, opt)}
<p style="margin-top:12px">${esc(opt.footer || '')}</p></body></html>`;
  }

  // all strong witnesses of one text unit (Moshe, fdcf7a9d: "להרחיב את הסינופסיס מקרה שיש יותר ממקבילה חזקה אחת"),
  // ordered by dating as in the matryoshka path view (D8). Marks: a-x = aligned (Oppenheim: aligned to at least one witness).
  function fromUnit(ctx, uid, roleOf) {
    const u = ctx.U[uid], T = ctx.T;
    const toks = (T.p[u.pid] || '').split(' ');
    const merged = k => {
      const w = u.wit.find(x => x.k === k); let src = [], am = {}, off = 0;
      w.ids.forEach(id => { const t = T.c[id]; t.al.forEach(([a, j, x]) => { if (am[a] === undefined || (x && !am[a][1])) am[a] = [j + off, x]; }); const s2 = t.src.split(' '); src = src.concat(s2); off += s2.length; });
      return { src, am, ids: w.ids };
    };
    const yr = k => (ctx.W[k] && ctx.W[k].date_from != null ? ctx.W[k].date_from : 9999);
    const wits = u.wit.map(x => x.k).sort((a, b) => yr(a) - yr(b));
    const Ms = wits.map(merged);
    const anyAl = new Set(); Ms.forEach(M => Object.keys(M.am).forEach(a => anyAl.add(+a)));
    const lo = Math.max(0, u.lo - 12), hi = Math.min(toks.length, u.hi + 13);
    const win = M => { const js = Object.values(M.am).map(x => x[0]); return js.length ? [Math.max(0, Math.min(...js) - 15), Math.min(M.src.length, Math.max(...js) + 16)] : [0, Math.min(M.src.length, 60)]; };
    const name = k => (ctx.W[k] && ctx.W[k].name_he) || k, ref = M => M.ids.map(id => (ctx.C[id] || {}).ref).join(' + ');
    return { pivot: 0, witnesses: [{ key: 'Oppenheim_128', name: 'אופנהיימר 128', ref: 'HTR', tokens: toks, lo, hi, cls: a => (anyAl.has(a) ? 'a-x' : '') }]
      .concat(wits.map((k, n) => {
        const M = Ms[n], aj = new Set(Object.values(M.am).map(x => x[0])), [a0, a1] = win(M), r = roleOf ? roleOf(k) : null;
        return { key: k, name: name(k), ref: ref(M), tokens: M.src, lo: a0, hi: a1, anchors: M.am, cls: j => (aj.has(j) ? 'a-x' : ''), role: r && r.he, roleWhy: r && r.why };
      })) };
  }

  // ---------- the explorer's comparison → spec (same windows and marks as the running view in showComp) ----------
  function fromComparison(ctx, i, roleOf) {
    const c = ctx.D.comps[i], u = ctx.U[c.uid], T = ctx.T;
    const toks = (T.p[u.pid] || '').split(' ');
    const merged = k => {
      const w = u.wit.find(x => x.k === k); let src = [], am = {}, off = 0;
      w.ids.forEach(id => { const t = T.c[id]; t.al.forEach(([a, j, x]) => { if (am[a] === undefined || (x && !am[a][1])) am[a] = [j + off, x]; }); const s = t.src.split(' '); src = src.concat(s); off += s.length; });
      return { src, am, ids: w.ids };
    };
    const O = merged(c.o), N = merged(c.n);
    const eo = new Set((c.b.opp_O_notM || []).flat()), en = new Set((c.b.opp_M_notO || []).flat()), om = new Set((c.b.shared_omission || []).flat());
    const lo = Math.max(0, u.lo - 12), hi = Math.min(toks.length, u.hi + 13);
    const win = M => { const js = Object.values(M.am).map(x => x[0]); return js.length ? [Math.max(0, Math.min(...js) - 15), Math.min(M.src.length, Math.max(...js) + 16)] : [0, Math.min(M.src.length, 60)]; };
    const oj = new Set(Object.values(O.am).map(x => x[0])), nj = new Set(Object.values(N.am).map(x => x[0]));
    const [o0, o1] = win(O), [n0, n1] = win(N);
    const name = k => (ctx.W[k] && ctx.W[k].name_he) || k, ref = M => M.ids.map(id => (ctx.C[id] || {}).ref).join(' + ');
    const rl = k => { const r = roleOf ? roleOf(k) : null; return r ? { role: r.he, roleWhy: r.why } : {}; };
    return { pivot: 0, witnesses: [
      { key: 'Oppenheim_128', name: 'אופנהיימר 128', ref: 'HTR', tokens: toks, lo, hi,
        cls: a => [O.am[a] ? 'a-o' : '', N.am[a] ? 'a-n' : '', eo.has(a) ? 'e-o' : '', en.has(a) ? 'e-n' : ''].filter(Boolean).join(' ') },
      Object.assign({ key: c.o, name: name(c.o), ref: ref(O), tokens: O.src, lo: o0, hi: o1, anchors: O.am,
        cls: j => [oj.has(j) ? 'a-o' : '', om.has(j) ? 'om' : ''].filter(Boolean).join(' ') }, rl(c.o)),
      Object.assign({ key: c.n, name: name(c.n), ref: ref(N), tokens: N.src, lo: n0, hi: n1, anchors: N.am, cls: j => (nj.has(j) ? 'a-n' : '') }, rl(c.n))
    ] };
  }

  const api = { fromComparison, fromUnit, build, check, checkText, tableHTML, toTSV, standaloneHTML, rowLabel, rowNotes, cellText, TABLE_CSS, OPT, _norm: norm, _sim: sim };
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.Synoptic = api;
})(typeof window !== 'undefined' ? window : this);
