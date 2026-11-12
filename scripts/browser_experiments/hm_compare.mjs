// One page load; save the original HTML (before JS) and the rendered DOM (after JS) for offline comparison.
import { chromium } from '/usr/local/share/npm-global/lib/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const url = 'https://www.homes.co.jp/chintai/tokyo/tokyutoyoko-line/list/?cond%5Bmadori%5D%5B15%5D=15&cond%5Bmonthmoneyroomh%5D=19&cond%5Bwalkminutesh%5D=10';
const browser = await chromium.launch({ headless: true });
const probe = await browser.newContext(); const pp = await probe.newPage();
const ua = (await pp.evaluate(() => navigator.userAgent)).replace('HeadlessChrome', 'Chrome'); await probe.close();
const ctx = await browser.newContext({ locale: 'ja-JP', userAgent: ua });
const page = await ctx.newPage();
const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
fs.writeFileSync('hm_raw.html', await resp.text());
await page.waitForSelector('div.prg-building', { timeout: 25000 }).catch(() => {});
await page.waitForTimeout(3000);
fs.writeFileSync('hm_rendered.html', await page.content());
console.log('status', resp.status());
await browser.close();
