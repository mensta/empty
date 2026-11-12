// Sequential crawl of HOME'S list pages with plain headless Chromium (UA: HeadlessChrome -> Chrome only).
// Waits GAP seconds between page loads, stops after 2 consecutive failures. No stealth, no solving, no retries.
import { chromium } from '/usr/local/share/npm-global/lib/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const GAP = Number(process.env.GAP || 6);
const BLOCK = process.env.BLOCK !== '0';
const LINES = { toyoko: 'tokyutoyoko-line', meguro: 'tokyumeguro-line' };
const q = 'cond%5Bmadori%5D%5B15%5D=15&cond%5Bmonthmoneyroomh%5D=19&cond%5Bwalkminutesh%5D=10';
const sleep = ms => new Promise(r => setTimeout(r, ms));

const browser = await chromium.launch({ headless: true });
const probe = await browser.newContext(); const pp = await probe.newPage();
const ua = (await pp.evaluate(() => navigator.userAgent)).replace('HeadlessChrome', 'Chrome'); await probe.close();
const ctx = await browser.newContext({ locale: 'ja-JP', userAgent: ua });
if (BLOCK) await ctx.route('**/*', r => ['image', 'media', 'font'].includes(r.request().resourceType()) ? r.abort() : r.continue());
const page = await ctx.newPage();
let nReq = 0; page.on('request', () => nReq++);

const log = []; let consecutiveFail = 0; let first = true;
outer: for (const [line, slug] of Object.entries(LINES)) {
  let pages = null;
  for (let n = 1; n <= (pages || 1); n++) {
    if (!first) await sleep(GAP * 1000);
    first = false;
    const url = `https://www.homes.co.jp/chintai/tokyo/${slug}/list/?${q}` + (n > 1 ? `&page=${n}` : '');
    const t0 = Date.now(); let status = null, err = null;
    try {
      const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
      status = resp.status();
      await page.waitForSelector('div.prg-building', { timeout: 15000 }).catch(() => {});
    } catch (e) { err = String(e).slice(0, 120); }
    const info = await page.evaluate(() => ({
      title: document.title.slice(0, 40),
      buildings: document.querySelectorAll('div.prg-building').length,
      rooms: new Set([...document.querySelectorAll('table.unitSummary tr a.prg-detailAnchor')].map(a => a.href.split('?')[0])).size,
      total: (document.body.innerText.match(/([\d,]+)\s*件\s*[（(]\s*総物件数/) || [])[1] || null,
    })).catch(() => ({ title: null, buildings: 0, rooms: 0, total: null }));
    if (n === 1 && info.total) pages = Math.ceil(Number(info.total.replace(/,/g, '')) / 30);
    const ok = status === 200 && info.buildings > 0;
    if (ok) fs.writeFileSync(`pages/${line}_${n}.html`, await page.content());
    const rec = { line, page: n, of: pages, status, ok, secs: +((Date.now() - t0) / 1000).toFixed(1), ...info, err };
    log.push(rec); console.log(JSON.stringify(rec));
    consecutiveFail = ok ? 0 : consecutiveFail + 1;
    if (consecutiveFail >= 2) { console.log('STOP: 2 consecutive failures'); break outer; }
  }
}
console.log(JSON.stringify({ summary: { gap: GAP, blockAssets: BLOCK, loads: log.length, ok: log.filter(x => x.ok).length, browserRequests: nReq, rooms: log.reduce((a, x) => a + (x.ok ? x.rooms : 0), 0) } }));
fs.writeFileSync('run_gap' + GAP + '.json', JSON.stringify(log, null, 1));
await browser.close();
