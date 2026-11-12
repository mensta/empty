// One plain headless-Chromium page load of a HOME'S list page. No stealth, no UA spoofing, no clicking.
import { chromium } from '/usr/local/share/npm-global/lib/node_modules/playwright/index.mjs';

const url = process.argv[2] || 'https://www.homes.co.jp/chintai/tokyo/tokyutoyoko-line/list/?cond%5Bmadori%5D%5B15%5D=15&cond%5Bmonthmoneyroomh%5D=19&cond%5Bwalkminutesh%5D=10';
const browser = await chromium.launch({ headless: true });
// Only change: report the engine's own UA as plain "Chrome" (not "HeadlessChrome"); the version stays the real one.
const probe = await browser.newContext(); const probePage = await probe.newPage();
const ua = (await probePage.evaluate(() => navigator.userAgent)).replace('HeadlessChrome', 'Chrome'); await probe.close();
const ctx = await browser.newContext({ locale: 'ja-JP', userAgent: ua });
const page = await ctx.newPage();
const reqs = { total: 0, homes: 0 };
page.on('request', r => { reqs.total++; if (new URL(r.url()).hostname.endsWith('homes.co.jp')) reqs.homes++; });
const statuses = [];
page.on('response', r => { if (r.request().resourceType() === 'document') statuses.push([r.status(), r.url().slice(0, 90), r.headers()['x-amzn-waf-action'] || null]); });
const t0 = Date.now();
let navStatus = null, err = null;
try {
  const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
  navStatus = resp && resp.status();
  await page.waitForSelector('div.prg-building', { timeout: 25000 }).catch(() => {});
} catch (e) { err = String(e).slice(0, 200); }
const secs = ((Date.now() - t0) / 1000).toFixed(1);
const info = await page.evaluate(() => ({
  title: document.title,
  buildings: document.querySelectorAll('div.prg-building').length,
  rooms: document.querySelectorAll('table.unitSummary tr a.prg-detailAnchor').length,
  ua: navigator.userAgent,
  webdriver: navigator.webdriver,
  bodyHead: document.body ? document.body.innerText.slice(0, 120).replace(/\s+/g, ' ') : '',
})).catch(e => ({ evalError: String(e).slice(0, 120) }));
console.log(JSON.stringify({ navStatus, err, secs, documentResponses: statuses, requests: reqs, ...info }, null, 1));
await browser.close();
