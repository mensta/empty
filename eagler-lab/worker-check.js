// R16: is the integrated server really a separate Web Worker, and does it keep real time while the page clock is held?
// Also lists every network request / WebSocket / Worker the page makes (privacy: does the offline file phone home?).
const L = require('./lib.js');
(async () => {
  const net = [], sockets = [], workers = [];
  const t0 = Date.now();
  const lib = await L.launch({ shotTimeout: 120000, beforeGoto: async (page) => {
    page.on('request', (r) => { const u = r.url(); if (!/^(file|data|blob):/.test(u)) net.push({ ms: Date.now() - t0, type: r.resourceType(), host: new URL(u).host, method: r.method() }); });
    page.on('websocket', (ws) => sockets.push({ ms: Date.now() - t0, url: ws.url().replace(/\?.*/, '') }));
    page.on('worker', (w) => workers.push({ ms: Date.now() - t0, scheme: w.url().split(':')[0], w }));
  } });
  const { browser, page, rawLogs, enterWorld, freezeWorld, render, vtEnable, vtDisable } = lib;
  const log = (...a) => console.error(...a);
  await render(false);
  log('workers before world:', workers.length);
  await enterWorld('eagler'); await freezeWorld({ time: 6000 });
  log('workers after world:', page.workers().length, 'created:', JSON.stringify(workers.map((w) => ({ ms: w.ms, scheme: w.scheme }))));
  for (const w of page.workers()) {
    const info = await w.evaluate(() => ({ scope: self.constructor.name, hasWindow: typeof window, hasImportScripts: typeof importScripts, now: Math.round(performance.now()) }));
    log(' worker', w.url().slice(0, 40), JSON.stringify(info));
  }
  log('zeus cloud state in page:', await page.evaluate(() => (window.__zeusCloud ? JSON.stringify(window.__zeusCloud.state) : 'window.__zeusCloud not created')));
  // server ticks while the PAGE clock is held
  const gt = async () => { const n = rawLogs.length; await lib.chat('/time query gametime'); const line = rawLogs.slice(n).find((x) => /\[CHAT\].*\d{3,}/.test(x)); if (!line) return null;
    const m = /\[(\d\d):(\d\d):(\d\d)\+(\d+)\]/.exec(line); const wall = ((+m[1] * 60 + +m[2]) * 60 + +m[3]) * 1000 + +m[4]; return { ticks: +/(\d{3,})/.exec(line.replace(/^.*?\[CHAT\]/, ''))[1], wall }; };
  const g0 = await gt();
  const srv = page.workers()[0];
  await vtEnable();
  const w0 = srv ? await srv.evaluate(() => performance.now()) : null; const p0 = await page.evaluate(() => performance.now());
  await page.waitForTimeout(20000);
  const w1 = srv ? await srv.evaluate(() => performance.now()) : null; const p1 = await page.evaluate(() => performance.now());
  log(`while the page clock is held for 20 s of wall time: page performance.now moved ${(p1 - p0).toFixed(0)} ms; worker performance.now moved ${w1 === null ? 'n/a' : (w1 - w0).toFixed(0)} ms`);
  await vtDisable(); await page.waitForTimeout(3000);
  const g1 = await gt();
  if (g0 && g1) log(`server game time: ${g0.ticks} -> ${g1.ticks} (+${g1.ticks - g0.ticks}) over ${((g1.wall - g0.wall) / 1000).toFixed(1)} s => ${((g1.ticks - g0.ticks) / ((g1.wall - g0.wall) / 1000)).toFixed(2)} ticks/s across the pause`);
  const byHost = {}; for (const r of net) { const k = `${r.host} ${r.type} ${r.method}`; byHost[k] = (byHost[k] || 0) + 1; }
  log('network requests (non file/data/blob):', net.length, JSON.stringify(byHost)); log('WebSockets opened:', sockets.length, JSON.stringify(sockets));
  await browser.close(); log('DONE');
})().catch((e) => { console.error('FAILED', e); process.exit(1); });
