// verifyAccess の単体テスト: ダミーの RSA 鍵と JWKS を使う（worker.js を Node で読み込める形に加工）
import fs from "node:fs";
import crypto from "node:crypto";
import os from "node:os";
import path from "node:path";
const src = fs.readFileSync(new URL("../../worker/src/worker.js", import.meta.url), "utf8")
  .replace('import { DurableObject } from "cloudflare:workers";', "class DurableObject {}")
  .replace(/new WebSocketRequestResponsePair/g, "(0,0)&&new Object") + "\nexport { verifyAccess, authBrowser };";
const tmp = path.join(os.tmpdir(), `worker-test-${process.pid}.mjs`);
fs.writeFileSync(tmp, src);
const { verifyAccess, authBrowser } = await import(tmp);
fs.unlinkSync(tmp);

const { publicKey, privateKey } = crypto.generateKeyPairSync("rsa", { modulusLength: 2048 });
const jwk = { ...publicKey.export({ format: "jwk" }), kid: "k1", alg: "RS256", use: "sig" };
const other = crypto.generateKeyPairSync("rsa", { modulusLength: 2048 });
const TEAM = "team.cloudflareaccess.com", AUD = "aud123";
globalThis.fetch = async (u) => { if (u === `https://${TEAM}/cdn-cgi/access/certs`) return new Response(JSON.stringify({ keys: [jwk] })); return new Response("no", { status: 404 }); };
const b = (o) => Buffer.from(JSON.stringify(o)).toString("base64url");
const sign = (payload, key = privateKey, kid = "k1") => {
  const h = b({ alg: "RS256", kid }), p = b(payload);
  const s = crypto.sign("sha256", Buffer.from(`${h}.${p}`), key).toString("base64url");
  return `${h}.${p}.${s}`;
};
const now = Math.floor(Date.now() / 1000);
const good = { aud: [AUD], iss: `https://${TEAM}`, exp: now + 600 };
const env = { ACCESS_TEAM: TEAM, ACCESS_AUD: AUD };
const req = (t) => new Request("https://x/", { headers: t ? { "cf-access-jwt-assertion": t } : {} });
let fail = 0;
const expect = async (name, tok, want) => {
  const got = await verifyAccess(req(tok), env);
  const ok = want === null ? got === null : typeof got === "string" && got.includes(want);
  console.log(ok ? "PASS" : "FAIL", name, got ?? "");
  if (!ok) fail++;
};
await expect("valid token", sign(good), null);
await expect("no token", null, "no Access token");
await expect("expired", sign({ ...good, exp: now - 10 }), "expired");
await expect("wrong audience", sign({ ...good, aud: ["other"] }), "bad audience");
await expect("wrong issuer", sign({ ...good, iss: "https://evil.example" }), "bad issuer");
await expect("signed with another key", sign(good, other.privateKey), "bad signature");
await expect("unknown kid", sign(good, privateKey, "zzz"), "unknown signing key");
await expect("garbage", "a.b.c", "malformed");
console.log("authBrowser unconfigured →", await authBrowser(req(sign(good)), {}));
console.log(fail ? `${fail} FAILED` : "ALL PASS");
process.exit(fail ? 1 : 0);
