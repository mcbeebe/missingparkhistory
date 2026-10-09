// Builds the tone-review Word document from tone-review-draft.json/.md.
// Usage: NODE_PATH=$(npm root -g) node build-tone-review-docx.js tone-review-v1.0.json tone-review-v1.0.md ../Tone_Review_v1.0.docx
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType,
  ShadingType, BorderStyle, AlignmentType, ExternalHyperlink, LevelFormat, Footer, Header, PageNumber,
  TableOfContents, PageBreak,
} = require('docx');

const [, , jsonPath, mdPath, outPath] = process.argv;
const items = JSON.parse(fs.readFileSync(jsonPath, 'utf8'));
const md = fs.readFileSync(mdPath, 'utf8');

const FONT = 'Calibri';
const C = { navy: '1F3864', red: 'B91C1C', amber: 'B45309', gray: '595959', light: 'F2F2F2', cur: 'FDF2F2', prop: 'EEF7EE', border: 'BFBFBF' };
const SEV = { High: C.red, Medium: C.amber, Low: C.gray };

const ENT = { '&ldquo;': '“', '&rdquo;': '”', '&lsquo;': '‘', '&rsquo;': '’', '&mdash;': '—', '&ndash;': '–',
  '&amp;': '&', '&quot;': '"', '&#39;': "'", '&nbsp;': ' ', '&lt;': '<', '&gt;': '>', '&hellip;': '…', '&middot;': '·', '&eacute;': 'é' };
const unent = (s) => s.replace(/&[a-z#0-9]+;/gi, (e) => (ENT[e] !== undefined ? ENT[e] : e.startsWith('&#') ? String.fromCodePoint(parseInt(e.slice(2).replace(/^x/, '0x'))) : e));

/** HTML fragment -> TextRuns (keeps bold/italic; drops other tags). */
function htmlRuns(html, base = {}) {
  const runs = [];
  let b = 0, i = 0;
  const parts = html.trim().replace(/<p[^>]*>|<\/p>/g, ' ').trim().split(/(<[^>]+>)/);
  for (const p of parts) {
    if (!p) continue;
    if (p.startsWith('<')) {
      const t = p.toLowerCase();
      if (/^<(strong|b)\b/.test(t)) b++; else if (/^<\/(strong|b)>/.test(t)) b = Math.max(0, b - 1);
      else if (/^<(em|i)\b/.test(t)) i++; else if (/^<\/(em|i)>/.test(t)) i = Math.max(0, i - 1);
      continue;
    }
    const text = unent(p).replace(/\s+/g, ' ');
    if (text) runs.push(new TextRun({ text, bold: b > 0 || base.bold, italics: i > 0 || base.italics, font: FONT, size: base.size || 21, color: base.color }));
  }
  if (runs.length) {
    // trim leading/trailing whitespace of the whole block
    const first = runs[0], last = runs[runs.length - 1];
    first.root && 0; // no-op (TextRun is immutable); whitespace is harmless
  }
  return runs;
}

/** Markdown inline (**bold**, `code`) -> TextRuns. */
function mdRuns(s, base = {}) {
  const out = [];
  for (const part of s.split(/(\*\*[^*]+\*\*|`[^`]+`)/)) {
    if (!part) continue;
    if (part.startsWith('**')) out.push(new TextRun({ text: part.slice(2, -2), bold: true, font: FONT, size: base.size || 21 }));
    else if (part.startsWith('`')) out.push(new TextRun({ text: part.slice(1, -1), font: 'Consolas', size: 19 }));
    else out.push(new TextRun({ text: part, font: FONT, size: base.size || 21 }));
  }
  return out;
}

const P = (children, opts = {}) => new Paragraph({ children, spacing: { after: 100, line: 276 }, ...opts });
const T = (text, o = {}) => new TextRun({ text, font: FONT, size: 21, ...o });
const H1 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text, font: FONT, bold: true, size: 32, color: C.navy })], spacing: { before: 360, after: 160 } });
const H2 = (text, color = C.navy) => new Paragraph({ heading: HeadingLevel.HEADING_2, keepNext: true, children: [new TextRun({ text, font: FONT, bold: true, size: 26, color })], spacing: { before: 280, after: 100 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: C.border, space: 2 } } });
const H3 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_3, keepNext: true, children: [new TextRun({ text, font: FONT, bold: true, size: 22, color: '404040' })], spacing: { before: 160, after: 60 } });
const bullet = (children, level = 0) => new Paragraph({ children, numbering: { reference: 'bullets', level }, spacing: { after: 60, line: 264 } });

const W = 9360; // 6.5in content width
const cellBorders = { top: { style: BorderStyle.SINGLE, size: 4, color: C.border }, bottom: { style: BorderStyle.SINGLE, size: 4, color: C.border },
  left: { style: BorderStyle.SINGLE, size: 4, color: C.border }, right: { style: BorderStyle.SINGLE, size: 4, color: C.border } };
