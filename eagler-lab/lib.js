// Shared helpers: launch the (locally downloaded) Eaglercraft HTML in headless Chromium,
// walk through the first-run screens, create a cheat-enabled fixed-seed world.
const { chromium } = require('playwright');
const fs = require('fs');

// Path to the Eaglercraft single-file HTML. Not shipped in this repo (Mojang assets).
const DEFAULT_HTML = process.env.EAGLER_HTML;
const GATE = fs.readFileSync(__dirname + '/gl-gate.js', 'utf8');

exports.launch = async ({ html = DEFAULT_HTML, shots = process.env.EAGLER_SHOTS || '.', gate = true } = {}) => {
  if (!html) throw new Error('set EAGLER_HTML to the Eaglercraft html path');
  const browser = await chromium.launch({
    args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
  });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  const logs = [];
  page.on('console', (m) => { const t = m.text(); if (!/does not exist|OptiFine/.test(t)) logs.push(t.slice(0, 240)); });
  page.on('pageerror', (e) => logs.push('[pageerror] ' + String(e).slice(0, 300)));
  if (gate) await page.addInitScript(GATE);
  await page.goto('file://' + html);
  await page.click('#skipCountdown');
  await page.waitForTimeout(9000);

  // Game polls input per frame; with software GL a press must be held across frames.
  const click = async (x, y, wait = 2500) => {
    await page.mouse.move(x, y); await page.waitForTimeout(600);
    await page.mouse.down(); await page.waitForTimeout(500); await page.mouse.up();
    await page.waitForTimeout(wait);
  };
  const shot = (name) => page.screenshot({ path: `${shots}/${name}.png` });
  const chat = async (cmd) => {
    await page.keyboard.press('t'); await page.waitForTimeout(700);
    await page.keyboard.type(cmd, { delay: 30 });
    await page.keyboard.press('Enter'); await page.waitForTimeout(1500);
  };
  // render on/off at the WebGL command level
  const render = (on) => page.evaluate((v) => { window.__gl.on = !!v; }, on);
  const glStats = () => page.evaluate(() => { const g = window.__gl; return { on: g.on, passed: g.passed, skipped: g.skipped, frames: g.frames }; });

  // 1.8.8 first-run screens + fixed-seed cheat world (coordinates measured at 1280x720)
  const enterWorld = async (seed = 'eagler') => {
    await click(640, 563); await click(640, 653, 5000); await click(640, 575, 4000); // warnings, profile, username
    await click(640, 353, 4000); await click(875, 593, 4000); await click(640, 329, 4000); // SP > create
    await click(640, 590, 3000);                       // More World Options
    await click(640, 210, 500); await page.keyboard.type(seed, { delay: 80 });
    await click(400, 482, 800);                        // Allow Cheats
    await click(640, 590, 2000);                       // Done
    await click(400, 665, 25000);                      // Create New World
    await page.waitForTimeout(15000);
  };
  // Build-specific minified field names (EaglercraftX 1.8-u53 JS build). Found empirically, see NOTES.
  //   mc = window.__eagMC() (needs the hook patch), mc.bR = thePlayer, mc.bR.dz = bounding box
  //   D/J/E = posX/Y/Z, fS/gr/fT = lastTickPos, mT/l2/mU = prevPos, bN/cR = yaw/pitch, hq/ip = prevYaw/prevPitch
  //   AABB: cG/b4/cF = min x/y/z, cL/cI/cM = max x/y/z
  const getState = () => page.evaluate(() => {
    const e = window.__eagMC().bR; return [e.D, e.J, e.E, e.bN, e.cR].map((v) => +v.toFixed(3));
  });
  const setCamera = (x, y, z, yaw, pitch) => page.evaluate(([x, y, z, yaw, pitch]) => {
    const e = window.__eagMC().bR, bb = e.dz, w = bb.cL - bb.cG, h = bb.cI - bb.b4;
    bb.cG = x - w / 2; bb.cL = x + w / 2; bb.b4 = y; bb.cI = y + h; bb.cF = z - w / 2; bb.cM = z + w / 2;
    e.D = e.fS = e.mT = x; e.J = e.gr = e.l2 = y; e.E = e.fT = e.mU = z;
    e.bN = e.hq = yaw; e.cR = e.ip = pitch;
  }, [x, y, z, yaw, pitch]);
  return { browser, page, logs, click, shot, chat, render, glStats, enterWorld, getState, setCamera };
};
