// LINE サブ垢 操作 UI (ローカル専用)。bot と Web UI を 1 プロセスで動かす。
// 使い方: npm start → ブラウザで http://localhost:3000
import http from "node:http";
import fs from "node:fs";
import QRCode from "qrcode";
import { loginWithQR, loginWithAuthToken, TalkMessage } from "@evex-dev/linejs";
import { FileStorage } from "@evex-dev/linejs/storage";

const PORT = Number(process.env.PORT ?? 3000);
const HOST = "127.0.0.1"; // 外部公開しない
const DEVICE = "ANDROIDSECONDARY";
const TOKEN_KEY = "userAuthToken";
const storage = new FileStorage("./session.json"); // 認証情報。コミット・共有禁止
const opts = { device: DEVICE, storage };

const state = { status: "starting", qr: null, pin: null, error: null, me: null };
let client = null;
const names = new Map();

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const rep = (k, v) => (typeof v === "bigint" ? v.toString() : v);

// ---------- ログイン ----------
async function onReady(c) {
	client = c;
	client.base.on("update:authtoken", (t) => storage.set(TOKEN_KEY, t));
	if (client.base.authToken) await storage.set(TOKEN_KEY, client.base.authToken);
	client.on("message", (m) => {
		if (m.isMyMessage) return;
		fs.appendFileSync("./inbox.jsonl", JSON.stringify({ time: new Date().toISOString(), id: m.raw.id, from: m.from.id, to: m.to.id, text: m.text ?? null }) + "\n");
		if (m.text === "!ping") m.reply("pong!").catch(() => {});
	});
	client.listen();
	const p = client.base.profile;
	state.me = { mid: p?.mid, name: p?.displayName };
	state.status = "ready";
	state.qr = state.pin = state.error = null;
}

async function loginWithSaved() {
	const saved = await storage.get(TOKEN_KEY);
	if (typeof saved !== "string" || !saved) return (state.status = "need-login");
	try {
		await onReady(await loginWithAuthToken(saved, opts));
	} catch (e) {
		state.status = "need-login";
		state.error = `保存済みトークンでログインできません(期限切れの可能性): ${e?.message ?? e}`;
	}
}

async function startQrLogin() {
	if (state.status === "qr" || state.status === "ready") return;
	state.status = "qr"; state.qr = null; state.pin = null; state.error = null;
	try {
		const c = await loginWithQR(
			{
				onReceiveQRUrl: async (url) => (state.qr = await QRCode.toDataURL(url, { width: 360, margin: 3 })),
				onPincodeRequest: (pin) => (state.pin = pin),
			},
			opts,
		);
		await onReady(c);
	} catch (e) {
		state.status = "need-login";
		state.error = `QR ログインに失敗: ${e?.message ?? e}`;
	}
}

// ---------- LINE 操作 ----------
async function contactInfo(mids) {
	const need = mids.filter((m) => m.startsWith("u") && !names.has(m));
	if (need.length) {
		const r = await client.base.talk.getContactsV2({ mids: need });
		for (const m of need) {
			const c = r.contacts?.[m]?.contact;
			names.set(m, { name: c?.displayName ?? m.slice(0, 8), buddy: !!c?.capableBuddy });
		}
	}
	for (const m of mids.filter((m) => !m.startsWith("u") && !names.has(m))) {
		try { names.set(m, { name: (await client.getChat(m)).name ?? m.slice(0, 8), buddy: false }); }
		catch { names.set(m, { name: m.slice(0, 8), buddy: false }); }
	}
	return (m) => names.get(m) ?? { name: m, buddy: false };
}

async function listChats() {
	const boxes = (await client.base.talk.getMessageBoxes({ messageBoxListRequest: {} })).messageBoxes;
	const info = await contactInfo(boxes.map((b) => b.id));
	return boxes
		.map((b) => ({ mid: b.id, name: info(b.id).name, unread: Number(b.unreadCount ?? 0), time: Number(b.lastDeliveredMessageId?.deliveredTime ?? 0) }))
		.sort((a, b) => b.time - a.time);
}

const TYPE_LABEL = { FLEX: "(Flex メッセージ)", STICKER: "(スタンプ)", IMAGE: "(画像)", VIDEO: "(動画)", AUDIO: "(音声)", LOCATION: "(位置情報)", CALL: "(通話)" };

