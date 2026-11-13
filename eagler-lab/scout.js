// Scout candidate places: teleport (server accepts /tp at any distance), let chunks load with the draw gate off, take stills.
// usage: SPOTS="x,z;x,z" [Y=100] [PITCH=35] [YAWS=0,180] EAGLER_HTML=... EAGLER_SHOTS=... node scout.js
const L = require('./lib.js');
const fs = require('fs');
(async () => {
  const OUT = process.env.EAGLER_SHOTS, Y = +(process.env.Y || 100), PITCH = +(process.env.PITCH || 35), YAWS = (process.env.YAWS || '0,180').split(',').map(Number);
  const spots = process.env.SPOTS.split(';').map((s) => s.split(',').map(Number));
  const { browser, rawLogs, enterWorld, freezeWorld, dismissHints, hideHud, teleport, waitChunks, captureFrame, render, chat } = await L.launch({ shotTimeout: 120000, logFile: OUT + '/scout-console.log' });
  await enterWorld('eagler'); await freezeWorld({ time: 6000 }); await dismissHints(); await hideHud();
  const n0 = rawLogs.length; await chat('/seed'); await new Promise((r) => setTimeout(r, 1500));
  console.error('seed line:', (rawLogs.slice(n0).find((l) => /Seed/i.test(l)) || 'none').replace(/^.*?\]\s*/, '').slice(0, 100));
  await render(false);
  for (const [x, z] of spots) {
    for (const yaw of YAWS) {
      await teleport(x + 0.5, Y, z + 0.5, yaw, PITCH);
      const w = await waitChunks({ quietMs: 4000, minMs: 6000, maxMs: 90000 });
      const f = `${OUT}/scout_${x}_${z}_y${yaw}.png`;
      await captureFrame(f, { settleClears: 20, stable: false });
      console.error('spot', x, z, 'yaw', yaw, JSON.stringify(w));
    }
  }
  await browser.close(); console.error('DONE');
})().catch((e) => { console.error('FAILED', e); process.exit(1); });
