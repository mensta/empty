// Click through menus from the title screen and screenshot each step.
// usage: node explore.js "485,605;640,300" prefix     (x,y pairs separated by ';')
const L = require('./lib.js');
(async () => {
  const steps = (process.argv[2] || '').split(';').filter(Boolean).map((p) => p.split(',').map(Number));
  const prefix = process.argv[3] || 'explore';
  const { browser, skipFirstRun, click, shot } = await L.launch();
  await skipFirstRun();
  await shot(`${prefix}-0`);
  for (let i = 0; i < steps.length; i++) { await click(steps[i][0], steps[i][1], 3000); await shot(`${prefix}-${i + 1}`); }
  await browser.close();
})();
