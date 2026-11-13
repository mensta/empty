// DOOR building pages (for the structure: RC / steel / wood) of the building ids listed in the JSON file given as argv[2].
// Env: OUT (default ./pages/door_b), GAP (seconds, default 4). Stops at the first block.
import { open, sleep, CHALLENGE } from './hm_common.mjs';
import fs from 'node:fs';
const ids = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const OUT = process.env.OUT || './pages/door_b', GAP = Number(process.env.GAP || 4) * 1000;
fs.mkdirSync(OUT, { recursive: true });
const { browser, newPage } = await open();
const page = await newPage();
for (const id of ids) {
  const file = `${OUT}/${id}.html`;
  if (fs.existsSync(file)) continue;
  const resp = await page.goto('https://door.ac/buildings/' + id, { waitUntil: 'domcontentloaded', timeout: 30000 }).catch(() => null);
  await sleep(1200);
  const html = await page.content();
  if (!resp || resp.status() !== 200 || CHALLENGE.test(html.slice(0, 3000))) { console.log('STOP', id, resp && resp.status()); break; }
  fs.writeFileSync(file, html); console.log('ok', id);
  await sleep(GAP);
}
await browser.close();
