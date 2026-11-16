// VM 中継 Worker。
//   VM ──(外向き WebSocket 443, /_tunnel/connect)──→ Durable Object ←── ブラウザ (HTTP / WebSocket)
// ブラウザ側の認証は Cloudflare Access（JWT をここでも検証する）。VM 側の認証は X-Tunnel-Key ヘッダー。
//
// VM ⇔ DO のプロトコル（1 本の WebSocket に多重化）
//   テキストフレーム = JSON の制御メッセージ
//   バイナリフレーム = [4 バイトの id (BE)][本文チャンク]
//   DO→VM  req{id,method,url,headers} / req-end / req-abort / ws-open{id,url,headers,protocols} / ws-text / ws-close
//   VM→DO  res{id,status,headers} / res-end / res-err / ws-opened{id,protocol} / ws-fail / ws-text / ws-close
import { DurableObject } from "cloudflare:workers";

const TUNNEL_PATH = "/_tunnel/connect";
const HEAD_TIMEOUT_MS = 60_000;
const NULL_BODY = new Set([101, 204, 205, 304]);
const DROP_REQ = new Set([
  "connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailer",
  "transfer-encoding", "upgrade", "host", "accept-encoding", "x-real-ip",
  "sec-websocket-key", "sec-websocket-version", "sec-websocket-extensions", "sec-websocket-protocol",
]);
const DROP_RES = new Set([
  "connection", "keep-alive", "transfer-encoding", "upgrade", "content-length", "proxy-authenticate",
]);

// ---------- 入口 Worker ----------
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const stub = env.RELAY.get(env.RELAY.idFromName("main"));

    if (url.pathname === TUNNEL_PATH) {
      if (!env.TUNNEL_KEY) return text("TUNNEL_KEY is not configured", 500);
      const given = request.headers.get("x-tunnel-key") || "";
      if (!(await safeEqual(given, env.TUNNEL_KEY))) return text("forbidden", 403);
      return stub.fetch(request);
    }

    const err = await authBrowser(request, env);
    if (err) return text(err, 403);
    return stub.fetch(request);
  },
};

const text = (body, status = 200) =>
  new Response(body + "\n", { status, headers: { "content-type": "text/plain; charset=utf-8" } });

async function safeEqual(a, b) {
  const enc = new TextEncoder();
  const [ha, hb] = await Promise.all([
    crypto.subtle.digest("SHA-256", enc.encode(a)),
    crypto.subtle.digest("SHA-256", enc.encode(b)),
  ]);
  return crypto.subtle.timingSafeEqual(ha, hb);
}

// ---------- ブラウザ側の認証 (Cloudflare Access の JWT 検証) ----------
async function authBrowser(request, env) {
  if (env.ACCESS_TEAM && env.ACCESS_AUD) {
    const err = await verifyAccess(request, env).catch((e) => `verify error: ${e.message}`);
    return err ? `Access verification failed: ${err}` : null;
  }
  if (env.ALLOW_PUBLIC === "1") return null; // テスト専用。本番では設定しないこと
  return "Not configured: set ACCESS_TEAM and ACCESS_AUD (Cloudflare Access) before use";
}

const b64u = (s) =>
  Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(s.length / 4) * 4, "=")), (c) => c.charCodeAt(0));
