// Shared helpers: launch the (locally downloaded) Eaglercraft HTML in headless Chromium,
// walk through the first-run screens, create a cheat-enabled fixed-seed world, and capture frames.
//
// IMPORTANT about footage: the game runs on SwiftShader (software GL). Frames are drawn one at a time at
// whatever speed the CPU allows (~15 fps plain, ~1 fps with the PBR pack). Anything captured here is a
// sequence of stills; the speed of a video assembled from them is NOT the speed of the real game.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

// Path to the Eaglercraft single-file HTML (a hook-patched COPY, see patch-hook.js). Not shipped in this repo.
const DEFAULT_HTML = process.env.EAGLER_HTML;
const GATE = fs.readFileSync(__dirname + '/gl-gate.js', 'utf8');
const pad = (n, w = 5) => String(n).padStart(w, '0');

exports.launch = async ({
  html = DEFAULT_HTML, shots = process.env.EAGLER_SHOTS || '.', gate = true,
  viewport = { width: 1280, height: 720 }, shotTimeout = 30000,
  logFile = process.env.EAGLER_LOG || null,            // G3: full, timestamped, never filtered
} = {}) => {
  if (!html) throw new Error('set EAGLER_HTML to the Eaglercraft html path');
  const browser = await chromium.launch({
    args: ['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
  });
  const page = await browser.newPage({ viewport });

  // ---- G3: raw console log. Attached BEFORE goto, so the very first line is kept; no line is dropped
  //      or truncated; each line carries wall-clock ms (ISO) and ms since attach. `logs` keeps the old
  //      filtered/truncated view for existing scripts.
  const t0 = Date.now();
  const logs = [], rawLogs = [];
  const out = logFile ? fs.createWriteStream(logFile, { flags: 'w' }) : null;
  const rec = (type, text) => {
    const now = Date.now();
    const line = `${new Date(now).toISOString()} +${now - t0}ms [${type}] ${text}`;
    rawLogs.push(line); if (out) out.write(line + '\n');
  };
  page.on('console', (m) => { const t = m.text(); rec(m.type(), t); if (!/does not exist|OptiFine/.test(t)) logs.push(t.slice(0, 240)); });
  page.on('pageerror', (e) => { rec('pageerror', String(e)); logs.push('[pageerror] ' + String(e).slice(0, 300)); });
  page.on('requestfailed', (r) => rec('requestfailed', r.url().slice(0, 200)));

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
  const shot = (name) => page.screenshot({ path: `${shots}/${name}.png`, timeout: shotTimeout });
  const chat = async (cmd) => {
    await page.keyboard.press('t'); await page.waitForTimeout(700);
    await page.keyboard.type(cmd, { delay: 30 });
    await page.keyboard.press('Enter'); await page.waitForTimeout(1500);
  };
  // render on/off at the WebGL command level
  const render = (on) => page.evaluate((v) => { window.__gl.on = !!v; }, on);
  const glStats = () => page.evaluate(() => { const g = window.__gl; return { on: g.on, passed: g.passed, skipped: g.skipped, frames: g.frames, uploads: g.uploads }; });
  // every evaluate that may land on a busy main thread is raced against a timeout
  const probe = (fn, arg, ms = 60000) => Promise.race([page.evaluate(fn, arg), new Promise((r) => setTimeout(() => r(null), ms))]);

  // 1.8.8 first-run screens + fixed-seed cheat world (coordinates measured at 1280x720)
  // first-run screens appear in a slightly varying order, so run the (harmless-on-title) pass twice
  const skipFirstRun = async () => {
    for (let pass = 0; pass < 2; pass++) { await click(640, 563); await click(640, 653, 5000); await click(640, 575, 4000); }
  };
  const enterWorld = async (seed = 'eagler', { first = true } = {}) => {
    if (first) await skipFirstRun();
    await click(640, 353, 4000); await click(875, 593, 4000); await click(640, 329, 4000); // SP > create
    await click(640, 590, 3000);                       // More World Options
    await click(640, 210, 500); await page.keyboard.type(seed, { delay: 80 });
    await click(400, 482, 800);                        // Allow Cheats
    await click(640, 590, 2000);                       // Done
    await click(400, 665, 25000);                      // Create New World
    await page.waitForTimeout(15000);
  };
  // Build-specific minified field names (EaglercraftX 1.8-u53 JS build). Found empirically, see FINDINGS.md.
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

  // ---- G10: wait until chunks stop loading. Heuristic: no gl.bufferData/bufferSubData for `quietMs`.
  const waitChunks = async ({ quietMs = 3000, minMs = 1500, maxMs = 120000 } = {}) => {
    const t = Date.now(); await page.waitForTimeout(minMs);
    while (Date.now() - t < maxMs) {
      const r = await probe(() => ({ now: performance.now(), last: window.__gl.lastUpload }), null, 30000);
      if (r && r.now - r.last >= quietMs) return { waitedMs: Date.now() - t, quiet: true };
      await page.waitForTimeout(500);
    }
    return { waitedMs: Date.now() - t, quiet: false };
  };

  // ---- G11: HUD / hints / resolution
  let hudHidden = false;
  const hideHud = async () => { if (!hudHidden) { await page.keyboard.press('F1'); hudHidden = true; await page.waitForTimeout(1000); } };
  const showHud = async () => { if (hudHidden) { await page.keyboard.press('F1'); hudHidden = false; await page.waitForTimeout(1000); } };
  // The "Press 'E' to open your inventory" toast stays until the inventory has been opened once.
  const dismissHints = async () => { await page.keyboard.press('e'); await page.waitForTimeout(2500); await page.keyboard.press('e'); await page.waitForTimeout(2500); };
  // Menu click coordinates assume 1280x720, so change resolution only AFTER enterWorld().
  const setResolution = async (w, h) => { await page.setViewportSize({ width: w, height: h }); await page.waitForTimeout(4000); };

  // ---- G2 helpers: a world that holds still, and camera moves the server will accept
  const freezeWorld = async ({ time = 6000, weather = 'clear' } = {}) => {
    for (const c of ['/gamemode spectator', '/gamerule doDaylightCycle false', '/gamerule doMobSpawning false',
      `/time set ${time}`, `/weather ${weather} 1000000`, '/kill @e[type=!Player]']) await chat(c);
  };
  // Large moves are rejected by the integrated server (40+ blocks were reverted; the limit is per client
  // packet, ~10 blocks in vanilla). Move in steps of <= stepMax blocks with >= 2 client ticks between them.
  const teleport = async (x, y, z, yaw = 0, pitch = 0) => { await chat(`/tp @p ${x} ${y} ${z} ${yaw} ${pitch}`); await page.waitForTimeout(1500); await setCamera(x, y, z, yaw, pitch); };
  const moveSafe = async (to, { stepMax = 2, stepWaitMs = 120, maxJump = 100 } = {}) => {
    const [x0, y0, z0] = await getState();
    const dist = Math.hypot(to[0] - x0, to[1] - y0, to[2] - z0);
    if (dist > maxJump) throw new Error(`moveSafe: ${dist.toFixed(1)} blocks is too far; use teleport()`);
    const n = Math.max(1, Math.ceil(dist / stepMax));
    for (let i = 1; i <= n; i++) {
      const f = i / n;
      await setCamera(x0 + (to[0] - x0) * f, y0 + (to[1] - y0) * f, z0 + (to[2] - z0) * f, to[3], to[4]);
      if (n > 1) await page.waitForTimeout(stepWaitMs);
    }
    return { steps: n, dist };
  };

  // ---- image comparison done in a separate blank page (the browser decodes the PNGs; no extra deps)
  let cmpPage = null;
  const diffPct = async (bufA, bufB, region = [0, 1]) => {
    if (!cmpPage) { cmpPage = await browser.newPage(); await cmpPage.goto('about:blank'); }
    return cmpPage.evaluate(async ([a, b, region]) => {
      const load = async (b64) => {
        const bm = await createImageBitmap(await (await fetch('data:image/png;base64,' + b64)).blob());
        const c = new OffscreenCanvas(bm.width, bm.height), g = c.getContext('2d'); g.drawImage(bm, 0, 0);
        return g.getImageData(0, 0, bm.width, bm.height).data;
      };
      const A = await load(a), B = await load(b); if (A.length !== B.length) return 100;
      const px = A.length / 4, from = Math.floor(px * region[0]), to = Math.floor(px * region[1]);
      let n = 0; for (let p = from; p < to; p++) { const i = p * 4; if (Math.abs(A[i] - B[i]) + Math.abs(A[i + 1] - B[i + 1]) + Math.abs(A[i + 2] - B[i + 2]) > 24) n++; }
      return 100 * n / Math.max(1, to - from);
    }, [bufA.toString('base64'), bufB.toString('base64'), region]);
  };

  // ---- warmPath: the integrated server only generates/sends chunks around where the player is, and JS world
  // generation is slow, so a still image can be "stable" while distant terrain is simply not there yet
  // (seen: first frame = one hill, last frame at the same pose = hills, trees, fog). Visit the whole route
  // once with the draw gate OFF (fast frames) and dwell at each stop; then capture.
  const warmPath = async (pathFn, stops = 8, { dwellMs = 8000, stepMax = 2 } = {}) => {
    const wasOn = (await glStats()).on; await render(false);
    for (let i = 0; i < stops; i++) { await moveSafe(pathFn(stops > 1 ? i / (stops - 1) : 0), { stepMax }); await page.waitForTimeout(dwellMs); }
    const w = await waitChunks({ quietMs: 4000, minMs: 1000, maxMs: 90000 });
    if (wasOn) await render(true);
    return w;
  };

  // ---- G1: draw frames with the gate open, take ONE still, close the gate again.
  // Waiting a fixed number of clears is NOT enough: Minecraft only rebuilds a limited number of chunk
  // sections per frame, so right after a move the terrain may be missing (seen: a sky-only first frame).
  // With stable:true (default) we shoot repeatedly until two consecutive shots differ in <= tolPct of the
  // pixels, and report whether that happened. "settleClears" counts gl.clear calls (~8-10 per game frame).
  // Each PBR shot takes 60-140 s, so use stable:false there. With a warmed route and >= 60 clears two PBR shots
  // taken ~90 s apart differed in only 0.23% of pixels (FINDINGS.md section 10). `stable` is null when not checked.
  const captureFrame = async (file, { settleClears = 40, maxMs = 300000, keepOn = false, stable = true, tolPct = 1.0, stableAttempts = 5 } = {}) => {
    const before = await glStats();
    await render(true);
    const t = Date.now(); let prev = null, buf = null, pct = null, attempts = 0, isStable = stable ? false : null, clears = 0;
    while (attempts < (stable ? stableAttempts : 1) && Date.now() - t < maxMs) {
      attempts++;
      await page.evaluate(() => window.__gl.reset());
      const ta = Date.now();
      while (Date.now() - ta < maxMs) {                 // wait for settleClears fresh clears
        const r = await probe(() => window.__gl.frames, null, 60000);
        if (r !== null && (clears = r) >= settleClears) break;
        await page.waitForTimeout(250);
      }
      buf = await page.screenshot({ timeout: shotTimeout });
      if (!stable) break;
      if (prev) { pct = await diffPct(prev, buf); if (pct <= tolPct) { isStable = true; break; } }
      prev = buf;
    }
    fs.writeFileSync(file, buf);
    if (!keepOn && !before.on) await render(false);
    return { file, clears, attempts, stable: isStable, lastDiffPct: pct === null ? null : +pct.toFixed(3), totalMs: Date.now() - t };
  };

  // ---- G2: stills along a camera path. pathFn(u) -> [x,y,z,yaw,pitch], u in [0,1]. Resumable: existing files
  // are skipped. Writes manifest.json (poses, timings, reminder that speed in video is not game speed).
  const captureSequence = async (pathFn, frames, outDir, { prefix = 'f', start = 0, settleClears = 40, chunkQuietMs = 2000, stepMax = 2, capOpts = {} } = {}) => {
    fs.mkdirSync(outDir, { recursive: true });
    const manifestFile = path.join(outDir, 'manifest.json');
    const manifest = fs.existsSync(manifestFile) ? JSON.parse(fs.readFileSync(manifestFile, 'utf8')) : { note: 'Frames were drawn one at a time on software GL; playback speed is not game speed.', frames: [] };
    for (let i = start; i < frames; i++) {
      const file = path.join(outDir, `${prefix}${pad(i)}.png`);
      const pose = pathFn(frames > 1 ? i / (frames - 1) : 0);
      if (fs.existsSync(file) && manifest.frames.some((m) => m.i === i)) continue;
      const mv = await moveSafe(pose, { stepMax });
      const ch = await waitChunks({ quietMs: chunkQuietMs, minMs: 500, maxMs: 60000 });
      const cap = await captureFrame(file, { settleClears, ...capOpts });
      const got = await getState();
      manifest.frames = manifest.frames.filter((m) => m.i !== i).concat([{ i, file: path.basename(file), pose, got, moveSteps: mv.steps, chunksQuiet: ch.quiet, ...cap, file: path.basename(file) }]);
      fs.writeFileSync(manifestFile, JSON.stringify(manifest, null, 1));
    }
    return manifest;
  };

  return { browser, page, logs, rawLogs, click, shot, chat, render, glStats, probe, enterWorld, skipFirstRun, getState, setCamera,
    waitChunks, hideHud, showHud, dismissHints, setResolution, freezeWorld, teleport, moveSafe, captureFrame, captureSequence, warmPath, diffPct };
};

// Camera-path helpers for captureSequence
exports.paths = {
  // circle of `radius` blocks around (cx,cz) at height y, always looking at the centre; yaw sweeps with u
  orbit: (cx, y, cz, radius, pitch = 10, turns = 1, startDeg = 0) => (u) => {
    const a = (startDeg + 360 * turns * u) * Math.PI / 180;
    const x = cx + radius * Math.sin(a), z = cz - radius * Math.cos(a);
    const yaw = ((Math.atan2(-(cx - x), cz - z) * 180) / Math.PI);        // Minecraft yaw: 0 = +Z, 90 = -X
    return [x, y, z, yaw, pitch];
  },
  line: (a, b) => (u) => a.map((v, i) => v + (b[i] - v) * u),
};
