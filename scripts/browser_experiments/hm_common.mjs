// Shared setup: headless Chromium, UA "HeadlessChrome" -> "Chrome" (only change), images/media/fonts not loaded.
import { chromium } from '/usr/local/share/npm-global/lib/node_modules/playwright/index.mjs';
import fs from 'node:fs';
export { fs };
export const sleep = ms => new Promise(r => setTimeout(r, ms));
export const GAP = Number(process.env.GAP || 6);
export const CHALLENGE = /confirm you are human|Request blocked|人間であることを確認/i;
export async function open() {
  const browser = await chromium.launch({ headless: true });
  const probe = await browser.newContext(); const pp = await probe.newPage();
  const ua = (await pp.evaluate(() => navigator.userAgent)).replace('HeadlessChrome', 'Chrome'); await probe.close();
  const ctx = await browser.newContext({ locale: 'ja-JP', userAgent: ua });
  await ctx.route('**/*', r => ['image', 'media', 'font'].includes(r.request().resourceType()) ? r.abort() : r.continue());
  const ver = browser.version(); const major = ver.split('.')[0];
  // Make the Client Hints (sec-ch-ua, navigator.userAgentData) say "Chrome" like the User-Agent string does.
  // Nothing else is changed: navigator.webdriver stays true, no fingerprint patching.
  const meta = {
    brands: [{ brand: 'Not:A-Brand', version: '8' }, { brand: 'Chromium', version: major }, { brand: 'Google Chrome', version: major }],
    fullVersionList: [{ brand: 'Not:A-Brand', version: '8.0.0.0' }, { brand: 'Chromium', version: ver }, { brand: 'Google Chrome', version: ver }],
    fullVersion: ver, platform: 'Linux', platformVersion: '6.6.0', architecture: 'arm', bitness: '64', model: '', mobile: false, wow64: false,
  };
  const newPage = async () => {
    const page = await ctx.newPage();
    const cdp = await ctx.newCDPSession(page);
    await cdp.send('Emulation.setUserAgentOverride', { userAgent: ua, acceptLanguage: 'ja-JP', userAgentMetadata: meta });
    return page;
  };
  return { browser, ctx, newPage, ua };
}
export const LINES = { toyoko: 'tokyutoyoko-line', meguro: 'tokyumeguro-line' };
// 1LDK=15, 2DK=23, 2LDK=25 (checkbox labels on the HOME'S list page)
export const QUERY = 'cond%5Bmadori%5D%5B15%5D=15&cond%5Bmadori%5D%5B23%5D=23&cond%5Bmadori%5D%5B25%5D=25&cond%5Bmonthmoneyroomh%5D=19&cond%5Bwalkminutesh%5D=10';
export const listUrl = line => `https://www.homes.co.jp/chintai/tokyo/${LINES[line]}/list/?${QUERY}`;
export async function listInfo(page) {
  return page.evaluate(() => ({
    title: document.title.slice(0, 50), url: location.href.slice(0, 90),
    buildings: document.querySelectorAll('div.prg-building').length,
    rooms: new Set([...document.querySelectorAll('table.unitSummary tr a.prg-detailAnchor')].map(a => a.href.split('?')[0])).size,
    total: (document.body.innerText.match(/([\d,]+)\s*件\s*[（(]\s*総物件数/) || [])[1] || null,
  })).catch(() => ({ title: null, buildings: 0, rooms: 0, total: null, url: null }));
}
