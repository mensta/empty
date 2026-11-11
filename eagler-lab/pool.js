const fs=require('fs');
const js=fs.readFileSync('main.js','utf8');
const s=js.indexOf('$rt_stringPool([',20000000)+'$rt_stringPool('.length;
let depth=0,i=s,inStr=false,q='';
for(;i<js.length;i++){const c=js[i];
 if(inStr){ if(c==='\\')i++; else if(c===q)inStr=false; continue;}
 if(c==='"'||c==="'"){inStr=true;q=c;continue}
 if(c==='[')depth++; else if(c===']'){depth--; if(depth===0){i++;break}}
}
const arr=eval(js.slice(s,i));
fs.writeFileSync('pool.json',JSON.stringify(arr));
console.log('pool size',arr.length);
for (const t of ['Setting user: ','Initializing game','Reloading ResourceManager: ','Startup','Pre startup']) console.log(JSON.stringify(t),arr.indexOf(t));
