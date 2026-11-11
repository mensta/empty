// 1) measure the WebGL draw gate  2) timeline of a client-side position write vs the server.
const L = require('./lib.js');

(async () => {
  const { browser, page, logs, chat, render, glStats, enterWorld, shot } = await L.launch();
  await enterWorld();
  await chat('/gamemode spectator');
  await chat('/tp @p 100.5 100 200.5 0 0');
  await page.waitForTimeout(2500);

  // --- position write timeline: one write, then poll with short evaluates (hang-safe), render stays ON ---
  await page.evaluate(() => {
    const e = window.__eagMC().bR, bb = e.dz;
    const w = bb.cL - bb.cG, h = bb.cI - bb.b4;
    const x = e.D + 5, y = e.J, z = e.E;
    bb.cG = x - w / 2; bb.cL = x + w / 2; bb.b4 = y; bb.cI = y + h; bb.cF = z - w / 2; bb.cM = z + w / 2;
    e.D = e.fS = e.mT = x; e.J = e.gr = e.l2 = y; e.E = e.fT = e.mU = z;
    window.__t0 = performance.now(); window.__wrote = x;
  });
  const t0 = Date.now(); const rows = []; const seen = new Set();
  while (Date.now() - t0 < 4000) {
    const r = await Promise.race([
      page.evaluate(() => { const e = window.__eagMC().bR; return [Math.round(performance.now() - window.__t0), +e.D.toFixed(2), +e.cG.toFixed(2)]; }),
      new Promise((res) => setTimeout(() => res(null), 3000)),
    ]);
    if (!r) { console.log('page unresponsive for >3s'); break; }
    const k = r[1] + '/' + r[2]; if (!seen.has(k)) { seen.add(k); rows.push(r); }
  }
  console.log('TIMELINE [ms since write, posX, aabb.minX]  (written posX = start+5)');
  for (const r of rows) console.log(' ', JSON.stringify(r));
  console.log('SERVER/CLIENT LOG lines mentioning movement:');
  console.log(logs.filter((l) => /moved|wrongly|too quickly|teleport|IntegratedServer.*WARN/i.test(l)).slice(-10).join('\n') || '(none)');
  await browser.close();
})();
