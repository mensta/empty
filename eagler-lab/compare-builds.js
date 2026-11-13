// R11: run ONE build (JS or WASM-GC) under identical conditions and record startup log, GL activity and fps.
// usage: LABEL=js|wasm EAGLER_HTML=<html> OUTDIR=<dir> node compare-builds.js     (no hook needed)
const L = require('./lib.js');
const fs = require('fs');
(async () => {
  const OUT = process.env.OUTDIR, label = process.env.LABEL;
  const lib = await L.launch({ shotTimeout: 240000, logFile: `${OUT}/${label}-console.log`, shots: OUT });
  const { browser, page, skipFirstRun, enterWorld, chat, render, glStats, shot } = lib;
  const cdp = await page.context().newCDPSession(page); await cdp.send('Performance.enable');
  const heap = async () => { const m = Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map((x) => [x.name, x.value])); return +(m.JSHeapUsedSize / 1048576).toFixed(0); };
  const res = { label, heapMB: {} };
  res.heapMB.afterLoad = await heap();
  await skipFirstRun(); await page.waitForTimeout(3000); res.heapMB.title = await heap(); await shot(`${label}-title`);
  await render(false); await enterWorld('eagler', { first: false });
  for (const c of ['/gamemode spectator', '/gamerule doDaylightCycle false', '/time set 6000', '/weather clear 1000000']) await chat(c);
  await page.keyboard.press('F1'); await page.waitForTimeout(1000); await page.keyboard.press('e'); await page.waitForTimeout(2500); await page.keyboard.press('e'); await page.waitForTimeout(2500);
  await page.waitForTimeout(20000);                       // let chunks load (gate off = fast frames)
  res.heapMB.inWorld = await heap();
  await render(true); await page.waitForTimeout(8000);   // settle
  const win = [];
  for (let i = 0; i < 3; i++) { await page.evaluate(() => window.__gl.reset()); await page.waitForTimeout(10000); const g = await glStats(); win.push({ clearsPerS: +(g.frames / 10).toFixed(1), cmdsPerS: Math.round(g.passed / 10) }); }
  res.glWindows10s = win; console.error('PROGRESS', JSON.stringify(res));
  await page.keyboard.press('F1'); await page.keyboard.press('F3'); await page.waitForTimeout(3500);
  const clip = { x: 0, y: 28, width: 520, height: 30 };
  for (let i = 0; i < 3; i++) { const t = Date.now(); await page.screenshot({ path: `${OUT}/${label}-fps-${i}.png`, clip, timeout: 240000 }); console.error('fps shot', i, 'took ms', Date.now() - t); await page.waitForTimeout(1500); }
  await shot(`${label}-world`);
  res.shaderPrograms = await page.evaluate(() => window.__gl.createdPrograms);
  res.extensions = await page.evaluate(() => window.__gl.extensions.map((e) => e[0] + (e[1] ? '' : '(denied)')));
  console.log(JSON.stringify(res));
  await browser.close();
})().catch((e) => { console.error('FAILED', e); process.exit(1); });
