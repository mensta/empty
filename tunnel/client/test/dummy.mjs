// テスト用ダミーサーバー: HTTP / 大きい応答 / アップロード / SSE / WebSocket
import http from "node:http";
import { WebSocketServer } from "ws";
const port = Number(process.argv[2] || 8099);
const server = http.createServer((req, res) => {
  if (req.headers.host !== `localhost:${port}`) { res.writeHead(403); return res.end("bad host " + req.headers.host); }
  if (req.url === "/") { res.setHeader("content-type", "text/html"); res.setHeader("set-cookie", ["a=1; Path=/", "b=2; Path=/"]); return res.end("<h1>hello from VM</h1>"); }
  if (req.url === "/big") { res.writeHead(200, { "content-type": "application/octet-stream" }); const b = Buffer.alloc(5 * 1024 * 1024, 7); return res.end(b); }
  if (req.url === "/echo") { const c = []; req.on("data", (d) => c.push(d)); req.on("end", () => { const body = Buffer.concat(c); res.setHeader("content-type", "application/json"); res.end(JSON.stringify({ method: req.method, len: body.length, hdr: req.headers["x-test"], ct: req.headers["content-type"], sha: require_sha(body) })); }); return; }
  if (req.url === "/sse") { res.writeHead(200, { "content-type": "text/event-stream" }); let n = 0; const t = setInterval(() => { res.write(`data: tick ${++n}\n\n`); if (n === 3) { clearInterval(t); res.end(); } }, 200); return; }
  if (req.url === "/redirect") { res.writeHead(302, { location: "/" }); return res.end(); }
  if (req.url === "/304") { res.writeHead(304); return res.end(); }
  res.writeHead(404); res.end("nope");
});
import crypto from "node:crypto";
const require_sha = (b) => crypto.createHash("sha256").update(b).digest("hex");
const wss = new WebSocketServer({ server });
wss.on("connection", (ws, req) => { ws.send("welcome " + req.headers.host); ws.on("message", (d, bin) => ws.send(d, { binary: bin })); });
server.listen(port, "127.0.0.1", () => console.log("dummy on", port));
