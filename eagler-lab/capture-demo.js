// End-to-end check of the capture API (G1/G2/G3/G10/G11). Output goes to EAGLER_SHOTS (outside the repo).
const L = require('./lib.js');
const fs = require('fs');
(async () => {
  const OUT = process.env.EAGLER_SHOTS;
  const { browser, page, rawLogs, enterWorld, freezeWorld, dismissHints, hideHud, teleport, waitChunks, captureSequence, warmPath, captureFrame, setResolution, getState, chat, diffPct } =
    await L.launch({ shotTimeout: 240000, logFile: OUT + '/raw-console.log' });
  await enterWorld('eagler');
  await freezeWorld({ time: 6000 });
  await dismissHints();
  await hideHud();
  const POSE = [100.5, 100, 200.5, 45, 10];
  await teleport(...POSE);
  console.error('waitChunks', JSON.stringify(await waitChunks({ quietMs: 3000, maxMs: 90000 })));
  // orbit whose first pose == POSE (centre 25 blocks ahead of it)
  const path = L.paths.orbit(100.5 - 25 * Math.sin(Math.PI / 4), 100, 200.5 + 25 * Math.cos(Math.PI / 4), 25, 10, 1, 45);
  console.error('warmPath', JSON.stringify(await warmPath(path, 8, { dwellMs: 8000 })), 'in', 'warm pass');
  const t = Date.now();
  const man = await captureSequence(path, 5, OUT + '/seq', { prefix: 'orbit-', settleClears: 40 });
  console.error('sequence done in', Math.round((Date.now() - t) / 1000), 's; frames', man.frames.length);
  for (const f of man.frames) console.error(' frame', f.i, 'want', f.pose.map((v) => +v.toFixed(1)).join(','), 'got', f.got.join(','), 'steps', f.moveSteps, 'chunksQuiet', f.chunksQuiet, 'attempts', f.attempts, 'stable', f.stable, 'lastDiff%', f.lastDiffPct, 'ms', f.totalMs);
  const A = fs.readFileSync(OUT + '/seq/orbit-00000.png'), B = fs.readFileSync(OUT + '/seq/orbit-00004.png');
  console.error('DETERMINISM first vs last frame (same pose): differing pixels % whole', (await diffPct(A, B)).toFixed(3), '| terrain only (lower 55%)', (await diffPct(A, B, [0.45, 1])).toFixed(3));
  // server-side check: "/tp @p ~ ~ ~" echoes the position the integrated server holds
  const n0 = rawLogs.length; await chat('/tp @p ~ ~ ~');
  console.error('server says:', (rawLogs.slice(n0).find((l) => /Teleported/.test(l)) || 'no line').replace(/^.*?\]\s*/, '').slice(0, 120), '| client:', JSON.stringify(await getState()));
  // 1080p still
  await setResolution(1920, 1080);
  console.error('1080p', JSON.stringify(await captureFrame(OUT + '/still-1080p.png', { settleClears: 40 })));
  await browser.close();
  console.error('raw log lines:', rawLogs.length);
})().catch((e) => { console.error('FAILED', e); process.exit(1); });
