// Same-pose still for PBR on/off. PBR=1 enables the built-in shader pack from Options first.
// Order: world setup with the draw gate OFF (chat works even when PBR would run at ~1 fps) ->
// warm pass over a route around the pose (terrain streams in around where the player is) ->
// back to the pose -> captureFrame. Plain: shoot until stable (clouds drift, so ~1% remains). PBR: each
// shot takes 60-140 s, so no stability loop; shoot SHOTS times and keep all of them to compare.
// usage: PBR=0|1 EAGLER_HTML=<hook-patched copy> EAGLER_SHOTS=<dir> node ab-still.js
const L = require('./lib.js');
const PBR = process.env.PBR === '1';
const POSE = (process.env.POSE || '100.5,100,200.5,45,10').split(',').map(Number); // x,y,z,yaw,pitch
const SHOTS = +(process.env.SHOTS || (PBR ? 2 : 1));
(async () => {
  const lib = await L.launch({ shotTimeout: 240000 });
  const { browser, page, click, render, skipFirstRun, enterWorld, freezeWorld, dismissHints, hideHud, teleport, warmPath, captureFrame, setCamera, getState } = lib;
  const tag = PBR ? 'pbr' : 'plain', OUT = process.env.EAGLER_SHOTS;
  await skipFirstRun();
  if (PBR) {
    await click(485, 605, 3000); await click(878, 275, 3500); await click(400, 659, 2500); // Options > Shaders > Enable
    await click(878, 659, 12000);                                                          // Done (waits for "Refreshing Resources")
    await click(640, 653, 4000);                                                           // Done (options)
  }
  await render(false);
  await enterWorld('eagler', { first: false });
  await freezeWorld({ time: 6000 });
  await dismissHints(); await hideHud();
  await teleport(...POSE);
  const ahead = [POSE[0] - 25 * Math.sin(POSE[3] * Math.PI / 180), POSE[2] + 25 * Math.cos(POSE[3] * Math.PI / 180)];
  const route = L.paths.orbit(ahead[0], POSE[1], ahead[1], 25, POSE[4], 1, POSE[3]);
  console.error(tag, 'warm', JSON.stringify(await warmPath(route, 8, { dwellMs: 8000 })));
  await setCamera(...POSE);
  console.error(tag, 'pose', JSON.stringify(await getState()));
  for (let i = 0; i < SHOTS; i++) {
    const r = await captureFrame(`${OUT}/ab-${tag}-${i}.png`, { settleClears: PBR ? 60 : 40, stable: !PBR, keepOn: true });
    console.error(tag, 'shot', i, JSON.stringify(r), 'pose', JSON.stringify(await getState()));
  }
  await browser.close();
})().catch((e) => { console.error('FAILED', e); process.exit(1); });
