// Menu stills (A4): navigate at 1280x720 (click coordinates are measured there), and for each screen switch the
// viewport to 1920x1080, take one still with PBR off, switch back. Output outside the repo (Mojang assets).
// usage: EAGLER_HTML=<hooked copy> EAGLER_SHOTS=<dir> node menus-capture.js
const L = require('./lib.js');
(async () => {
  const OUT = process.env.EAGLER_SHOTS;
  const { browser, page, click, skipFirstRun, setResolution, captureFrame, render } = await L.launch({ logFile: OUT + '/menus-raw.log' });
  const still = async (name) => {
    await setResolution(1920, 1080);
    await render(true); await page.waitForTimeout(2500);
    const r = await captureFrame(`${OUT}/${name}.png`, { settleClears: 12, stable: true, tolPct: 0.5 });
    await render(true); await setResolution(1280, 720); console.error(name, JSON.stringify(r));
  };
  await skipFirstRun();
  await page.waitForTimeout(3000);
  if (process.env.SHADERS === '1') {
    await click(485, 605, 3000); await still('menu-4-options');
    await click(878, 275, 3500); await still('menu-5-options-shaders');
    await browser.close(); console.error('DONE'); return;
  }
  await still('menu-1-title');
  await click(640, 353, 4000);                         // Singleplayer
  await still('menu-2-singleplayer-worldlist');
  await click(875, 593, 4000);                         // Create New World (opens the create-world dialog, see enterWorld)
  await still('menu-3-create-world-a');
  await click(640, 329, 4000);
  await still('menu-3-create-world-b');
  await browser.close(); console.error('DONE');
})().catch((e) => { console.error('FAILED', e); process.exit(1); });