async function listMessages(mid) {
	const raws = await client.base.talk.getRecentMessagesV2({ messageBoxId: mid, messagesCount: 50 });
	const myMid = client.base.profile?.mid;
	const out = [];
	for (const raw of raws) {
		let text = null;
		try { text = (await TalkMessage.fromRawTalk(raw, client)).text; } catch { text = "(復号できません)"; }
		out.push({ id: String(raw.id), time: Number(raw.createdTime), mine: raw.from === myMid, text: text || TYPE_LABEL[raw.contentType] || `(${raw.contentType})` });
	}
	return out.sort((a, b) => a.time - b.time);
}

async function sendText(to, text) {
	const info = await contactInfo([to]);
	// 公式アカウント(capableBuddy)は E2EE 非対応。個人は E2EE ありで送る
	const e2ee = to.startsWith("u") && !info(to).buddy;
	await client.base.talk.sendMessage({ to, text, e2ee });
}

// 入力(URL / @ID / チケット URL)から連絡先を探す
async function lookupFriend(input) {
	input = String(input).trim();
	const m = input.match(/\/ti\/p\/([^?#\s]+)/);
	const key = decodeURIComponent(m ? m[1] : input);
	let c;
	if (key.startsWith("@") || !m) c = await client.base.talk.findContactByUserid({ searchId: key });
	else c = await client.base.talk.findContactByUserTicket({ ticketIdWithTag: key });
	if (!c?.mid) throw new Error("見つかりませんでした");
	return { mid: c.mid, name: c.displayName, status: c.statusMessage ?? "", buddy: !!c.capableBuddy, relation: c.relation };
}

async function myFriendUrl() {
	const f = "./friend-url.txt";
	if (fs.existsSync(f)) return fs.readFileSync(f, "utf8").trim();
	const t = await client.base.talk.generateUserTicket({ expirationTime: 0n, maxUseCount: -1 });
	const url = `https://line.me/ti/p/${t.id}`;
	fs.writeFileSync(f, url + "\n");
	return url;
}

// ---------- HTTP ----------
const json = (res, code, body) => { res.writeHead(code, { "content-type": "application/json; charset=utf-8" }); res.end(JSON.stringify(body, rep)); };
const readBody = (req) => new Promise((ok) => { let s = ""; req.on("data", (d) => (s += d)); req.on("end", () => ok(s ? JSON.parse(s) : {})); });

const server = http.createServer(async (req, res) => {
	try {
		// DNS rebinding / 他サイトからの操作対策
		const host = req.headers.host ?? "";
		if (!/^(localhost|127\.0\.0\.1)(:\d+)?$/.test(host)) return json(res, 403, { error: "forbidden host" });
		const url = new URL(req.url, "http://localhost");
		if (req.method === "POST" && req.headers["x-requested-with"] !== "ui") return json(res, 403, { error: "forbidden" });

		if (url.pathname === "/") { res.writeHead(200, { "content-type": "text/html; charset=utf-8" }); return res.end(fs.readFileSync("./public/index.html")); }
		if (url.pathname === "/jsqr.js") { res.writeHead(200, { "content-type": "text/javascript" }); return res.end(fs.readFileSync("./node_modules/jsqr/dist/jsQR.js")); }
		if (url.pathname === "/api/state") return json(res, 200, state);
		if (url.pathname === "/api/login/qr" && req.method === "POST") { startQrLogin(); return json(res, 200, { ok: true }); }

		if (state.status !== "ready") return json(res, 409, { error: "not logged in" });
		if (url.pathname === "/api/chats") return json(res, 200, await listChats());
		if (url.pathname === "/api/messages") return json(res, 200, await listMessages(url.searchParams.get("mid")));
		if (url.pathname === "/api/send" && req.method === "POST") { const b = await readBody(req); await sendText(b.to, b.text); return json(res, 200, { ok: true }); }
		if (url.pathname === "/api/friend/lookup" && req.method === "POST") return json(res, 200, await lookupFriend((await readBody(req)).input));
		if (url.pathname === "/api/friend/add" && req.method === "POST") { await client.base.relation.addFriendByMid({ mid: (await readBody(req)).mid }); return json(res, 200, { ok: true }); }
		if (url.pathname === "/api/myurl") return json(res, 200, { url: await myFriendUrl() });
		if (url.pathname === "/api/myqr.png") { const png = await QRCode.toBuffer(await myFriendUrl(), { width: 360, margin: 3 }); res.writeHead(200, { "content-type": "image/png" }); return res.end(png); }
		json(res, 404, { error: "not found" });
	} catch (e) {
		json(res, 500, { error: e?.message ?? String(e) });
	}
});

server.listen(PORT, HOST, () => console.log(`UI: http://localhost:${PORT}`));
await loginWithSaved();
console.log("status:", state.status);
