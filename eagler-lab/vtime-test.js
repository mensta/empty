// (b) Can the game's time be driven frame by frame? Checks which clock the game reads and whether the
// client tick count follows the virtual clock. Output: JSON-ish lines on stderr.
const L = require('./lib.js');
(async () => {
  const OUT = process.env.EAGLER_SHOTS;
  const lib = await L.launch({ shotTimeout: 240000, logFile: OUT + '/vt-console.log' });
  const { browser, page, rawLogs, enterWorld, freezeWorld, dismissHints, hideHud, teleport, captureFrame, vtEnable, vtDisable, vtStep, diffPct } = lib;
  await enterWorld('eagler'); await freezeWorld({ time: 6000 }); await dismissHints(); await hideHud();
  await teleport(100.5, 100, 200.5, 45, 10); await page.waitForTimeout(15000);
  const ticks = () => page.evaluate(() => { const mc = window.__eagMC(); return mc.bR.ke; });
  const calls = () => page.evaluate(() => ({ ...window.__vt.calls }));
  const log = (...a) => console.error(...a);

  let a = await ticks(); await page.waitForTimeout(3000); let b = await ticks();
  log('REAL clock, 3 s wall: client ticks +' + (b - a));

  await vtEnable();
  const c0 = await calls();
  a = await ticks(); await page.waitForTimeout(3000); b = await ticks();
  const c1 = await calls();
  log('VIRTUAL clock paused, 3 s wall: client ticks +' + (b - a), '| clock reads: performance.now', c1.perf - c0.perf, 'Date.now', c1.date - c0.date);

  const before = await captureFrame(OUT + '/vt-s0.png', { stable: false, settleClears: 20, keepOn: false });
  for (const [steps, ms] of [[30, 1000 / 30], [60, 1000 / 60], [15, 1000 / 15]]) {
    const t0 = Date.now(); a = await ticks(); const cl = [];
    for (let i = 0; i < steps; i++) cl.push(await vtStep(ms));
    b = await ticks();
    log(`${steps} steps x ${ms.toFixed(2)} ms (= 1.000 virtual s): client ticks +${b - a}; clears/step avg ${(cl.reduce((x, y) => x + y, 0) / steps).toFixed(1)}; wall ${((Date.now() - t0) / 1000).toFixed(1)} s`);
  }
  // visual check: one virtual second later (30+60+15 steps = 3 virtual s) the clouds must have moved
  const after = await captureFrame(OUT + '/vt-s1.png', { stable: false, settleClears: 20, keepOn: false });
  const fs = require('fs');
  log('sky region (top 30%) differing % after 3 virtual s:', (await diffPct(fs.readFileSync(OUT + '/vt-s0.png'), fs.readFileSync(OUT + '/vt-s1.png'), [0, 0.3])).toFixed(2),
      '| terrain region (bottom 55%):', (await diffPct(fs.readFileSync(OUT + '/vt-s0.png'), fs.readFileSync(OUT + '/vt-s1.png'), [0.45, 1])).toFixed(2));
  // does the game stay connected while its clock is held? (server keep-alive)
  await page.waitForTimeout(20000);
  log('after 20 s wall with clock held: client ticks', (await ticks()), '| disconnect/timeout lines:', rawLogs.filter((l) => /timed out|disconnect|lost connection/i.test(l)).length);
  await vtDisable(); await page.waitForTimeout(3000);
  a = await ticks(); await page.waitForTimeout(3000); b = await ticks();
  log('clock released, 3 s wall: client ticks +' + (b - a));
  await browser.close();
})().catch((e) => { console.error('FAILED', e); process.exit(1); });
