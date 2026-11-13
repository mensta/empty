// Same-pose still for PBR on/off. PBR=1 enables the built-in shader pack from Options first.
// World setup runs with the draw gate OFF (fast, chat works even when PBR would run at ~1 fps);
// then rendering is switched back ON for enough frames to settle, and stills are grabbed.
// usage: PBR=0|1 EAGLER_HTML=... EAGLER_SHOTS=dir node ab-still.js
const L = require('./lib.js');
const PBR = process.env.PBR === '1';
const POSE = (process.env.POSE || '100.5,100,200.5,45,10').split(',').map(Number); // x,y,z,yaw,pitch
const SETTLE_MS = +(process.env.SETTLE_MS || (PBR ? 40000 : 10000));
(async () => {
  const { browser, page, click, shot, chat, render, glStats, skipFirstRun, enterWorld, getState, setCamera } = await L.launch({ shotTimeout: 240000 });
  const tag = PBR ? 'pbr' : 'plain';
  await skipFirstRun();
  if (PBR) {
    await click(485, 605, 3000); await click(878, 275, 3500); await click(400, 659, 2500); // Options > Shaders > Enable
    await click(878, 659, 12000);                                                          // Done (waits for "Refreshing Resources")
    await click(640, 653, 4000);                                                           // Done (options)
  }
  await render(false);                                   // keep menus/loading cheap
  await enterWorld('eagler', { first: false });
  for (const c of ['/gamemode spectator', '/gamerule doDaylightCycle false', '/time set 6000', '/weather clear 1000000',
                   `/tp @p ${POSE.join(' ')}`]) await chat(c);
  await page.keyboard.press('F1'); await page.waitForTimeout(1500);   // hide HUD
  await page.waitForTimeout(15000);                                    // let chunks load / toast & chat fade (gate still off)
  await setCamera(POSE[0], POSE[1], POSE[2], POSE[3], POSE[4]);
  console.error(tag, 'state before render', JSON.stringify(await getState()));
  await page.evaluate(() => window.__gl.reset());
  await render(true);
  await page.waitForTimeout(SETTLE_MS);
  const st = await glStats(); console.error(tag, 'frames settled: clears', st.frames, 'passed', st.passed);
  console.error(tag, 'state', JSON.stringify(await getState()));
  for (let i = 0; i < 2; i++) { const t = Date.now(); await shot(`ab-${tag}-${i}`); console.error(tag, 'shot', i, 'took ms', Date.now() - t); await page.waitForTimeout(6000); }
  await browser.close();
})();
