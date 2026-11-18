// Tests for docs/explorer/synoptic.js. Run: node tests/synoptic_test.js
//  1. Integrity on every comparison in the explorer: no word lost, added or duplicated; each witness's order kept.
//  2. Behaviour on Moshe Lavee's reference cases (sources: his synoptic developer handoff, 2026-11-09):
//     A = "יספת לגוי יי" (verify/30), B = "גם את זה לעומת זה" (verify/57).
const path = require('path'), fs = require('fs'), assert = require('assert');
const E = path.join(__dirname, '..', 'docs', 'explorer');
const S = require(path.join(E, 'synoptic.js'));
const D = JSON.parse(fs.readFileSync(path.join(E, 'core.json'))), T = JSON.parse(fs.readFileSync(path.join(E, 'texts.json')));
const map = (a, k) => Object.fromEntries(a.map(x => [x[k], x]));
const ctx = { D, T, W: map(D.works, 'key'), C: map(D.cands, 'id'), U: map(D.units, 'uid') };
let fails = 0;
const test = (name, fn) => { try { fn(); console.log('ok   ' + name); } catch (e) { fails++; console.log('FAIL ' + name + '\n     ' + e.message); } };

// 1. integrity, all comparisons
test(`integrity on all ${D.comps.length} comparisons`, () => {
  const t0 = Date.now(); let rows = 0, worst = 0, bad = [];
  D.comps.forEach((_, i) => {
    const t = Date.now(), res = S.build(S.fromComparison(ctx, i)), rep = S.check(res);
    worst = Math.max(worst, Date.now() - t); rows += res.rows.length;
    if (!rep.ok) bad.push(i);
    // the rendered text of each witness, row by row, is exactly its window
    res.witnesses.forEach((w, v) => {
      const got = res.rows.map(r => r.cells[v].map(x => res.spec.witnesses[v].tokens[x]).join(' ')).filter(Boolean).join(' ');
      const exp = w.idx.map(x => res.spec.witnesses[v].tokens[x]).join(' ');
      if (got !== exp) bad.push(i + ':' + v);
    });
  });
  console.log(`     ${rows} rows, ${(rows / D.comps.length).toFixed(1)} per comparison; ${Date.now() - t0} ms in all, slowest ${worst} ms`);
  assert.deepStrictEqual(bad, [], 'failed: ' + bad.slice(0, 10).join(', '));
});

const text = (res, r, v) => r.cells[v].map(x => res.spec.witnesses[v].tokens[x]).join(' ');
const rowWith = (res, v, s) => res.rows.find(r => text(res, r, v).includes(s));
const has = (r, v) => r.cells[v].length > 0;

// 2A. "יספת לגוי יי": Oppenheim / Pesikta deRav Kahana / Midrash HaGadol
const A = S.build(S.fromComparison(ctx, 30));
test('A: separate prologues are not forced into one row', () => {
  const o = rowWith(A, 0, 'ויאמר נחמיה'), p = rowWith(A, 1, 'החג אנו');
  assert(o && p && o !== p && !has(o, 1) && !has(p, 0));
});
test('A: Pharaoh, Sennacherib, Nebuchadnezzar, David, Solomon, Daniel each read in parallel across all three', () => {
  ['לפרעה', 'לסנחריב', 'לדוד', 'לשלמה', 'לדניאל'].forEach(k => { const r = rowWith(A, 0, k); assert(r && has(r, 1) && has(r, 2), k); assert(text(A, r, 1).includes(k) && text(A, r, 2).includes(k), k + ' in the same row'); });
  const r = rowWith(A, 0, 'לנבוכד'); assert(r && /לנבוכד/.test(text(A, r, 1)) && /לנבוכדנצר/.test(text(A, r, 2)));
});
test('A: the rest of the Sennacherib quotation is in Oppenheim and MHG, with the PdRK cell empty', () => {
  const r = rowWith(A, 0, 'כי יציל'); assert(r && !has(r, 1) && has(r, 2) && text(A, r, 2).includes('כי יציל'));
});
test('A: the expanded end in MHG is kept', () => { const r = rowWith(A, 2, 'אומות העולם'); assert(r && !has(r, 0)); });

// 2B. "גם את זה לעמת זה"
const B = S.build(S.fromComparison(ctx, 57));
test('B: "יצא זה צדיק וזה רשע" before the attribution in Oppenheim, after it in the parallels, marked as a change of order', () => {
  const o = rowWith(B, 0, 'יצא זה צדיק'), p = rowWith(B, 1, 'ויצא זה צדיק'), att = rowWith(B, 0, 'בשם ר סימון');
  assert(o && p && att && o.n < att.n && p.n > att.n, 'order');
  assert(o.moved.includes(p.n) && p.moved.includes(o.n), 'linked');
});
test('B: "אגודה של ירק" in PdRK and MHG, Oppenheim cell empty', () => {
  const r = rowWith(B, 1, 'אגודה'); assert(r && !has(r, 0) && text(B, r, 2).includes('אגודה'));
});
test('B: additions found only in MHG are not attached to a shared row', () => {
  ['אבא בר כהנא', 'והיו דראון'].forEach(k => { const r = rowWith(B, 2, k); assert(r && !has(r, 0) && !has(r, 1), k); });
});
test('exports: TSV has a header and one line per row; HTML is a full document', () => {
  const tsv = S.toTSV(A).trim().split('\r\n'); assert.strictEqual(tsv.length, A.rows.length + 1);
  assert(tsv[0].includes('פסיקתא דרב כהנא (28 Ot 1 6)'));
  const html = S.standaloneHTML(A, { title: 't' }); assert(html.startsWith('<!doctype html>') && html.includes('class="syn"'));
});
// 3. all witnesses of a unit (N columns)
test(`unit synopsis: integrity on all ${D.units.length} units`, () => {
  let bad = [], maxCols = 0;
  D.units.forEach(u => { const r = S.build(S.fromUnit(ctx, u.uid)); maxCols = Math.max(maxCols, r.witnesses.length); if (!S.check(r).ok) bad.push(u.uid); });
  console.log(`     up to ${maxCols} columns`);
  assert.deepStrictEqual(bad, []);
});
test('unit synopsis: columns ordered by dating, Oppenheim first', () => {
  const r = S.build(S.fromUnit(ctx, 'fol_23v_1#u1')), yrs = r.witnesses.slice(1).map(w => ctx.W[w.key].date_from);
  assert.strictEqual(r.witnesses[0].key, 'Oppenheim_128');
  assert.deepStrictEqual(yrs, yrs.slice().sort((a, b) => a - b));
});

