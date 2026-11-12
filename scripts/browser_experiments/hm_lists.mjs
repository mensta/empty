// Pass 1: walk the list pages of each line by clicking "next". Page 1 of a line is opened by URL; the rest only by clicks.
import { open, fs, sleep, GAP, STAGE, CHALLENGE, listUrl, listInfo } from './hm_common.mjs';
const LINES = (process.env.LINES || 'toyoko,meguro').split(',');
const { browser, ctx, newPage } = await open();
const page = await newPage();
const log = []; let stop = false, first = true;
for (const line of LINES) {
  if (stop) break;
  let n = 1;
  while (true) {
    if (!first) await sleep(GAP * 1000);
    first = false;
    const t0 = Date.now(); let resp = null, how = n === 1 ? 'goto' : 'click', err = null;
    try {
      if (n === 1) resp = await page.goto(listUrl(line), { waitUntil: 'domcontentloaded', timeout: 45000 });
      else {
        const next = page.locator('a', { hasText: /^次[へヘ]$/ }).last();
        if (await next.count() === 0) { console.log(`${line}: no next link after page ${n - 1} (end)`); break; }
        [resp] = await Promise.all([page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 45000 }), next.click({ timeout: 10000 })]);
      }
    } catch (e) { err = String(e).slice(0, 100); }
    await page.waitForSelector('div.prg-building', { timeout: 15000 }).catch(() => {});
    const info = await listInfo(page);
    const body = info.buildings ? '' : await page.evaluate(() => document.body ? document.body.innerText.slice(0, 80) : '').catch(() => '');
    const ok = !!resp && resp.status() === 200 && info.buildings > 0;
    if (ok) fs.writeFileSync(`pages/L_${line}_${n}.html`, await page.content());
    const rec = { line, page: n, how, status: resp ? resp.status() : null, ok, secs: +((Date.now() - t0) / 1000).toFixed(1), referer: resp ? (resp.request().headers()['referer'] || null) : null, ...info, challenge: CHALLENGE.test(info.title || body || ''), err };
    log.push(rec); console.log(JSON.stringify(rec));
    if (!ok) { console.log(`STOP: blocked or empty at ${line} page ${n} (no retry, no bypass)`); stop = true; break; }
    n++;
  }
}
const okN = log.filter(x => x.ok);
console.log(JSON.stringify({ summary: { gap: GAP, loads: log.length, ok: okN.length, failed: log.length - okN.length, buildings: okN.reduce((a, x) => a + x.buildings, 0) } }));
fs.writeFileSync(`run_lists_${STAGE}.json`, JSON.stringify(log, null, 1));
await browser.close();
