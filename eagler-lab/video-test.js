// (c) Small video test: camera move at fps (default 30) for N frames with a virtual clock, then mp4.
// PBR=1 enables the shader pack first (then use a small FRAMES: each frame is expensive).
// usage: [PBR=1] [FRAMES=90] [FPS=30] EAGLER_HTML=<hooked copy> EAGLER_SHOTS=<dir> node video-test.js
const L = require('./lib.js');
const fs = require('fs');
const PBR = process.env.PBR === '1', FRAMES = +(process.env.FRAMES || 90), FPS = +(process.env.FPS || 30);
// RES=1920x1080 switches the viewport after the world is entered (menu clicks are measured at 1280x720); STOPS = warm-up stops along the path
const RES = (process.env.RES || '').split('x').map(Number), STOPS = +(process.env.STOPS || 8);
(async () => {
  const OUT = process.env.EAGLER_SHOTS;
  const lib = await L.launch({ shotTimeout: 240000, logFile: OUT + '/video-console.log' });
  const { browser, page, click, render, skipFirstRun, enterWorld, freezeWorld, dismissHints, hideHud, teleport, warmPath, setCamera, getState, waitChunks, captureVideoFrames, diffPct, chat, rawLogs, setResolution } = lib;
  const tag = (PBR ? 'pbr' : 'plain') + (process.env.TAG ? '-' + process.env.TAG : '');
  await skipFirstRun();
  if (PBR) { await click(485, 605, 3000); await click(878, 275, 3500); await click(400, 659, 2500); await click(878, 659, 12000); await click(640, 653, 4000); }
  await render(false);
  await enterWorld('eagler', { first: false });
  await freezeWorld({ time: 6000 }); await dismissHints(); await hideHud();
  if (RES.length === 2) await setResolution(RES[0], RES[1]);
  const POSE = [100.5, 100, 200.5, 45, 10];
  await teleport(...POSE);
  // orbit around a point 25 blocks ahead: a quarter turn (~39 blocks) in 90 frames
  const cx = 100.5 - 25 * Math.sin(Math.PI / 4), cz = 200.5 + 25 * Math.cos(Math.PI / 4);
  const path = L.paths.orbit(cx, 100, cz, 25, 10, 0.25 * FRAMES / 90, 45);   // same speed per frame whatever FRAMES is
  console.error(tag, 'warm', JSON.stringify(await warmPath(path, STOPS, { dwellMs: 8000 })));
  await setCamera(...path(0));
  const dir = `${OUT}/video-${tag}`; fs.rmSync(dir, { recursive: true, force: true });
  const t0 = Date.now();
  const man = await captureVideoFrames(path, FRAMES, dir, { fps: FPS, prefix: 'v-', settleClears: PBR ? 40 : 20 });
  const wall = (Date.now() - t0) / 1000;
  const ms = man.frames.map((f) => f.ms).sort((a, b) => a - b);
  console.error(`${tag}: ${FRAMES} frames in ${wall.toFixed(0)} s  -> per frame mean ${(wall / FRAMES).toFixed(2)} s, median ${ms[ms.length >> 1] / 1000} s, max ${ms[ms.length - 1] / 1000} s`);
  const bad = man.frames.filter((f) => f.got.some((v, k) => Math.abs(v - f.pose[k]) > 0.01));
  console.error('pose mismatches (client value != requested):', bad.length, bad.slice(0, 3).map((f) => f.i));
  // frame-to-frame continuity: whole-image and terrain-only differing %
  const d = [];
  for (let i = 1; i < FRAMES; i++) {
    const a = fs.readFileSync(`${dir}/v-${String(i - 1).padStart(5, '0')}.png`), b = fs.readFileSync(`${dir}/v-${String(i).padStart(5, '0')}.png`);
    d.push([i, await diffPct(a, b), await diffPct(a, b, [0.45, 1])]);
  }
  const s = (k) => d.map((x) => x[k]);
  const stat = (v) => `mean ${(v.reduce((x, y) => x + y, 0) / v.length).toFixed(2)} min ${Math.min(...v).toFixed(2)} max ${Math.max(...v).toFixed(2)}`;
  console.error('consecutive frames, whole image differing %:', stat(s(1)), '| terrain only:', stat(s(2)));
  const mean = s(1).reduce((x, y) => x + y, 0) / s(1).length, sd = Math.sqrt(s(1).reduce((x, y) => x + (y - mean) ** 2, 0) / s(1).length);
  console.error('outlier frames (> mean + 3 sd):', d.filter((x) => x[1] > mean + 3 * sd).map((x) => `${x[0]}:${x[1].toFixed(1)}%`).join(' ') || 'none');
  console.error('disconnect/timeout lines:', rawLogs.filter((l) => /timed out|disconnect|lost connection/i.test(l)).length);
  fs.writeFileSync(`${OUT}/video-${tag}-diffs.json`, JSON.stringify(d));
  await browser.close();
  console.error('DONE');
})().catch((e) => { console.error('FAILED', e); process.exit(1); });
