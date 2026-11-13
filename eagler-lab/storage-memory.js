// R8 (memory) + R10 (what the game stores in the browser). Reads names/counts/sizes only, never contents.
const L = require('./lib.js');
(async () => {
  const lib = await L.launch({ shotTimeout: 120000 });
  const { browser, page, skipFirstRun, enterWorld, freezeWorld, render } = lib;
  const cdp = await page.context().newCDPSession(page); await cdp.send('Performance.enable');
  const heap = async (label) => {
    const m = Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map((x) => [x.name, x.value]));
    console.error(`HEAP ${label}: JS used ${(m.JSHeapUsedSize / 1048576).toFixed(0)} MB, JS total ${(m.JSHeapTotalSize / 1048576).toFixed(0)} MB, DOM nodes ${m.Nodes}`);
  };
  await heap('after page load + countdown skip (before first-run screens)');
  await skipFirstRun(); await page.waitForTimeout(3000); await heap('title screen');
  await render(false); await enterWorld('eagler', { first: false }); await freezeWorld({});
  await heap('in world (default settings)');
  const report = await page.evaluate(async () => {
    const out = { idb: [], local: [], estimate: null };
    const dbs = indexedDB.databases ? await indexedDB.databases() : [];
    for (const d of dbs) {
      const info = { name: d.name, version: d.version, stores: [] };
      await new Promise((res) => {
        const rq = indexedDB.open(d.name);
        rq.onsuccess = async () => {
          const db = rq.result;
          for (const sn of db.objectStoreNames) {
            const st = db.transaction(sn).objectStore(sn);
            const n = await new Promise((r) => { const c = st.count(); c.onsuccess = () => r(c.result); c.onerror = () => r(null); });
            // total byte length of values, if they are ArrayBuffer/typed arrays (no contents are returned)
            let bytes = 0, kinds = {};
            await new Promise((r) => { const cur = st.openCursor(); cur.onsuccess = () => { const c = cur.result; if (!c) return r(); const v = c.value; const k = Object.prototype.toString.call(v).slice(8, -1); kinds[k] = (kinds[k] || 0) + 1; if (v && v.byteLength !== undefined) bytes += v.byteLength; else if (v && v.data && v.data.byteLength !== undefined) bytes += v.data.byteLength; c.continue(); }; cur.onerror = () => r(); });
            info.stores.push({ store: sn, keyPath: st.keyPath, count: n, valueKinds: kinds, approxBytes: bytes });
          }
          db.close(); res();
        };
        rq.onerror = () => res();
      });
      out.idb.push(info);
    }
    for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i); out.local.push({ key: k, chars: (localStorage.getItem(k) || '').length }); }
    out.estimate = navigator.storage && navigator.storage.estimate ? await navigator.storage.estimate() : null;
    return out;
  });
  console.log(JSON.stringify(report, null, 1));
  await browser.close();
})().catch((e) => { console.error('FAILED', e); process.exit(1); });
