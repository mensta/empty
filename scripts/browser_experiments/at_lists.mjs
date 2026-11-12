// at home list pages in a headless browser (UA + Client Hints say Chrome). Page 1 by URL, the rest by CLICKING the page-number link.
import { open, fs, sleep, GAP, STAGE } from './hm_common.mjs';
const MAXP = Number(process.env.MAXP || 6);
const base = 'https://www.athome.co.jp/chintai/theme/madori_1ldk/tokyo/tokyutoyoko-line/list/';
const { browser, newPage } = await open();
const page = await newPage();
const info = () => page.evaluate(() => ({
  title: document.title.slice(0, 40), url: location.href.slice(0, 100),
  cards: document.querySelectorAll('div.property-card').length, rooms: document.querySelectorAll('div.room-info').length,
  sort: [...document.querySelectorAll('#sort-options option')].filter(o => o.selected).map(o => o.textContent.trim())[0] || null,
  total: (document.body.innerText.match(/該当件数\s*([\d,]+)/) || [])[1] || null,
  challenge: /認証中|Click to verify|confirm you are human/.test(document.body.innerText.slice(0, 600)),
})).catch(() => ({ title: null, cards: 0, rooms: 0, challenge: false }));
const log = [];
for (let n = 1; n <= MAXP; n++) {
  if (n > 1) await sleep(GAP * 1000);
  const t0 = Date.now(); let status = null, err = null, how = n === 1 ? 'goto' : 'click';
  try {
    if (n === 1) { const r = await page.goto(base + '?sort=33', { waitUntil: 'domcontentloaded', timeout: 45000 }); status = r.status(); }
    else {
      const a = page.locator(`a[href$="/page${n}/"]`).first();
      if (await a.count() === 0) { console.log(`no link to page ${n}: stop`); break; }
      await Promise.all([page.waitForURL(new RegExp(`/page${n}/`), { timeout: 30000 }), a.click({ timeout: 10000 })]);
    }
  } catch (e) { err = String(e).slice(0, 100); }
  await page.waitForSelector('div.property-card', { timeout: 15000 }).catch(() => {});
  const i = await info(); const ok = i.cards > 0 && !i.challenge;
  if (ok) fs.writeFileSync(`pages/AT_${n}.html`, await page.content());
  const rec = { page: n, how, status, ok, secs: +((Date.now() - t0) / 1000).toFixed(1), ...i, err };
  log.push(rec); console.log(JSON.stringify(rec));
  if (!ok) { console.log(`STOP: blocked or empty at at home page ${n} (no retry, no bypass)`); break; }
}
console.log(JSON.stringify({ summary: { loads: log.length, ok: log.filter(x => x.ok).length, rooms: log.filter(x => x.ok).reduce((a, x) => a + x.rooms, 0) } }));
fs.writeFileSync(`run_athome_${STAGE}.json`, JSON.stringify(log, null, 1));
await browser.close();
