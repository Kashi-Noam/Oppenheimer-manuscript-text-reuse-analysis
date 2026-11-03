/**
 * Comments backend for the Oppenheimer 128 explorer (Google Apps Script web app).
 * Every comment is one row in the sheet "הערות" of the spreadsheet this script is attached to.
 * Setup: see comments/SETUP.md in the repository.
 */

// Password for editor mode (changing status and writing replies on the site). Choose your own.
const ADMIN_KEY = 'CHANGE-ME';
// Optional: a password needed to READ the comments on the site. Leave '' to let anyone with the link read them.
const READ_KEY = '';

const SHEET = 'הערות';
const HEAD = ['id', 'created', 'author', 'type', 'tab', 'kind', 'item', 'label', 'url', 'text', 'status', 'reply', 'updated'];
const TYPES = ['question', 'error', 'idea', 'other'];
const STATUS = ['פתוחה', 'בטיפול', 'טופלה', 'לא רלוונטי'];

function sheet_() {
  const ss = SpreadsheetApp.getActive();
  let s = ss.getSheetByName(SHEET);
  if (!s) { s = ss.getSheets()[0]; s.setName(SHEET); }
  if (s.getLastRow() === 0) s.appendRow(HEAD);
  if (s.getFrozenRows() !== 1) {
    s.setFrozenRows(1);
    s.setRightToLeft(true);
    s.getRange(1, 1, 1, HEAD.length).setFontWeight('bold');
  }
  return s;
}

function out_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}

// Stops a value from being read as a spreadsheet formula, and limits its length.
function clean_(v, max) {
  let t = String(v == null ? '' : v).slice(0, max || 500);
  if (/^[=+\-@]/.test(t)) t = "'" + t;
  return t;
}

function doGet(e) {
  const p = (e && e.parameter) || {};
  if (READ_KEY && p.key !== READ_KEY && p.key !== ADMIN_KEY) return out_({ ok: false, error: 'key' });
  const values = sheet_().getDataRange().getValues();
  const head = values.shift();
  const comments = values.filter(r => r[0]).map(r => {
    const o = {};
    head.forEach((k, i) => { o[k] = r[i] instanceof Date ? r[i].toISOString() : r[i]; });
    return o;
  });
  return out_({ ok: true, comments: comments });
}

function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const d = JSON.parse(e.postData.contents);
    const s = sheet_();
    if (d.action === 'add') {
      if (!d.text || !String(d.text).trim()) return out_({ ok: false, error: 'empty' });
      const id = Utilities.getUuid().slice(0, 8);
      s.appendRow([id, new Date(), clean_(d.author, 80), TYPES.indexOf(d.type) >= 0 ? d.type : 'other', clean_(d.tab, 40),
        clean_(d.kind, 40), clean_(d.item, 300), clean_(d.label, 300), clean_(d.url, 500), clean_(d.text, 5000), 'פתוחה', '', '']);
      return out_({ ok: true, id: id });
    }
    if (d.action === 'update') {
      if (d.key !== ADMIN_KEY || ADMIN_KEY === 'CHANGE-ME') return out_({ ok: false, error: 'key' });
      const ids = s.getRange(2, 1, Math.max(s.getLastRow() - 1, 1), 1).getValues().map(r => String(r[0]));
      const i = ids.indexOf(String(d.id));
      if (i < 0) return out_({ ok: false, error: 'not_found' });
      const row = i + 2;
      if (STATUS.indexOf(d.status) >= 0) s.getRange(row, HEAD.indexOf('status') + 1).setValue(d.status);
      s.getRange(row, HEAD.indexOf('reply') + 1).setValue(clean_(d.reply, 5000));
      s.getRange(row, HEAD.indexOf('updated') + 1).setValue(new Date());
      return out_({ ok: true });
    }
    return out_({ ok: false, error: 'action' });
  } catch (err) {
    return out_({ ok: false, error: String(err) });
  } finally {
    lock.releaseLock();
  }
}
