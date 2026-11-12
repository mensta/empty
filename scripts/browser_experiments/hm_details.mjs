// Pass 2: walk the list pages again by clicking "next"; on each page, open the wanted rooms by CLICKING their links (they open in a new tab).
import { open, fs, sleep, GAP, CHALLENGE, listUrl, listInfo } from './hm_common.mjs';
const targets = JSON.parse(fs.readFileSync('targets.json', 'utf8'));
const LIMIT = Number(process.env.LIMIT || 1e9);
const { browser, ctx, newPage } = await open();
const page = await newPage();
const log = []; let stop = false, first = true, opened = 0;
const idOf = u => u.replace(/\/$/, '').split('/').pop();
for (const line of ['toyoko', 'meguro']) {
  if (stop) break;
  const todo = new Set(targets.filter(t => t.line === line).map(t => idOf(t.url)));
  if (!todo.size) continue;
  let n = 1;
  while (todo.size && !stop && opened < LIMIT) {
    if (!first) await sleep(GAP * 1000);
    first = false;
    let resp = null;
    try {
      if (n === 1) resp = await page.goto(listUrl(line), { waitUntil: 'domcontentloaded', timeout: 45000 });
      else {
        const next = page.locator('a', { hasText: /^次[へヘ]$/ }).last();
        if (await next.count() === 0) { console.log(`${line}: end of list, ${todo.size} targets not found on any page`); break; }
        [resp] = await Promise.all([page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 45000 }), next.click({ timeout: 10000 })]);
      }
    } catch (e) { console.log('list nav error', String(e).slice(0, 100)); stop = true; break; }
    await page.waitForSelector('div.prg-building', { timeout: 15000 }).catch(() => {});
    const info = await listInfo(page);
    if (!(resp && resp.status() === 200 && info.buildings > 0)) { console.log(`STOP: list ${line} p${n} blocked/empty (status ${resp && resp.status()})`); stop = true; break; }
    console.log(JSON.stringify({ list: line, page: n, buildings: info.buildings, remaining: todo.size }));
    for (const id of [...todo]) {
      const a = page.locator(`table.unitSummary tr a.prg-detailAnchor[href*="${id}"]`).first();
      if (await a.count() === 0) continue;
      await sleep(GAP * 1000);
      const t0 = Date.now(); let ok = false, title = null, size = 0, err = null;
      try {
        const [np] = await Promise.all([ctx.waitForEvent('page', { timeout: 20000 }), a.click({ timeout: 10000 })]);
        await np.waitForLoadState('domcontentloaded', { timeout: 45000 });
        await np.waitForSelector('th', { timeout: 15000 }).catch(() => {});
        const html = await np.content(); title = (await np.title()).slice(0, 40); size = html.length;
        ok = html.includes('建物構造') && !CHALLENGE.test(title);
        if (ok) fs.writeFileSync(`details/${id}.html`, html);
        await np.close();
      } catch (e) { err = String(e).slice(0, 100); }
      opened++; todo.delete(id);
      const rec = { detail: id, line, listPage: n, ok, secs: +((Date.now() - t0) / 1000).toFixed(1), title, size, err };
      log.push(rec); console.log(JSON.stringify(rec));
      if (!ok) { console.log(`STOP: detail blocked/failed (${id}) (no retry, no bypass)`); stop = true; break; }
      if (opened >= LIMIT) break;
    }
    n++;
  }
}
const okN = log.filter(x => x.ok);
console.log(JSON.stringify({ summary: { gap: GAP, detailsOpened: log.length, ok: okN.length, failed: log.length - okN.length } }));
fs.writeFileSync('run_details.json', JSON.stringify(log, null, 1));
await browser.close();