const cell = (children, width, fill, opts = {}) => new TableCell({ children, width: { size: width, type: WidthType.DXA }, borders: cellBorders,
  shading: fill ? { type: ShadingType.CLEAR, color: 'auto', fill } : undefined, margins: { top: 80, bottom: 80, left: 120, right: 120 }, ...opts });

function textBox(label, html, fill) {
  if (!html.replace(/<[^>]+>/g, '').trim()) html = '<em>(Delete this text; nothing replaces it.)</em>';
  return new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: [1500, W - 1500], rows: [new TableRow({ cantSplit: false, children: [
    cell([P([T(label, { bold: true, size: 19, color: '404040' })])], 1500, fill),
    cell([P(htmlRuns(html), { spacing: { after: 0, line: 276 } })], W - 1500, fill),
  ] })] });
}

// ---- group JSON items into issues (consecutive items with the same park+severity) ----
const groups = [];
for (const it of items) {
  const g = groups[groups.length - 1];
  if (g && g.park === it.park && g.severity === it.severity) g.items.push(it);
  else groups.push({ park: it.park, severity: it.severity, items: [it] });
}

const idToIssue = {};
groups.forEach((g, n) => g.items.forEach((it, k) => { idToIssue[it.id] = `${n + 1}${g.items.length > 1 ? String.fromCharCode(97 + k) : ''}`; }));
// ---- pull prose sections from the markdown ----
function mdSection(title) {
  const start = md.indexOf(`\n${title}\n`);
  if (start < 0) return '';
  const rest = md.slice(start + title.length + 2);
  const end = rest.search(/\n#{2,3} /);
  return end < 0 ? rest : rest.slice(0, end);
}
function mdBlock(text) {
  const out = [];
  for (let line of text.split('\n')) {
    line = line.replace(' (kept in the scratchpad, not the repo)', '').replace(/\bitem (\d+)/g, (m, a) => `issue ${idToIssue[a]}`).replace(/\bI\b/g, 'we').replace(/^we /, 'We ').replace(/([.:] )we /g, '$1We ');
    if (!line.trim()) continue;
    const m = line.match(/^(\s*)(?:- |\d+\. )(.*)$/);
    if (m) out.push(bullet(mdRuns(m[2]), Math.min(2, Math.floor(m[1].length / 2))));
    else out.push(P(mdRuns(line)));
  }
  return out;
}

const sevCount = (s) => groups.filter((g) => g.severity === s).length;
const body = [];

// Title block
body.push(new Paragraph({ children: [new TextRun({ text: 'Missing Park History', font: FONT, size: 24, color: C.red, bold: true })], spacing: { after: 60 } }));
body.push(new Paragraph({ children: [new TextRun({ text: 'Tone & Sensitivity Review: Park Narratives and Topic Pages', font: FONT, size: 40, bold: true, color: C.navy })], spacing: { after: 120 } }));
body.push(P([T('Version 1.0 · Draft for approval · October 9, 2026', { color: C.gray })]));
body.push(new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: [W], rows: [new TableRow({ children: [cell([
  P([T('Status: nothing on the site has changed. ', { bold: true }), T('Each item below proposes replacement text. Mark each one Approve, Edit or Reject (or reply with the item numbers), and we will apply only the approved wording, rebuild the park pages and open a pull request.')], { spacing: { after: 0, line: 276 } }),
], W, 'FFF7E6')] })] }));

body.push(H1('Why this review'));
body.push(P([T('On the Grand Teton entry, the narrative quoted a removed sign about Gustavus Doane’s part in the 1870 Marias Massacre, in which the U.S. Army killed more than 170 Piegan Blackfeet, many of them women, elders and children. It then moved straight to “the raw power of mountain geology” and a visitor count, with no acknowledgment of the massacre. We need to acknowledge our past in order to move forward, so we reviewed every entry and topic page for the same pattern.')]));

body.push(H1('Summary'));
body.push(bullet([T('Reviewed: ', { bold: true }), T('all 446 map entries (data/parkData.json), the four topic pages, and the Park History sections on the 20 park pages that have them. About 180 entries were read in full.')]));
body.push(bullet([T('Issues with a proposed rewrite: ', { bold: true }), T(`${groups.length} (${items.length} individual text changes)`)]));
body.push(bullet([T('High: ', { bold: true, color: C.red }), T(`${sevCount('High')}`), T('   Medium: ', { bold: true, color: C.amber }), T(`${sevCount('Medium')}`), T('   Low: ', { bold: true, color: C.gray }), T(`${sevCount('Low')}`)]));
body.push(H2('What the problems have in common'));
body.push(...mdBlock(mdSection('### What the problems have in common')));
body.push(H2('Facts we could not fully verify'));
body.push(P([T('Network limits blocked direct access to nps.gov and most news sites. Facts marked “verified” were checked against search-engine summaries of the cited page; facts marked “from our records” come from the entry’s own flagged NPS text or our sourced Park History sections. Please check these before approving:', { italics: true })]));
body.push(...mdBlock(mdSection('### Facts I could not fully verify')));

