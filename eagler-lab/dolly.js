// Does a paced camera path survive? small steps, render gated off, server oracle at the end.
const L = require('./lib.js');
(async () => {
  const { browser, page, logs, chat, render, enterWorld, getState, setCamera, shot } = await L.launch();
  await enterWorld();
  await chat('/gamemode spectator');
  await chat('/tp @p 100.5 100 200.5 0 0');
  await page.waitForTimeout(2500);
  const start = await getState(); console.log('start', JSON.stringify(start));
  await render(false);
  const STEPS = 80, DX = 0.25;                       // 20 blocks total, 0.25 block per step
  for (let i = 1; i <= STEPS; i++) {
    await setCamera(start[0] + DX * i, start[1] + 0.05 * i, start[2], (90 * i) / STEPS, 10);
    await page.waitForTimeout(50);
  }
  console.log('end   (expected x=' + (start[0] + DX * STEPS) + ')', JSON.stringify(await getState()));
  await page.waitForTimeout(6000);
  console.log('+6s   ', JSON.stringify(await getState()));
  await render(true);
  await chat('/tp @p ~ ~ ~');                         // echoes the server-held position
  console.log('server', logs.filter((l) => /Teleported/.test(l)).slice(-1)[0]);
  console.log('client', JSON.stringify(await getState()));
  await page.waitForTimeout(1500); await shot('30-dolly-final');
  await browser.close();
})();
