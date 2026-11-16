#!/usr/bin/env node
// この VM のローカルサーバーを、Cloudflare Workers の中継経由で公開する。
//   TUNNEL_URL=wss://vm-relay.<account>.workers.dev/_tunnel/connect node expose.mjs 3000
// 合言葉は X-Tunnel-Key ヘッダー。プロキシのネットワークシークレットで自動挿入する場合は TUNNEL_KEY は不要。
import http from "node:http";
import WebSocket from "ws";
import { HttpsProxyAgent } from "https-proxy-agent";

const args = process.argv.slice(2);
const opt = (name, def) => {
  const i = args.indexOf(name);
  if (i < 0) return def;
  return args.splice(i, 2)[1];
};
const targetHost = opt("--host", "127.0.0.1");
const keepOrigin = args.includes("--keep-origin") && args.splice(args.indexOf("--keep-origin"), 1);
const port = Number(args[0]);
let relay = opt("--url", process.env.TUNNEL_URL);
if (!port || !relay) {
  console.error("usage: TUNNEL_URL=wss://<worker>/_tunnel/connect node expose.mjs <port> [--host 127.0.0.1] [--url wss://...]");
  process.exit(2);
}
if (!/^wss?:\/\//.test(relay)) relay = "wss://" + relay;
if (!new URL(relay).pathname.startsWith("/_tunnel/")) relay = relay.replace(/\/+$/, "") + "/_tunnel/connect";
const key = process.env.TUNNEL_KEY;
// Access のサービストークンを使う場合（中継の URL 全体を Access で守るとき）。これらもプロキシで自動挿入できる。
const accessId = process.env.CF_ACCESS_CLIENT_ID;
const accessSecret = process.env.CF_ACCESS_CLIENT_SECRET;
const hostHeader = `localhost:${port}`; // ローカルアプリの Host 検証に通るよう書き換える
const proxy = process.env.HTTPS_PROXY || process.env.https_proxy;
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);

const frame = (id, buf) => {
  const out = Buffer.allocUnsafe(4 + buf.length);
  out.writeUInt32BE(id, 0);
  buf.copy(out, 4);
  return out;
};
const HOP = new Set(["connection", "keep-alive", "transfer-encoding", "upgrade", "proxy-connection", "te", "trailer"]);
const closeCode = (c) => (Number.isInteger(c) && c >= 1000 && c <= 4999 && ![1004, 1005, 1006, 1015].includes(c) ? c : 1000);

function localHeaders(list) {
  const h = {};
  for (const [k, v] of list) {
    const lk = k.toLowerCase();
    if (HOP.has(lk)) continue;
    h[lk] = h[lk] === undefined ? v : [].concat(h[lk], v);
  }
  h.host = hostHeader;
  if (h.origin && !keepOrigin) h.origin = `http://${hostHeader}`;
  return h;
}

