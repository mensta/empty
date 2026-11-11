const L=require('./lib.js');
(async()=>{
  const {b,p,click,shot,logs}=await L.open();
  await click(640,563);await click(640,653,5000);await click(640,575,4000);
  await click(640,353,4000);await click(875,593,4000);await click(640,329,4000);
  await click(640,590,3000);               // More World Options
  await click(640,210,500); await p.keyboard.type('eagler',{delay:80}); await p.waitForTimeout(500);
  await click(400,482,800);                // Allow Cheats ON
  await click(640,590,2000);               // Done
  await click(400,665,25000);              // Create
  await p.waitForTimeout(15000);
  const chat=async(cmd)=>{await p.keyboard.press('t');await p.waitForTimeout(700);await p.keyboard.type(cmd,{delay:30});await p.keyboard.press('Enter');await p.waitForTimeout(1500);};
  await chat('/gamemode spectator');
  await chat('/time set 6000');
  await chat('/weather clear');
  await p.keyboard.press('F1'); await p.waitForTimeout(800);
  const cam=(x,y,z,yaw,pitch)=>p.evaluate(([x,y,z,yaw,pitch])=>{
    const e=window.__eagMC().bR;
    e.D=e.fS=e.mT=x; e.J=e.gr=e.l2=y; e.E=e.fT=e.mU=z;
    e.bN=e.hq=yaw; e.cR=e.ip=pitch; return [e.D,e.J,e.E,e.bN,e.cR];
  },[x,y,z,yaw,pitch]);
  const read=()=>p.evaluate(()=>{const e=window.__eagMC().bR;return [e.D,e.J,e.E,e.bN,e.cR].map(v=>+v.toFixed(2));});
  await chat('/tp @p 100.5 100 200.5 0 0'); await p.waitForTimeout(2500);
  await p.evaluate(()=>new Promise(res=>{const e=window.__eagMC().bR;const bb=e.dz;
    const x0=e.D,y0=e.J,z0=e.E; const w=bb.cL-bb.cG,h=bb.cI-bb.b4;
    let i=0;const t=setInterval(()=>{i++;const f=i/60;
      const x=x0+60*f,y=y0+10*f,z=z0;
      bb.cG=x-w/2;bb.cL=x+w/2;bb.b4=y;bb.cI=y+h;bb.cF=z-w/2;bb.cM=z+w/2;
      e.D=e.fS=e.mT=x; e.J=e.gr=e.l2=y; e.E=e.fT=e.mU=z; e.bN=e.hq=90*f; e.cR=e.ip=10;
      if(i>=60){clearInterval(t);res();}},50);}));
  await p.waitForTimeout(2500);
  console.log('after dolly',await read());
  await shot('26-dolly-end');
  await b.close();
})();
