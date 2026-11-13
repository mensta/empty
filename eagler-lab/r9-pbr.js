// R9: turn on the built-in "High Performance PBR" shader pack via Options > Shaders, then see whether it
// really runs: shader programs compiled, WebGL extensions requested, errors, frame cost, screenshots.
const L = require('./lib.js');
const fs = require('fs');
(async () => {
  const { browser, page, logs, click, shot, chat, glStats, skipFirstRun, enterWorld } = await L.launch();
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
  const timeline = [];
  for (const wait of [5000, 15000, 30000]) {
    await page.waitForTimeout(wait);
    const s = await page.evaluate(() => ({ t: Math.round(performance.now() / 1000), programs: window.__gl.createdPrograms, sources: window.__gl.shaders.length }));
    timeline.push(s); await shot(`51-pbr-t${timeline.length}`);
  }
  await page.evaluate(() => window.__gl.reset());
  await page.waitForTimeout(12000);
  const g = await glStats();
  await page.keyboard.press('F1'); await page.keyboard.press('F3'); await page.waitForTimeout(3000);
  await page.screenshot({ path: process.env.EAGLER_SHOTS + '/52-pbr-f3.png', clip: { x: 0, y: 28, width: 520, height: 30 } });
  await shot('53-pbr-f3-full');
  const gl = await page.evaluate(() => ({ shaders: window.__gl.shaders, programs: window.__gl.createdPrograms, ext: window.__gl.extensions }));
  const flagCount = {}; for (const s of gl.shaders) for (const f of s.flags) flagCount[f] = (flagCount[f] || 0) + 1;
  const sizes = gl.shaders.map((s) => s.n).sort((a, b) => b - a).slice(0, 8);
  console.log(JSON.stringify({ before, timeline, window12s: g, programs: gl.programs, sources: gl.shaders.length, flagCount, biggestSources: sizes,
    extensions: [...new Map(gl.ext).entries()] }, null, 1));
  console.log('LOG shader/gl/error lines:'); console.log(logs.filter((l) => /shader|pbr|gbuffer|error|fail|warn.*gl|framebuffer|extension/i.test(l) && !/does not exist/.test(l)).slice(-25).join('\n'));
  fs.writeFileSync(process.env.OUT || 'r9.json', JSON.stringify(gl));
  await browser.close();
})();
