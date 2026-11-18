// Print the synoptic rows of one comparison as text: node tests/synoptic_show.js <compIndex>
const path = require('path'), fs = require('fs');
const E = path.join(__dirname, '..', 'docs', 'explorer');
const S = require(path.join(E, 'synoptic.js'));
const D = JSON.parse(fs.readFileSync(path.join(E, 'core.json'))), T = JSON.parse(fs.readFileSync(path.join(E, 'texts.json')));
const map = (a, k) => Object.fromEntries(a.map(x => [x[k], x]));
const ctx = { D, T, W: map(D.works, 'key'), C: map(D.cands, 'id'), U: map(D.units, 'uid') };
const i = +process.argv[2];
const res = S.build(S.fromComparison(ctx, i));
console.log(res.witnesses.map(w => `${w.name} [${w.ref}] ${w.lo}-${w.hi}`).join(' | '));
res.rows.forEach(r => {
  console.log(`\n${r.n} · ${S.rowLabel(res, r)} ${S.rowNotes(r).join(' ')}`);
  r.cells.forEach((_, v) => { const t = S.cellText(res, r, v, true); console.log('   ' + ['O', '1', '2'][v] + ': ' + (t || '—')); });
});
console.log('\n' + S.checkText(S.check(res)));
