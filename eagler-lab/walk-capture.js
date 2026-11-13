// A3: eye-level walk through the village at x=568 (south-facing). Heights come from ground-probe.js samples
// (player settled on the ground in survival mode); the camera flies in spectator mode at ground + eye height.
// usage: [FRAMES=180] [FPS=30] [RES=1280x720] EAGLER_HTML=<hooked copy> EAGLER_SHOTS=<dir> node walk-capture.js
const L = require('./lib.js');
const fs = require('fs');
const FRAMES = +(process.env.FRAMES || 180), FPS = +(process.env.FPS || 30);
const RES = (process.env.RES || '').split('x').map(Number);
// ground samples: [z, feet y of the player standing there] at x=568.5 (measured)
const G = [[546, 74], [550, 72], [554, 71], [558, 69], [562, 69], [566, 69]];
const Z0 = 546.5, Z1 = 564.5, X = 568.5, EYE = 1.62, PITCH = 3;
const env = G.map(([z, y], i) => [z, Math.max(...G.slice(Math.max(0, i - 1), i + 2).map((g) => g[1]))]);
const hAt = (z) => { for (let i = 0; i < env.length - 1; i++) if (z >= env[i][0] && z <= env[i + 1][0]) return env[i][1] + (env[i + 1][1] - env[i][1]) * (z - env[i][0]) / (env[i + 1][0] - env[i][0]); return env[env.length - 1][1]; };
const path = (u) => { const z = Z0 + (Z1 - Z0) * u; return [X, hAt(z) + EYE + 0.25, z, 0, PITCH]; };   // yaw 0 = facing +Z (south)
(async () => {
  const OUT = process.env.EAGLER_SHOTS;
  const lib = await L.launch({ shotTimeout: 240000, logFile: OUT + '/walk-console.log' });
  const { browser, rawLogs, skipFirstRun, enterWorld, freezeWorld, dismissHints, hideHud, teleport, warmPath, setCamera, captureVideoFrames, setResolution, render, getState } = lib;
  await enterWorld('eagler'); await freezeWorld({ time: 6000 }); await dismissHints(); await hideHud();
  await render(false);
  if (RES.length === 2) await setResolution(RES[0], RES[1]);
  await teleport(...path(0));
  console.error('warm', JSON.stringify(await warmPath(path, 8, { dwellMs: 8000 })));
  await setCamera(...path(0));
  const dir = OUT + '/walk-frames'; fs.rmSync(dir, { recursive: true, force: true });
  const t0 = Date.now();
  const man = await captureVideoFrames(path, FRAMES, dir, { fps: FPS, prefix: 'w-', settleClears: 20 });
  const bad = man.frames.filter((f) => f.got.some((v, k) => Math.abs(v - f.pose[k]) > 0.01));
  console.error(`walk: ${FRAMES} frames in ${((Date.now() - t0) / 1000).toFixed(0)} s; pose mismatches: ${bad.length}`);
  fs.writeFileSync(OUT + '/walk-path.json', JSON.stringify({ X, Z0, Z1, EYE, PITCH, ground: G, poses: [path(0), path(0.5), path(1)] }));
  await browser.close(); console.error('DONE');
})().catch((e) => { console.error('FAILED', e); process.exit(1); });
