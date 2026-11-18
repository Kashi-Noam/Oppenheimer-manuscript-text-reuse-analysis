/* signals.js: reading aids computed from the explorer's data (core.json, texts.json). Browser global window.Signals
 * and CommonJS module. Nothing here changes a score, the threshold (D5) or a verdict (D6). These are flags shown
 * next to the data, following Moshe Lavee's review comments of November 2026.
 *
 *  roles(works)       witness roles: early / late / late yalkut / modern yalkut (comment 7a72b469). A proposed rule.
 *  runs(D)            run context per candidate. Does the same work match the neighbouring passages (6441b0ce)?
 *                     Does the candidate sit inside a long run of another work that matches here as strongly or more
 *                     strongly (b86bc045)?
 *  noise(D, T)        noise signals per candidate: common words, repeated words, the rarest aligned phrase
 *                     (df4708c8, d3a5f31e, b9c24a7e).
 *  windows(D, T)      where the alignment starts inside ACT's source window (e52f039b, Q6). ACT names each window of about
 *                     190–200 words after its first segment. When the aligned words start late in the window, the
 *                     reference may name an earlier segment, or even the previous tale or chapter.
 */
(function (root) {
  'use strict';
  const FIN = { 'ך': 'כ', 'ם': 'מ', 'ן': 'נ', 'ף': 'פ', 'ץ': 'צ' };
  const norm = w => String(w == null ? '' : w).replace(/[^א-ת]/g, '').replace(/[ךםןףץ]/g, c => FIN[c]);

  // ---------- witness roles ----------
  const ROLE_RULE = 'כלל מוצע (לבדיקה): ילקוט/אוסף שתוארך משנת 1700 ואילך = ילקוט מודרני; ילקוט/אוסף אחר = ילקוט מאוחר; ' +
    'חיבור אחר (מדרש, תלמוד, מסכת קטנה) שתחילת תיארוכו לפני שנת 1000 = מוקדם, ואחרת = מאוחר. התיארוכים עצמם טרם נבדקו.';
  function role(w) {
    if (!w) return null;
    const anth = /ילקוט|אוסף/.test(w.type || '');
    if (anth) return (w.date_from || 0) >= 1700 ? { key: 'modern', he: 'ילקוט מודרני' } : { key: 'lateyalkut', he: 'ילקוט מאוחר' };
    return (w.date_from || 0) < 1000 ? { key: 'early', he: 'מוקדם' } : { key: 'late', he: 'מאוחר' };
  }
  function roles(works) { const o = {}; works.forEach(w => { o[w.key] = role(w); }); return o; }

  // ---------- run context ----------
  function runs(D, opt) {
    opt = Object.assign({ win: 2, runMin: 3, close: 1.0, all: false }, opt || {});  // all: count every fully aligned candidate, not only those above the threshold
    const order = {}; D.passages.forEach((p, i) => { order[p.pid] = i; });
    const aboveAt = D.passages.map(() => new Map());   // passage index → work → max S above the threshold
    D.cands.forEach(c => { if (!c.above && !opt.all) return; const m = aboveAt[order[c.pid]]; if (m && (m.get(c.k) || 0) < c.S) m.set(c.k, c.S); });
    // the dominant run at each passage: a work above the threshold in at least runMin of the 2·win+1 passages around it
    const run = D.passages.map((_, i) => {
      const cnt = new Map();
      for (let d = -opt.win; d <= opt.win; d++) { const m = aboveAt[i + d]; if (m) m.forEach((s, k) => cnt.set(k, (cnt.get(k) || 0) + 1)); }
      let best = null, bn = 0;
      cnt.forEach((n, k) => { if (n > bn || (n === bn && best && (aboveAt[i].get(k) || 0) > (aboveAt[i].get(best) || 0))) { best = k; bn = n; } });
      return bn >= opt.runMin ? { k: best, n: bn } : null;
    });
    const out = {};
    D.cands.forEach(c => {
      const i = order[c.pid];
      const nb = [-2, -1, 1, 2].filter(d => aboveAt[i + d] && aboveAt[i + d].has(c.k));
      const adj = nb.filter(d => Math.abs(d) === 1).length;
      const r = run[i];
      const rS = r ? aboveAt[i].get(r.k) : undefined;
      const inRunOf = r && r.k !== c.k && rS !== undefined && rS >= c.S - opt.close ? r.k : null;
      out[c.id] = { nb: nb.length, adj, run: r ? r.k : null, inRunOf, rescue: !opt.all && !c.above && adj > 0 };
    });
    return out;
  }

  // ---------- noise ----------
  function noise(D, T, opt) {
    opt = Object.assign({ common: 0.1 }, opt || {});
    const NP = D.passages.length, df = new Map(), toksOf = {};
    D.passages.forEach(p => {
      const t = (T.p[p.pid] || '').split(' ').map(norm); toksOf[p.pid] = t;
      new Set(t.filter(Boolean)).forEach(w => df.set(w, (df.get(w) || 0) + 1));
    });
    const idf = w => Math.log(NP / (df.get(w) || 1));
    const raw = {};
    D.passages.forEach(p => { raw[p.pid] = (T.p[p.pid] || '').split(' '); });
    const out = {};
    D.cands.forEach(c => {
      const t = T.c[c.id]; if (!t) return;
      const toks = toksOf[c.pid], idx = [...new Set(t.al.map(a => a[0]))].filter(i => toks[i]).sort((a, b) => a - b);
      if (!idx.length) return;
      const words = idx.map(i => toks[i]);
      const common = words.filter(w => (df.get(w) || 0) / NP >= opt.common).length / words.length;
      const types = new Set(words).size / words.length;
      // contiguous runs in the Oppenheim passage; the rarest = the run with the largest sum of IDF
      let runsArr = [], cur = [idx[0]];
      for (let k = 1; k < idx.length; k++) { if (idx[k] === idx[k - 1] + 1) cur.push(idx[k]); else { runsArr.push(cur); cur = [idx[k]]; } }
      runsArr.push(cur);
      const longest = Math.max(...runsArr.map(r => r.length));
      const scoreRun = r => r.reduce((s, i) => s + idf(toks[i]), 0);
      const rare = runsArr.reduce((b, r) => (scoreRun(r) > scoreRun(b) ? r : b), runsArr[0]);
      const flag = (longest <= 3 && common >= 0.5) || types < 0.5;
      out[c.id] = {
        n: words.length, common: +common.toFixed(2), types: +types.toFixed(2), longest,
        rare: { text: rare.map(i => raw[c.pid][i]).join(' '), len: rare.length, idf: +(scoreRun(rare) / rare.length).toFixed(2), from: rare[0], to: rare[rare.length - 1] },
        flag
      };
    });
    return out;
  }

  // ---------- source windows (Q6) ----------
  function windows(D, T, opt) {
    opt = Object.assign({ late: 1 / 3 }, opt || {});
    const out = {};
    D.cands.forEach(c => {
      const t = T.c[c.id]; if (!t || !t.al.length) return;
      const n = t.src.split(' ').length, js = t.al.map(a => a[1]), j0 = Math.min(...js), j1 = Math.max(...js);
      out[c.id] = { n, j0, j1, late: j0 / n > opt.late };
    });
    return out;
  }

  const HELP = {
    rank: 'דירוג המועמד ברשימה של ACT לקטע הזה (0 = הראשון).',
    S: 'הציון המשוכלל: S = 1.975·ln(1+N) + 5.676·C + 3.248·Cp + 1.085·ln(1+score) + 6.459·align − 2.29·[תנ״ך]. הסף: S ≥ 21.14 (D5, D7).',
    p: 'ההסתברות שהזוג הוא "אותו טקסט" לפי המודל הלוגיסטי: p = 1/(1+e^−(S−19.75)). מעל הסף: p ≥ 0.8.',
    N: 'מספר המילים בקטע אופנהיימר שיושרו למקור.',
    C: 'כיסוי המקור: חלק המילים בחלון המקור של ACT שיושרו (0–1).',
    Cp: 'כיסוי הקטע: חלק המילים בקטע אופנהיימר שיושרו (0–1).',
    score: 'ציון היישור הגולמי של ACT (alignment_details.score).',
    align: 'alignment_score של ACT למועמד.',
    norm: 'norm_score של ACT למועמד.',
    tag: 'תיוג ידני, לפי קטגוריות התיוג (D4).',
    run: 'רצף: בכמה מארבעת הקטעים הסמוכים (±2) יש לאותו חיבור התאמה מעל הסף. "↑ מתחת לסף, אבל..." = מתחת לסף, והחיבור מופיע מעל הסף בקטע הסמוך (הערה 6441b0ce).',
    inrun: 'בתוך רצף של חיבור אחר: החיבור הזה מופיע כאן בתוך רצף ארוך של חיבור אחר (מעל הסף ב־3 לפחות מ־5 הקטעים), וההתאמה של החיבור האחר כאן חזקה לפחות כמעט כמוה. לפי הערה b86bc045, זו כנראה מקבילה או עד נוסח משני, ולא הטקסט שהובא.',
    noise: 'חשד לרעש: היישור בנוי ממילים נפוצות ברצפים של עד 3 מילים, או ממילים שחוזרות (למשל שם חכם). רק סימון, לא שינוי של הציון (הערות df4708c8, d3a5f31e).',
    ref: 'מראה המקום ש־ACT נותן הוא של המקטע שבו מתחיל חלון המקור (כ־194 מילים), ולא בהכרח של המקום שבו נמצא הטקסט המיושר. החלון עשוי לגלוש למקטעים הבאים, ואפילו לסיפור או לפרק הבא (Q6, הערה e52f039b).',
    win: '⚠ חלון: היישור מתחיל אחרי השליש הראשון של חלון המקור. ייתכן שהטקסט המיושר נמצא במקטע מאוחר ממראה המקום, ואפילו בסיפור או בפרק הבא (Q6). לבדיקה: פתחו את המקור ובדקו איפה מתחילות המילים המיושרות.',
    rare: 'הרצף הנדיר ביותר: רצף המילים המיושרות הרציף בקטע עם סכום ה־IDF הגבוה ביותר (IDF מחושב על 505 הקטעים של אופנהיימר) (הערה b9c24a7e).'
  };

  const api = { roles, role, ROLE_RULE, runs, noise, windows, HELP, _norm: norm };
  if (typeof module === 'object' && module.exports) module.exports = api; else root.Signals = api;
})(typeof window !== 'undefined' ? window : this);
