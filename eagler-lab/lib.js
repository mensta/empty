const { chromium } = require('playwright');
const S='/tmp/claude-0/-home-user-empty/1b4fe089-cb62-5283-840e-35a462022a00/scratchpad';
exports.S=S;
exports.open = async (html = S+'/analysis/patched/eagler-hooked.html') => {
  const b=await chromium.launch({args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
  const p=await b.newPage({viewport:{width:1280,height:720}});
  const logs=[]; p.on('console',m=>{const t=m.text(); if(!/does not exist|OptiFine/.test(t)) logs.push(t.slice(0,200));});
  p.on('pageerror',e=>logs.push('[pageerror] '+String(e).slice(0,300)));
  await p.goto('file://'+html);
  await p.click('#skipCountdown');
  await p.waitForTimeout(9000);
  const click=async(x,y,w=2500)=>{await p.mouse.move(x,y);await p.waitForTimeout(600);await p.mouse.down();await p.waitForTimeout(500);await p.mouse.up();await p.waitForTimeout(w);};
  const shot=(n)=>p.screenshot({path:S+'/run/shots/'+n+'.png'});
  return {b,p,logs,click,shot};
};