let attempt = 0;
function connect() {
  const secure = relay.startsWith("wss:");
  const wsOpts = { headers: {}, handshakeTimeout: 20000 };
  if (key) wsOpts.headers["x-tunnel-key"] = key;
  if (accessId && accessSecret) {
    wsOpts.headers["cf-access-client-id"] = accessId;
    wsOpts.headers["cf-access-client-secret"] = accessSecret;
  }
  if (secure && proxy) wsOpts.agent = new HttpsProxyAgent(proxy);
  const up = new WebSocket(relay, wsOpts);
  const reqs = new Map(); // id -> http.ClientRequest
  const socks = new Map(); // id -> ローカルの WebSocket
  let ping;

  const send = (obj) => up.readyState === WebSocket.OPEN && up.send(JSON.stringify(obj));

  up.on("open", () => {
    attempt = 0;
    log(`connected: ${relay} → ${targetHost}:${port}`);
    ping = setInterval(() => up.readyState === WebSocket.OPEN && up.send("ping"), 25000);
  });
  up.on("unexpected-response", (_req, res) => {
    log(`relay rejected the connection: HTTP ${res.statusCode}` + (res.statusCode === 403 ? " (合言葉 / Access の設定を確認)" : ""));
    res.resume();
  });
  up.on("error", (e) => log("relay error:", e.message));
  up.on("close", () => {
    clearInterval(ping);
    for (const r of reqs.values()) r.destroy();
    for (const s of socks.values()) s.terminate();
    const wait = Math.min(15000, 1000 * 2 ** Math.min(attempt++, 4));
    log(`disconnected; retry in ${wait / 1000}s`);
    setTimeout(connect, wait);
  });

  up.on("message", (data, isBinary) => {
    if (isBinary) {
      const b = Buffer.from(data);
      if (b.length < 4) return;
      const id = b.readUInt32BE(0);
      const payload = b.subarray(4);
      if (reqs.has(id)) reqs.get(id).write(payload);
      else if (socks.has(id)) socks.get(id).send(payload, { binary: true });
      return;
    }
    const s = data.toString();
    if (s === "pong") return;
    let m;
    try { m = JSON.parse(s); } catch { return; }
    switch (m.t) {
      case "req": return onReq(m);
      case "req-end": return reqs.get(m.id)?.end();
      case "req-abort": reqs.get(m.id)?.destroy(); reqs.delete(m.id); return;
      case "ws-open": return onWsOpen(m);
      case "ws-text": return socks.get(m.id)?.send(m.data);
      case "ws-close": {
        const w = socks.get(m.id);
        if (w) { try { w.close(closeCode(m.code), String(m.reason || "")); } catch { w.terminate(); } }
      }
    }
  });

  function onReq(m) {
    const t0 = Date.now();
    const req = http.request(
      { host: targetHost, port, method: m.method, path: m.url, headers: localHeaders(m.headers) },
      (res) => {
        const headers = [];
        for (let i = 0; i < res.rawHeaders.length; i += 2) {
          if (!HOP.has(res.rawHeaders[i].toLowerCase())) headers.push([res.rawHeaders[i], res.rawHeaders[i + 1]]);
        }
        send({ t: "res", id: m.id, status: res.statusCode, headers });
        res.on("data", (chunk) => {
          res.pause();
          up.send(frame(m.id, chunk), { binary: true }, () => res.resume());
        });
        res.on("end", () => {
          send({ t: "res-end", id: m.id });
          reqs.delete(m.id);
          log(`${m.method} ${m.url} → ${res.statusCode} (${Date.now() - t0}ms)`);
        });
        res.on("error", (e) => send({ t: "res-err", id: m.id, message: e.message }));
      },
    );
    req.on("error", (e) => {
      log(`${m.method} ${m.url} → local error: ${e.code || e.message}`);
      send({ t: "res-err", id: m.id, message: `local server error: ${e.code || e.message}` });
      reqs.delete(m.id);
    });
    reqs.set(m.id, req);
  }

  function onWsOpen(m) {
    const h = localHeaders(m.headers);
    const local = new WebSocket(`ws://${targetHost}:${port}${m.url}`, m.protocols || [], { headers: h });
    let opened = false;
    local.on("open", () => {
      opened = true;
      socks.set(m.id, local);
      send({ t: "ws-opened", id: m.id, protocol: local.protocol || "" });
      log(`WS open ${m.url}`);
    });
    local.on("message", (d, bin) => {
      if (bin) up.readyState === WebSocket.OPEN && up.send(frame(m.id, Buffer.from(d)), { binary: true });
      else send({ t: "ws-text", id: m.id, data: d.toString() });
    });
    local.on("close", (code, reason) => {
      socks.delete(m.id);
      if (opened) send({ t: "ws-close", id: m.id, code: closeCode(code), reason: reason.toString() });
    });
    local.on("error", (e) => {
      if (!opened) send({ t: "ws-fail", id: m.id, message: e.message });
    });
  }
}

connect();
