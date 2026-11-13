// Boot clip (A1 of the footage request): Playwright screen-recording of the REAL page load (not frame-stepped:
// the boot depends on real async work), the raw console log, and the title screen as virtual-clock stepped frames.
// usage: EAGLER_HTML=<hooked copy> EAGLER_SHOTS=<dir outside repo> [TITLE_FRAMES=120] [FPS=30] node boot-capture.js
const L = require('./lib.js');
const fs = require('fs');
const OUT = process.env.EAGLER_SHOTS, FRAMES = +(process.env.TITLE_FRAMES || 120), FPS = +(process.env.FPS || 30);
(async () => {
  fs.mkdirSync(OUT + '/rec', { recursive: true });
  // MODE=rec: record the real boot and stop at the title screen. MODE=frames: no recording (it slows the 1080p frames
  // ~2x), skip the countdown and step the title screen.
  const MODE = process.env.MODE || 'rec';
  const lib = await L.launch({ skipCountdown: false, logFile: OUT + `/boot-raw-${MODE}.log`, ...(MODE === 'rec' ? { recordVideo: { dir: OUT + '/rec', size: { width: 1280, height: 720 } } } : {}) });
  const { page, context, browser, t0, tGoto, click, skipFirstRun, setResolution, vtEnable, vtDisable, vtStep, captureFrame, render } = lib;
  const marks = { navStartMs: tGoto }; const mark = (k) => { marks[k] = Date.now() - t0; console.error('mark', k, marks[k]); };
  await page.waitForTimeout(1500);
  mark('skipCountdownClick'); await page.click('#skipCountdown');
  await page.waitForTimeout(9000); mark('afterBootWait');
  await skipFirstRun(); mark('afterFirstRunScreens');
  await page.waitForTimeout(3000); mark('titleSettled');
  fs.writeFileSync(OUT + `/boot-marks-${MODE}.json`, JSON.stringify(marks, null, 1));
  if (MODE === 'rec') { const vpath = await page.video().path(); await context.close(); await browser.close(); console.error('video', vpath, 'DONE'); return; }
  // stepped title frames at 1080p (panorama rotation is driven by client ticks, which follow the virtual clock)
  await setResolution(1920, 1080);
  await render(false);
  await vtEnable();
  const dir = OUT + '/title-frames'; fs.mkdirSync(dir, { recursive: true });
  for (let i = 0; i < FRAMES; i++) {
    await vtStep(1000 / FPS, { minClears: 4 });
    await captureFrame(`${dir}/t-${String(i).padStart(5, '0')}.png`, { settleClears: 4, stable: false });
  }
  await vtDisable();
  await context.close(); await browser.close();
  console.error('DONE');
})().catch((e) => { console.error('FAILED', e); process.exit(1); });
