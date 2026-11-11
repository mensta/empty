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
  await chat('/tp @p 100.5 90 200.5');
  await p.waitForTimeout(3000);
  await shot('21-after-tp');
  const res=await p.evaluate(()=>{
    const mc=window.__eagMC(); const seen=new Set(); const hits=[]; const q=[[mc,'mc',0]];
    while(q.length){const [o,path,d]=q.shift(); if(!o||typeof o!=='object'||seen.has(o)||d>4) continue; seen.add(o);
      let ks; try{ks=Object.keys(o);}catch(e){continue}
      const nums={}; for(const k of ks){const v=o[k]; if(typeof v==='number'&&(Math.abs(v-100.5)<2||Math.abs(v-200.5)<2||Math.abs(v-90)<3)) nums[k]=v;}
      if(Object.keys(nums).length>=2) hits.push([path,nums]);
      for(const k of ks){const v=o[k]; if(v&&typeof v==='object'&&!(v instanceof Array&&v.length>200)&&!ArrayBuffer.isView(v)) q.push([v,path+'.'+k,d+1]);}
    }
    return hits.slice(0,12);
  });
  console.log(JSON.stringify(res,null,1));
  console.log(logs.filter(l=>/Client thread|Server thread|chat|tp|Teleport/i.test(l)).slice(-8).join('\n'));
  await b.close();
})();