// Index table
body.push(new Paragraph({ children: [new PageBreak()] }));
body.push(H1('Index of issues'));
const iw = [600, 4560, 1200, 3000];
const hdr = ['#', 'Park or page', 'Severity', 'Where'];
const irows = [new TableRow({ tableHeader: true, children: hdr.map((h, k) => cell([P([T(h, { bold: true, color: 'FFFFFF', size: 19 })], { spacing: { after: 0 } })], iw[k], C.navy)) })];
groups.forEach((g, n) => {
  const where = [...new Set(g.items.map((i) => (i.field === 'page' ? i.file : 'Map entry' + (i.file ? ' + park page' : ''))))].join('; ');
  irows.push(new TableRow({ cantSplit: true, children: [
    cell([P([T(String(n + 1), { size: 19 })], { spacing: { after: 0 } })], iw[0], n % 2 ? C.light : undefined),
    cell([P([T(g.park, { size: 19 })], { spacing: { after: 0 } })], iw[1], n % 2 ? C.light : undefined),
    cell([P([T(g.severity, { size: 19, bold: true, color: SEV[g.severity] })], { spacing: { after: 0 } })], iw[2], n % 2 ? C.light : undefined),
    cell([P([T(where, { size: 18 })], { spacing: { after: 0 } })], iw[3], n % 2 ? C.light : undefined),
  ] }));
});
body.push(new Table({ width: { size: W, type: WidthType.DXA }, columnWidths: iw, rows: irows }));

// Issues
for (const sev of ['High', 'Medium', 'Low']) {
  body.push(new Paragraph({ children: [new PageBreak()] }));
  body.push(H1(`${sev} severity`));
  groups.forEach((g, n) => {
    if (g.severity !== sev) return;
    body.push(H2(`${n + 1}. ${g.park}`, C.navy));
    const keys = [...new Set(g.items.flatMap((i) => i.keys || []))];
    const files = [...new Set(g.items.flatMap((i) => i.files_containing_current_html || [i.file]).filter(Boolean))];
    body.push(P([T('Severity: ', { bold: true }), T(sev, { bold: true, color: SEV[sev] }), T(keys.length ? `   ·   Entry IDs: ${keys.join(', ')}` : '', { color: C.gray }), T(`   ·   Files: ${files.join(', ')}`, { color: C.gray, size: 18 })]));
    g.items.forEach((it, k) => {
      body.push(H3(`${n + 1}${g.items.length > 1 ? String.fromCharCode(97 + k) : ''}. ${unent(it.location.replace(/^narrative, /, ''))}`));
      body.push(P([T('Problem: ', { bold: true }), ...htmlRuns(it.problem)]));
      body.push(textBox('Current', it.current_html, C.cur));
      body.push(P([], { spacing: { after: 60 } }));
      body.push(textBox('Proposed', it.proposed_html, C.prop));
      body.push(P([T('Sources', { bold: true, size: 19 })], { spacing: { before: 100, after: 40 }, keepNext: true }));
      for (const s of it.sources || []) {
        const tag = s.verified ? 'verified (search summary)' : /^https?:/.test(s.url) ? 'from our records / not fetched' : 'from our records';
        const link = /^https?:\/\//.test(s.url)
          ? new ExternalHyperlink({ link: s.url, children: [new TextRun({ text: s.url, style: 'Hyperlink', font: FONT, size: 17 })] })
          : new TextRun({ text: s.url, font: 'Consolas', size: 17 });
        body.push(bullet([link, T(`  [${tag}] `, { size: 17, color: C.gray, italics: true }), T(unent(s.note || ''), { size: 17, color: '404040' })]));
      }
    });
    body.push(P([T('Decision:  ☐ Approve   ☐ Edit   ☐ Reject      Notes: ______________________________________', { size: 19, color: C.gray })], { spacing: { before: 120, after: 120 } }));
  });
}

body.push(new Paragraph({ children: [new PageBreak()] }));
body.push(H1('Smaller notes (no rewrite proposed yet)'));
body.push(...mdBlock(mdSection('## Low-severity notes without a rewrite')));
body.push(H1('Reviewed and fine'));
body.push(...mdBlock(mdSection('## Reviewed and fine')));
body.push(H1('Method'));
body.push(...mdBlock(mdSection('### Method')));

const doc = new Document({
  creator: 'Missing Park History', title: 'Tone & Sensitivity Review v1.0',
  styles: { default: { document: { run: { font: FONT, size: 21 } } },
    characterStyles: [{ id: 'Hyperlink', name: 'Hyperlink', run: { color: '0563C1', underline: {} } }] },
  numbering: { config: [{ reference: 'bullets', levels: [0, 1, 2].map((l) => ({ level: l, format: LevelFormat.BULLET, text: ['•', '–', '◦'][l], alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 360 + l * 360, hanging: 260 } } } })) }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: 'Tone & Sensitivity Review · v1.0 draft', font: FONT, size: 16, color: C.gray })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: ['Page ', PageNumber.CURRENT, ' of ', PageNumber.TOTAL_PAGES], font: FONT, size: 16, color: C.gray })] })] }) },
    children: body,
  }],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(outPath, buf); console.log('wrote', outPath, buf.length, 'bytes;', groups.length, 'issues'); });
