// R1: re-measure "render OFF is ~3.2x faster" with repeats, separating client ticks / frames / server ticks.
// R4: record which shader variants the game actually compiles (via gl-gate.js).
// Output: JSON on stdout (raw samples) so the definition of "speed-up" can be decided offline.
const L = require('./lib.js');
const fs = require('fs');

const ROUNDS = +(process.env.ROUNDS || 4);
const WINDOW_MS = +(process.env.WINDOW_MS || 12000);

(async () => {
  const { browser, page, logs, chat, render, glStats, enterWorld, shot } = await L.launch();
  await enterWorld();
  await chat('/gamemode spectator');
  await chat('/tp @p 100.5 100 200.5 0 0');
  await page.waitForTimeout(3000);

  // numeric int-like fields of Minecraft singleton and the player: used to find fps / tick counters offline
  const snap = () => page.evaluate(() => {
    const mc = window.__eagMC(), out = {};
    const grab = (o, p) => { for (const k of Object.keys(o)) { const v = o[k]; if (typeof v === 'number' && Number.isFinite(v)) out[p + '.' + k] = v; } };
    grab(mc, 'mc'); if (mc.bR) grab(mc.bR, 'pl');
    return out;
  });
  // server game time via "/time query gametime" -> chat line; timestamps come from the game's own log prefix
  const gameTime = async () => {
    const before = logs.length;
    await chat('/time query gametime');
    const line = logs.slice(before).find((l) => /\[CHAT\].*(\d{3,})/.test(l));
    if (!line) return null;
    const ts = /^\[(\d\d):(\d\d):(\d\d)\+(\d+)\]/.exec(line);
    const wall = ts ? ((+ts[1] * 60 + +ts[2]) * 60 + +ts[3]) * 1000 + +ts[4] : null;
    return { ticks: +/(\d{3,})/.exec(line.replace(/^\[[^\]]*\]/, ''))[1], wall, raw: line.slice(0, 120) };
  };

  await page.keyboard.press('F3'); await page.waitForTimeout(1500);
  await shot('40-f3-on-before');  // for matching the on-screen fps with a counter field offline
  const f3snap = await snap();

  const result = { rounds: [], f3snap, params: { ROUNDS, WINDOW_MS } };
  for (let r = 0; r < ROUNDS; r++) {
    for (const on of (r % 2 === 0 ? [true, false] : [false, true])) {   // alternate order to cancel drift
      await render(on);
      await page.evaluate(() => window.__gl.reset());
      const g0 = await gameTime(); const s0 = await snap(); const t0 = Date.now();
      const series = [];
      while (Date.now() - t0 < WINDOW_MS) { await page.waitForTimeout(1000); series.push({ t: Date.now() - t0, s: await snap() }); }
      const s1 = await snap(); const g1 = await gameTime(); const gl = await glStats();
      result.rounds.push({ round: r, render: on, ms: Date.now() - t0, g0, g1, gl, s0, series, s1 });
      if (r === 0) await shot(on ? '41-on' : '42-off');
      console.error(`round ${r} render=${on} gl=${JSON.stringify(gl)} gametime ${g0 && g0.ticks}->${g1 && g1.ticks}`);
    }
  }
  await render(true);
  result.shaders = await page.evaluate(() => ({ shaders: window.__gl.shaders, programs: window.__gl.createdPrograms, links: window.__gl.links }));
  fs.writeFileSync(process.env.OUT || 'measure-r1-r4.json', JSON.stringify(result));
  console.error('saved; shaders compiled:', result.shaders.shaders.length, 'programs:', result.shaders.programs);
  await browser.close();
})();