let jwksCache = { at: 0, team: "", keys: [] };
async function jwks(team, force) {
  if (!force && jwksCache.team === team && Date.now() - jwksCache.at < 600_000) return jwksCache.keys;
  const r = await fetch(`https://${team}/cdn-cgi/access/certs`);
  if (!r.ok) throw new Error(`certs ${r.status}`);
  const j = await r.json();
  jwksCache = { at: Date.now(), team, keys: j.keys || [] };
  return jwksCache.keys;
}
async function verifyAccess(request, env) {
  const tok = request.headers.get("cf-access-jwt-assertion");
  if (!tok) return "no Access token (is this URL behind Cloudflare Access?)";
  const parts = tok.split(".");
  if (parts.length !== 3) return "malformed token";
  const dec = new TextDecoder();
  let header, payload;
  try {
    header = JSON.parse(dec.decode(b64u(parts[0])));
    payload = JSON.parse(dec.decode(b64u(parts[1])));
  } catch { return "malformed token"; }
  if (header.alg !== "RS256") return "unexpected alg";
  const team = env.ACCESS_TEAM;
  let jwk = (await jwks(team)).find((k) => k.kid === header.kid);
  if (!jwk) jwk = (await jwks(team, true)).find((k) => k.kid === header.kid);
  if (!jwk) return "unknown signing key";
  const key = await crypto.subtle.importKey("jwk", jwk, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
  const ok = await crypto.subtle.verify("RSASSA-PKCS1-v1_5", key, b64u(parts[2]), new TextEncoder().encode(parts[0] + "." + parts[1]));
  if (!ok) return "bad signature";
  if (!(payload.exp > Date.now() / 1000)) return "expired";
  if (payload.iss !== `https://${team}`) return "bad issuer";
  if (![].concat(payload.aud || []).includes(env.ACCESS_AUD)) return "bad audience";
  return null;
}

// ---------- フレーム / ヘッダーの補助 ----------
function frame(id, data) {
  const p = data instanceof ArrayBuffer ? new Uint8Array(data) : new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
  const out = new Uint8Array(4 + p.length);
  new DataView(out.buffer).setUint32(0, id);
  out.set(p, 4);
  return out;
}
function fwdHeaders(h) {
  const out = [];
  for (const [k, v] of h) {
    if (DROP_REQ.has(k) || k.startsWith("cf-") || k.startsWith("x-forwarded-")) continue;
    out.push([k, v]);
  }
  return out;
}
const closeCode = (c) => (Number.isInteger(c) && c >= 1000 && c <= 4999 && ![1004, 1005, 1006, 1015].includes(c) ? c : 1000);

// ---------- Durable Object ----------
export class Relay extends DurableObject {
  constructor(ctx, env) {
    super(ctx, env);
    this.pending = new Map(); // id -> 進行中の HTTP リクエスト / WS 開通待ち（メモリのみ。処理中は DO は眠らない）
    ctx.setWebSocketAutoResponse(new WebSocketRequestResponsePair("ping", "pong")); // keepalive で DO を起こさない
  }

  vm() {
    return this.ctx.getWebSockets("vm").find((w) => w.readyState === WebSocket.OPEN) ?? null;
  }
  newId() {
    for (;;) {
      const id = crypto.getRandomValues(new Uint32Array(1))[0];
      if (id && !this.pending.has(id) && this.ctx.getWebSockets("b:" + id).length === 0) return id;
    }
  }

  async fetch(request) {
    const url = new URL(request.url);
    const isUpgrade = (request.headers.get("upgrade") || "").toLowerCase() === "websocket";

    if (url.pathname === TUNNEL_PATH) {
      if (!isUpgrade) return text("WebSocket required", 426);
      for (const old of this.ctx.getWebSockets("vm")) { try { old.close(1012, "replaced"); } catch {} }
      const pair = new WebSocketPair();
      this.ctx.acceptWebSocket(pair[1], ["vm"]);
      return new Response(null, { status: 101, webSocket: pair[0] });
    }

    if (!this.vm()) return text("Tunnel offline: the VM is not connected.", 502);
    return isUpgrade ? this.openBrowserWs(request, url) : this.proxyHttp(request, url);
  }

  // --- ブラウザの HTTP → VM ---
  async proxyHttp(request, url) {
    const vm = this.vm();
    const id = this.newId();
    const entry = {};
    const head = new Promise((resolve, reject) => { entry.resolve = resolve; entry.reject = reject; });
    this.pending.set(id, entry);
    const timer = setTimeout(() => entry.reject(new Error("timeout")), HEAD_TIMEOUT_MS);
    try {
      vm.send(JSON.stringify({
        t: "req", id, method: request.method, url: url.pathname + url.search, headers: fwdHeaders(request.headers),
      }));
      if (request.body && request.method !== "GET" && request.method !== "HEAD") {
        const reader = request.body.getReader();
        (async () => {
          try {
            for (;;) {
              const { done, value } = await reader.read();
              if (done) break;
              vm.send(frame(id, value));
            }
            vm.send(JSON.stringify({ t: "req-end", id }));
          } catch { /* VM 切断など */ }
        })();
      } else {
        vm.send(JSON.stringify({ t: "req-end", id }));
      }
      return await head;
    } catch (e) {
      this.pending.delete(id);
      try { vm.send(JSON.stringify({ t: "req-abort", id })); } catch {}
      return text(e.message === "timeout" ? "Gateway timeout: no response from the VM" : `Bad gateway: ${e.message}`, e.message === "timeout" ? 504 : 502);
    } finally {
      clearTimeout(timer);
    }
  }

  // --- ブラウザの WebSocket → VM ---
  async openBrowserWs(request, url) {
    const vm = this.vm();
    const id = this.newId();
    const entry = { buffer: [] };
    const opened = new Promise((resolve, reject) => { entry.resolve = resolve; entry.reject = reject; });
    this.pending.set(id, entry);
    const timer = setTimeout(() => entry.reject(new Error("timeout")), 15_000);
    const protocols = (request.headers.get("sec-websocket-protocol") || "").split(",").map((s) => s.trim()).filter(Boolean);
    try {
      vm.send(JSON.stringify({ t: "ws-open", id, url: url.pathname + url.search, headers: fwdHeaders(request.headers), protocols }));
      const r = await opened;
      const pair = new WebSocketPair();
      this.ctx.acceptWebSocket(pair[1], ["b:" + id]);
      pair[1].serializeAttachment({ id });
      for (const m of entry.buffer) pair[1].send(m); // 開通前に届いた分を流す
      return new Response(null, {
        status: 101, webSocket: pair[0],
        headers: r.protocol ? { "sec-websocket-protocol": r.protocol } : {},
      });
    } catch (e) {
      return text(`Bad gateway: ${e.message}`, 502);
    } finally {
      clearTimeout(timer);
      this.pending.delete(id);
    }
  }

  // --- WebSocket Hibernation のハンドラー ---
  async webSocketMessage(ws, msg) {
    if (this.ctx.getTags(ws).includes("vm")) return this.fromVm(msg);
    const { id } = ws.deserializeAttachment() || {};
    const vm = this.vm();
    if (!vm) { try { ws.close(1011, "tunnel offline"); } catch {} return; }
    if (typeof msg === "string") vm.send(JSON.stringify({ t: "ws-text", id, data: msg }));
    else vm.send(frame(id, msg));
  }

  async webSocketClose(ws, code, reason) {
    this.onSocketGone(ws, code, reason);
  }
  async webSocketError(ws) {
    this.onSocketGone(ws, 1011, "error");
  }
  onSocketGone(ws, code, reason) {
    if (this.ctx.getTags(ws).includes("vm")) {
      if (this.ctx.getWebSockets("vm").some((w) => w !== ws && w.readyState === WebSocket.OPEN)) return; // 置き換えられただけ
      for (const [, p] of this.pending) {
        try { p.reject?.(new Error("tunnel closed")); p.writer?.abort(new Error("tunnel closed")); } catch {}
      }
      this.pending.clear();
      for (const b of this.ctx.getWebSockets()) {
        if (b !== ws && !this.ctx.getTags(b).includes("vm")) { try { b.close(1012, "tunnel closed"); } catch {} }
      }
      return;
    }
    const { id } = ws.deserializeAttachment() || {};
    const vm = this.vm();
    if (vm && id) vm.send(JSON.stringify({ t: "ws-close", id, code: closeCode(code), reason: String(reason || "") }));
    try { ws.close(closeCode(code), String(reason || "")); } catch {}
  }

  // --- VM からのメッセージ ---
  fromVm(msg) {
    if (typeof msg !== "string") {
      const b = new Uint8Array(msg);
      if (b.length < 4) return;
      const id = new DataView(b.buffer, b.byteOffset).getUint32(0);
      const payload = b.slice(4);
      const p = this.pending.get(id);
      if (p?.writer) {
        p.writer.write(payload).catch(() => { // ブラウザが切れた
          this.pending.delete(id);
          try { this.vm()?.send(JSON.stringify({ t: "req-abort", id })); } catch {}
        });
      } else if (p?.buffer) p.buffer.push(payload);
      else this.ctx.getWebSockets("b:" + id)[0]?.send(payload);
      return;
    }
    let m;
    try { m = JSON.parse(msg); } catch { return; }
    const p = this.pending.get(m.id);
    switch (m.t) {
      case "res": {
        if (!p?.resolve) return;
        const headers = new Headers();
        for (const [k, v] of m.headers || []) if (!DROP_RES.has(k.toLowerCase())) { try { headers.append(k, v); } catch {} }
        if (NULL_BODY.has(m.status)) {
          this.pending.delete(m.id);
          p.resolve(new Response(null, { status: m.status, headers }));
        } else {
          const { readable, writable } = new TransformStream();
          p.writer = writable.getWriter();
          p.resolve(new Response(readable, { status: m.status, headers }));
        }
        break;
      }
      case "res-end":
        if (p?.writer) p.writer.close().catch(() => {});
        this.pending.delete(m.id);
        break;
      case "res-err":
        if (p?.writer) p.writer.abort(new Error(m.message || "upstream error")).catch(() => {});
        else p?.reject?.(new Error(m.message || "upstream error"));
        this.pending.delete(m.id);
        break;
      case "ws-opened": p?.resolve?.({ protocol: m.protocol || "" }); break;
      case "ws-fail": p?.reject?.(new Error(m.message || "upstream websocket failed")); break;
      case "ws-text":
        if (p?.buffer) p.buffer.push(m.data);
        else this.ctx.getWebSockets("b:" + m.id)[0]?.send(m.data);
        break;
      case "ws-close": {
        const b = this.ctx.getWebSockets("b:" + m.id)[0];
        if (b) { try { b.close(closeCode(m.code), String(m.reason || "")); } catch {} }
        break;
      }
    }
  }
}
