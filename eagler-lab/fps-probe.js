// What does the game's own F3 "N fps" say right after a render-OFF stretch?
// The game updates that number once a second inside its loop (independent of GL), so
// turning rendering back ON and grabbing the F3 line immediately shows the last OFF-second value.
const L = require('./lib.js');
const OUT = process.env.EAGLER_SHOTS || '.';
(async () => {
  const { browser, page, chat, render, enterWorld } = await L.launch();
  await enterWorld();
  await chat('/gamemode spectator'); await chat('/tp @p 100.5 100 200.5 0 0'); await page.waitForTimeout(3000);
  await page.keyboard.press('F3'); await page.waitForTimeout(4000);
  const clip = { x: 0, y: 28, width: 520, height: 30 };
  const grab = async (name) => { const t = Date.now(); await page.screenshot({ path: `${OUT}/${name}.png`, clip }); return Date.now() - t; };
  for (let i = 0; i < 3; i++) { await grab('fps-on-' + i); await page.waitForTimeout(1200); }
  for (let rep = 0; rep < 3; rep++) {
    await render(false); await page.waitForTimeout(8000);
    await render(true);
    const stamps = [];
    for (let i = 0; i < 5; i++) stamps.push(await grab(`fps-after-off${rep}-${i}`));
    console.log('rep', rep, 'screenshot ms', stamps.join(','));
    await page.waitForTimeout(4000);
  }
  await browser.close();
})();
