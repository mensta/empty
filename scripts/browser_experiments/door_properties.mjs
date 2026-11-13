// DOOR room pages (photos, deposit, renewal fee, guarantor) for the URLs in the JSON array given as argv[2].
// Images are blocked by hm_common.mjs, so photo counts come from the alt texts. Env: OUT (default ./pages/door_p), GAP (default 4).
import { open, sleep, CHALLENGE } from './hm_common.mjs';
import fs from 'node:fs';
const urls = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const OUT = process.env.OUT || './pages/door_p', GAP = Number(process.env.GAP || 4) * 1000;
fs.mkdirSync(OUT, { recursive: true });
const { browser, newPage } = await open();
const page = await newPage();
for (const u of urls) {
  const id = u.split('/').pop(); const file = `${OUT}/${id}.html`;
  if (fs.existsSync(file)) continue;
  const resp = await page.goto(u, { waitUntil: 'domcontentloaded', timeout: 30000 }).catch(() => null);
  await sleep(1200);
  const html = await page.content();
  if (!resp || resp.status() !== 200 || CHALLENGE.test(html.slice(0, 3000))) { console.log('STOP', u, resp && resp.status()); break; }
  fs.writeFileSync(file, html); console.log('ok', id);
  await sleep(GAP);
}
await browser.close();