// 4. signals (docs/explorer/signals.js), checked on Moshe's own examples and on the 487 labelled pairs
const G = require(path.join(E, 'signals.js'));
const NZ = G.noise(D, T), RN = G.runs(D), RO = G.roles(D.works);
test('noise: Moshe\'s two noise examples are flagged (df4708c8 fol 16r 1 c6, d3a5f31e fol 174v 2 c8)', () => {
  assert(NZ['Oppenheimer_128_fol_16r_1|6'].flag && NZ['Oppenheimer_128_fol_174v_2|8'].flag);
});
test('noise: his meaningful short phrase is not flagged, and is found as the rarest run (b9c24a7e fol 14r 1 c1)', () => {
  const n = NZ['Oppenheimer_128_fol_14r_1|1']; assert(!n.flag && n.rare.text.includes('בספר אוריתא דמשה'));
});
test('noise: on the labelled pairs it flags most "אין קשר" and almost no "אותו טקסט"', () => {
  const lab = D.cands.filter(c => c.rel), none = lab.filter(c => c.rel === 'אין קשר'), same = lab.filter(c => /^אותו טקסט/.test(c.rel));
  const fn = none.filter(c => NZ[c.id] && NZ[c.id].flag).length, fs_ = same.filter(c => NZ[c.id] && NZ[c.id].flag).length;
  console.log(`     אין קשר flagged ${fn}/${none.length}; אותו טקסט flagged ${fs_}/${same.length}`);
  assert(fn / none.length > 0.5 && fs_ / same.length < 0.05);
});
test('runs: inside the Pesikta run, a Midrash HaGadol match is marked as inside the run of PdRK (b86bc045)', () => {
  const c = D.cands.find(x => x.k === 'Midrash_HaGadol' && RN[x.id].inRunOf === 'Pesikta_DRav_Kahanna'); assert(c);
  assert(!D.cands.some(x => x.k === 'Pesikta_DRav_Kahanna' && RN[x.id].inRunOf === 'Pesikta_DRav_Kahanna'));
});
test('roles: Yalkut Shimoni = late yalkut, Otzar Midrashim = modern yalkut, PdRK = early (7a72b469)', () => {
  assert.strictEqual(RO.Yalkut_Shimoni_on_Torah.key, 'lateyalkut'); assert.strictEqual(RO.Otzar_Midrashim.key, 'modern'); assert.strictEqual(RO.Pesikta_DRav_Kahanna.key, 'early');
});
test('windows (Q6): fol 173r 1 c1 is flagged; its alignment starts at word 70 of 194, in the next tale (e52f039b)', () => {
  const WN = G.windows(D, T), w = WN['Oppenheimer_128_fol_173r_1|1'];
  assert(w.late && w.j0 === 69 && w.n === 194);
  const late = D.cands.filter(c => WN[c.id] && WN[c.id].late);
  console.log(`     flagged ${late.length} of ${Object.keys(WN).length}; ${late.filter(c => c.above).length} above the threshold`);
});
// 5. the model tab and the raw ACT tab (pipeline/r4)
test('model report: out-of-fold precision and recall at p ≥ 0.8 match D5 (98.1%, 85.8%)', () => {
  const R = JSON.parse(fs.readFileSync(path.join(E, 'model_report.json'))), r = R.oof.find(x => x.t === 0.8);
  assert.strictEqual(R.n, 487); assert(Math.abs(r.precision - 0.981) < 0.0006 && Math.abs(r.recall - 0.858) < 0.0006);
});
test('model breakdown: the six contributions add up to S for every candidate (within rounding)', () => {
  const m = D.model, bad = D.cands.filter(c => {
    const v = { lN: Math.log1p(c.N), C: c.C, Cp: c.Cp, lscore: Math.log1p(+c.score || 0), align: c.align, tanakh: /^Tanakh/.test(c.loc) ? 1 : 0 };
    return Math.abs(m.F.reduce((a, f, i) => a + v[f] * m.b[i], 0) - c.S) > 0.05; });
  assert.strictEqual(bad.length, 0, bad.slice(0, 3).map(c => c.id).join(', '));
});
test('raw ACT data: every fully aligned candidate in the explorer is in act_raw.json, with the same location', () => {
  const A = JSON.parse(fs.readFileSync(path.join(E, 'act_raw.json'))), li = A.cols.indexOf('loc'), fi = A.cols.indexOf('full');
  const full = Object.values(A.p).flat().filter(r => r[fi]).length; assert.strictEqual(full, D.cands.length);
  D.cands.forEach(c => { const r = A.p[c.pid][c.rank]; assert(r && r[li] === c.loc && r[fi] === 1, c.id); });
});
console.log(fails ? `\n${fails} failed` : '\nall passed');
process.exit(fails ? 1 : 0);
