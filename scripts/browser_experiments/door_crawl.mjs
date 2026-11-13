// DOOR (door.ac) list pages for Toyoko (404) and Meguro (406), Tokyo side, saved as HTML for door_parse.py.
// Same rules as the other experiments: UA/Client Hints say Chrome (hm_common.mjs), no stealth, no proxy,
// one request per GAP seconds, stop at the first block. door.ac/robots.txt has no restrictions (checked 2026-11-13).
// Env: SORT (default rent_asc: the order stays stable while paging; updated_desc shifts and gives duplicates/gaps),
//      OUT (default ./pages/door), GAP (seconds, default 4), MAXP (default 60).
// Filters mirror the repo conditions: 1LDK/2DK/2LDK, <= 19man incl. admin, <= 10 min walk, >= 25 m2 (refined later).
import { open, sleep, CHALLENGE } from './hm_common.mjs';
import fs from 'node:fs';
const GAP = Number(process.env.GAP || 4) * 1000, MAXP = Number(process.env.MAXP || 60);
const SORT = process.env.SORT || 'rent_asc', OUT = process.env.OUT || './pages/door';
const LINES = { toyoko: 404, meguro: 406 };
const base = id => 'https://door.ac/list?cond[prefectures][]=13&cond[lines][]=' + id +
  '&cond[layouts][]=15&cond[layouts][]=23&cond[layouts][]=25&cond[fee_max]=190000&cond[walk_time]=10&cond[included]=1&cond[sqmeter_min]=25&cond[sort]=' + SORT;
fs.mkdirSync(OUT, { recursive: true });
const { browser, newPage } = await open();
const page = await newPage();
let stop = false;
for (const [name, id] of Object.entries(LINES)) {
  let total = null;
  for (let p = 1; p <= MAXP && !stop; p++) {
    const file = `${OUT}/${name}_${String(p).padStart(3, '0')}.html`;
    if (fs.existsSync(file) && fs.statSync(file).size > 50000) { console.log('skip (have)', file); continue; }
    let resp;
    try { resp = await page.goto(base(id) + (p > 1 ? '&page=' + p : ''), { waitUntil: 'domcontentloaded', timeout: 30000 }); }
    catch (e) { console.log('STOP error', name, p, String(e.message).slice(0, 80)); stop = true; break; }
    await sleep(1500);
    const html = await page.content();
    if (resp.status() !== 200 || CHALLENGE.test(html.slice(0, 5000)) || /Just a moment|認証中/.test(await page.title())) { console.log('STOP blocked', name, p, resp.status()); stop = true; break; }
    const info = await page.evaluate(() => ({ b: document.querySelectorAll('.building-box').length, n: (document.body.innerText.match(/([\d,]+)\s*件/) || [])[1] }));
    if (info.b === 0) { console.log('end', name, p); break; }
    fs.writeFileSync(file, html);
    total = total || info.n;
    console.log(name, p, 'buildings', info.b, 'total', total);
    await sleep(GAP);
  }
  if (stop) break;
  await sleep(8000);
}
await browser.close();
