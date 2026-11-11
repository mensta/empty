// 1) measure the WebGL draw gate  2) timeline of a client-side position write vs the server.
const L = require('./lib.js');

(async () => {
  const { browser, page, logs, chat, render, glStats, enterWorld, shot } = await L.launch();
  await enterWorld();
  await chat('/gamemode spectator');
  await chat('/tp @p 100.5 100 200.5 0 0');
  await page.waitForTimeout(2500);

  // --- 1) draw gate ---
  const measure = async (on, ms) => {
    await render(on);
    await page.evaluate(() => window.__gl.reset());
    await page.waitForTimeout(ms);
    const s = await glStats();
    return { on, seconds: ms / 1000, frames_per_s: +(s.frames / (ms / 1000)).toFixed(1), passed_per_s: Math.round(s.passed / (ms / 1000)), skipped_per_s: Math.round(s.skipped / (ms / 1000)) };
  };
  console.log('GATE render ON ', JSON.stringify(await measure(true, 6000)));
  console.log('GATE render OFF', JSON.stringify(await measure(false, 6000)));
  await render(true);

  // --- 2) position write timeline (render off => faster ticks, finer sampling) ---
  await render(false);
  const timeline = await page.evaluate(() => new Promise((res) => {
    const e = window.__eagMC().bR, bb = e.dz;
    const w = bb.cL - bb.cG, h = bb.cI - bb.b4;
    const x = e.D + 5, y = e.J, z = e.E;
    const samples = []; let t0;
    const write = () => {
      bb.cG = x - w / 2; bb.cL = x + w / 2; bb.b4 = y; bb.cI = y + h; bb.cF = z - w / 2; bb.cM = z + w / 2;
      e.D = e.fS = e.mT = x; e.J = e.gr = e.l2 = y; e.E = e.fT = e.mU = z;
    };
    write(); t0 = performance.now();
    const id = setInterval(() => {
      samples.push([Math.round(performance.now() - t0), +e.D.toFixed(2), +e.cG.toFixed(2)]);
      if (performance.now() - t0 > 1500) { clearInterval(id); res(samples); }
    }, 5);
  }));
  console.log('TIMELINE [ms, posX, aabb.minX] (written x = start+5)');
  const first = timeline[0], seen = new Set();
  for (const s of timeline) { const k = s[1] + '/' + s[2]; if (!seen.has(k)) { seen.add(k); console.log(' ', JSON.stringify(s)); } }
  await render(true);
  await page.waitForTimeout(1500);
  console.log('SERVER/CLIENT LOG lines mentioning movement:');
  console.log(logs.filter((l) => /moved|wrongly|too quickly|teleport|IntegratedServer.*WARN/i.test(l)).slice(-10).join('\n') || '(none)');
  await browser.close();
})();
