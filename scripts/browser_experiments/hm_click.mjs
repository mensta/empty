// Experiment D: same as hm_crawl.mjs (UA Chrome, 6 s gap, assets blocked, one context) but pages 2.. are reached by CLICKING the "next" link.
import { chromium } from '/usr/local/share/npm-global/lib/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const GAP = Number(process.env.GAP || 6), MAXP = Number(process.env.MAXP || 10);
const q = 'cond%5Bmadori%5D%5B15%5D=15&cond%5Bmonthmoneyroomh%5D=19&cond%5Bwalkminutesh%5D=10';
const sleep = ms => new Promise(r => setTimeout(r, ms));
const browser = await chromium.launch({ headless: true });
const probe = await browser.newContext(); const pp = await probe.newPage();
const ua = (await pp.evaluate(() => navigator.userAgent)).replace('HeadlessChrome', 'Chrome'); await probe.close();
const ctx = await browser.newContext({ locale: 'ja-JP', userAgent: ua });
await ctx.route('**/*', r => ['image', 'media', 'font'].includes(r.request().resourceType()) ? r.abort() : r.continue());
const page = await ctx.newPage();
let lastDoc = null;
page.on('response', r => { if (r.request().resourceType() === 'document') lastDoc = { status: r.status(), referer: r.request().headers()['referer'] || null, url: r.url().slice(0, 100) }; });

async function snapshot(n, how, t0) {
  await page.waitForSelector('div.prg-building', { timeout: 15000 }).catch(() => {});
  const info = await page.evaluate(() => ({
    title: document.title.slice(0, 40), url: location.href.slice(0, 100),
    buildings: document.querySelectorAll('div.prg-building').length,
    rooms: new Set([...document.querySelectorAll('table.unitSummary tr a.prg-detailAnchor')].map(a => a.href.split('?')[0])).size,
    total: (document.body.innerText.match(/([\d,]+)\s*件\s*[（(]\s*総物件数/) || [])[1] || null,
  })).catch(() => ({ title: null, buildings: 0, rooms: 0, total: null, url: null }));
  const ok = lastDoc && lastDoc.status === 200 && info.buildings > 0;
  if (ok) fs.writeFileSync(`pages/click_toyoko_${n}.html`, await page.content());
  const rec = { page: n, how, ok, secs: +((Date.now() - t0) / 1000).toFixed(1), doc: lastDoc, ...info };
  console.log(JSON.stringify(rec)); return rec;
}

const log = []; let fails = 0;
let t0 = Date.now();
await page.goto(`https://www.homes.co.jp/chintai/tokyo/tokyutoyoko-line/list/?${q}`, { waitUntil: 'domcontentloaded', timeout: 45000 }).catch(e => console.log('goto err', String(e).slice(0, 100)));
log.push(await snapshot(1, 'goto', t0));
for (let n = 2; n <= MAXP; n++) {
  if (!log[log.length - 1].ok && ++fails >= 2) { console.log('STOP: 2 consecutive failures'); break; }
  await sleep(GAP * 1000);
  const next = page.locator('a', { hasText: /^次[へヘ]$/ }).last();
  if (await next.count() === 0) { console.log('no next link: stop'); break; }
  t0 = Date.now();
  try {
    await Promise.all([page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 45000 }), next.click({ timeout: 10000 })]);
  } catch (e) { console.log('click/nav err', String(e).slice(0, 100)); }
  const rec = await snapshot(n, 'click', t0); log.push(rec);
  if (rec.ok) fails = 0; else if (++fails >= 2) { console.log('STOP: 2 consecutive failures'); break; }
}
const okN = log.filter(x => x.ok);
console.log(JSON.stringify({ summary: { gap: GAP, loads: log.length, ok: okN.length, buildings: okN.reduce((a, x) => a + x.buildings, 0), rooms: okN.reduce((a, x) => a + x.rooms, 0) } }));
fs.writeFileSync('run_click.json', JSON.stringify(log, null, 1));
await browser.close();
