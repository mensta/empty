// Probe ground height: put the player in survival mode with the Resistance effect (gravity applies, no fall damage; creative mode keeps the player flying) high above (x,z), let gravity drop it, read the settled y.
// Also takes an eye-level still looking along YAW. usage: PTS="x,z;x,z" [YAW=180] [DROP=140] [STILLS=1] EAGLER_HTML=... EAGLER_SHOTS=... node ground-probe.js
const L = require('./lib.js');
const fs = require('fs');
(async () => {
  const OUT = process.env.EAGLER_SHOTS, YAW = +(process.env.YAW || 180), DROP = +(process.env.DROP || 140), STILLS = process.env.STILLS !== '0';
  const pts = process.env.PTS.split(';').map((s) => s.split(',').map(Number));
  const { browser, enterWorld, freezeWorld, dismissHints, hideHud, chat, getState, waitChunks, captureFrame, render, page } = await L.launch({ shotTimeout: 120000, logFile: OUT + '/probe-console.log' });
  await enterWorld('eagler'); await freezeWorld({ time: 6000 }); await dismissHints(); await hideHud();
  await render(false);
  const res = [];
  for (const [x, z] of pts) {
    await chat('/gamemode survival'); await chat('/effect @p resistance 1000 10');
    await chat(`/tp @p ${x + 0.5} ${DROP} ${z + 0.5} ${YAW} 0`);
    await waitChunks({ quietMs: 3000, minMs: 4000, maxMs: 90000 });
    let last = null, same = 0, s;
    for (let i = 0; i < 40 && same < 4; i++) { await page.waitForTimeout(1000); s = await getState(); same = last !== null && Math.abs(s[1] - last) < 0.001 ? same + 1 : 0; last = s[1]; }
    const r = { x, z, y: s[1], settled: same >= 4, state: s };
    if (STILLS) { r.still = `${OUT}/ground_${x}_${z}.png`; await captureFrame(r.still, { settleClears: 20, stable: false }); }
    res.push(r); console.error(JSON.stringify(r)); fs.writeFileSync(OUT + '/ground.json', JSON.stringify(res, null, 1));
  }
  await browser.close(); console.error('DONE');
})().catch((e) => { console.error('FAILED', e); process.exit(1); });
