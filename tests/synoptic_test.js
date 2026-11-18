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
console.log(fails ? `\n${fails} failed` : '\nall passed');
process.exit(fails ? 1 : 0);
