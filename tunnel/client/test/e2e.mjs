import crypto from "node:crypto";
import WS from "ws";
const B = process.argv[2] || "http://127.0.0.1:8787";
let fail = 0;
const ok = (n, c, extra = "") => { console.log(c ? "PASS" : "FAIL", n, extra); if (!c) fail++; };
const sha = (b) => crypto.createHash("sha256").update(b).digest("hex");

let r = await fetch(B + "/");
ok("GET /", r.status === 200 && (await r.text()).includes("hello from VM"));
ok("multi set-cookie", r.headers.getSetCookie().length === 2);

r = await fetch(B + "/big"); const big = Buffer.from(await r.arrayBuffer());
ok("5MB download", big.length === 5 * 1024 * 1024 && big.every((x) => x === 7), `len=${big.length}`);

const up = crypto.randomBytes(3 * 1024 * 1024);
r = await fetch(B + "/echo", { method: "POST", body: up, headers: { "x-test": "hi", "content-type": "application/octet-stream" } });
const j = await r.json();
ok("3MB upload (sha match)", j.len === up.length && j.sha === sha(up) && j.hdr === "hi", JSON.stringify({ len: j.len, hdr: j.hdr }));

r = await fetch(B + "/echo", { method: "POST", body: JSON.stringify({ a: 1 }), headers: { "content-type": "application/json" } });
ok("small POST", (await r.json()).len === 7);

r = await fetch(B + "/sse"); const chunks = [];
const t0 = Date.now();
for await (const c of r.body) chunks.push([Date.now() - t0, Buffer.from(c).toString()]);
ok("SSE streamed incrementally", chunks.length >= 3 && chunks.at(-1)[0] - chunks[0][0] > 200, JSON.stringify(chunks.map((c) => c[0])));

r = await fetch(B + "/redirect", { redirect: "manual" });
ok("302 passthrough", r.status === 302 && r.headers.get("location") === "/");
r = await fetch(B + "/304");
ok("304 passthrough", r.status === 304);
r = await fetch(B + "/nope"); ok("404 passthrough", r.status === 404);

const wsRes = await new Promise((resolve) => {
  const w = new WS(B.replace("http", "ws") + "/ws"); const got = [];
  w.on("message", (d, bin) => { got.push([bin, bin ? d.length : d.toString()]); if (got.length === 3) w.close(); });
  w.on("open", () => { w.send("text-msg"); w.send(Buffer.alloc(1000, 1)); });
  w.on("close", () => resolve(got));
  w.on("error", (e) => resolve("err " + e.message));
});
ok("WebSocket text+binary echo", Array.isArray(wsRes) && wsRes[0][1] === "welcome localhost:8099" && wsRes[1][1] === "text-msg" && wsRes[2][0] === true && wsRes[2][1] === 1000, JSON.stringify(wsRes));

const par = await Promise.all(Array.from({ length: 20 }, (_, i) => fetch(B + "/echo", { method: "POST", body: "x".repeat(i) }).then((r) => r.json())));
ok("20 parallel", par.every((p, i) => p.len === i));

console.log(fail ? `${fail} FAILED` : "ALL PASS");
process.exit(fail ? 1 : 0);
