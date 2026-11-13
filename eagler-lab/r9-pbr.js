// R9: turn on the built-in "High Performance PBR" shader pack via Options > Shaders, then see whether it
// really runs: shader programs compiled, WebGL extensions requested, errors, frame cost, screenshots.
const L = require('./lib.js');
const fs = require('fs');
(async () => {
  const { browser, page, logs, click, shot, chat, glStats, skipFirstRun, enterWorld } = await L.launch({ shotTimeout: 240000 });
  await skipFirstRun();
  await click(485, 605, 3000);            // Options
  await click(878, 275, 3500);            // Shaders...
  await click(400, 659, 2500);            // Enable Shaders: No -> Yes
  await shot('50-shaders-enabled');
  await click(878, 659, 12000);           // Done (shaders) -> "Refreshing Resources... Please Wait." (swallows clicks)
  await shot('50b-after-refresh');
  await click(640, 653, 4000);            // Done (options) -> title
  await shot('50c-title');
  const before = await page.evaluate(() => ({ programs: window.__gl.createdPrograms, shaders: window.__gl.shaders.length }));
  await enterWorld('eagler', { first: false });
  await chat('/gamemode spectator'); await chat('/tp @p 100.5 100 200.5 0 0');
  await page.keyboard.press('F1');
  // Hang-safe sampling: every evaluate is raced against a timeout; a miss means the main thread was
  // blocked for that long (one PBR frame under software GL can exceed it).
  const probe = async (ms) => Promise.race([
    page.evaluate(() => ({ t: Math.round(performance.now()), programs: window.__gl.createdPrograms, sources: window.__gl.shaders.length, clears: window.__gl.frames, passed: window.__gl.passed })),
    new Promise((res) => setTimeout(() => res(null), ms)),
  ]);
  const timeline = []; const t0 = Date.now();
  for (let i = 0; i < 14; i++) {                       // ~ 14 x 15 s
    await page.waitForTimeout(15000);
    const s = await probe(60000); timeline.push({ wall: Math.round((Date.now() - t0) / 1000), s });
    console.error('probe', i, JSON.stringify(s));
    if (i === 2 || i === 8) { try { await shot(`51-pbr-${i}`); } catch (e) { console.error('shot failed', String(e).slice(0, 80)); } }
  }
  const g = null;
  try { await page.keyboard.press('F1'); await page.keyboard.press('F3'); await page.waitForTimeout(5000); await shot('53-pbr-f3-full'); } catch (e) { console.error('f3 shot failed'); }
  const gl = await page.evaluate(() => ({ shaders: window.__gl.shaders, programs: window.__gl.createdPrograms, ext: window.__gl.extensions }));
  const flagCount = {}; for (const s of gl.shaders) for (const f of s.flags) flagCount[f] = (flagCount[f] || 0) + 1;
  const sizes = gl.shaders.map((s) => s.n).sort((a, b) => b - a).slice(0, 8);
  console.log(JSON.stringify({ before, timeline, programs: gl.programs, sources: gl.shaders.length, flagCount, biggestSources: sizes,
    extensions: [...new Map(gl.ext).entries()] }, null, 1));
  console.log('LOG shader/gl/error lines:'); console.log(logs.filter((l) => /shader|pbr|gbuffer|error|fail|warn.*gl|framebuffer|extension/i.test(l) && !/does not exist/.test(l)).slice(-25).join('\n'));
  fs.writeFileSync(process.env.OUT || 'r9.json', JSON.stringify(gl));
  await browser.close();
})();
