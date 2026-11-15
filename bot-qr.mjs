// QR ログイン版: パスワード不要。表示された URL をサブ機で開いて承認し、PIN をアプリに入力する。
import { loginWithQR, loginWithAuthToken } from "@evex-dev/linejs";
import { FileStorage } from "@evex-dev/linejs/storage";
import fs from "node:fs";

const storage = new FileStorage("./session.json"); // 秘密情報。コミット禁止
const opts = { device: "ANDROIDSECONDARY", storage };

const saved = await storage.get("userAuthToken");
const client =
	typeof saved === "string" && saved
		? await loginWithAuthToken(saved, opts)
		: await loginWithQR(
				{
					onReceiveQRUrl: (url) => console.log("QR_URL:", url),
					onPincodeRequest: (pin) => console.log("PINCODE:", pin),
				},
				opts,
			);

client.base.on("update:authtoken", (t) => storage.set("userAuthToken", t));
if (client.base.authToken) await storage.set("userAuthToken", client.base.authToken);
console.log("LOGIN_OK");

// 受信箱: 自分以外が送ったメッセージを inbox.jsonl に追記する(Claude 側がここを読む)
client.on("message", async (m) => {
	if (m.isMyMessage) return;
	const entry = { time: new Date().toISOString(), id: m.raw.id, from: m.from.id, to: m.to.id, toType: m.to.type, text: m.text ?? null };
	fs.appendFileSync("./inbox.jsonl", JSON.stringify(entry) + "\n");
	console.log("受信:", m.text);
	if (m.text === "!ping") await m.reply("pong!");
});
client.on("square:message", async (m) => {
	if (m.text === "!ping") await m.reply("pong!");
});
// 送信窓口: outbox/*.json({"to":"<mid>","text":"..."})を拾って送信し、sent/ へ移す
fs.mkdirSync("./outbox/sent", { recursive: true });
setInterval(async () => {
	for (const f of fs.readdirSync("./outbox").filter((n) => n.endsWith(".json"))) {
		const path = `./outbox/${f}`;
		try {
			const { to, text, e2ee = true } = JSON.parse(fs.readFileSync(path, "utf8"));
			await client.base.talk.sendMessage({ to, text, e2ee });
			console.log("送信:", to);
		} catch (e) {
			console.error("送信失敗:", f, e?.constructor?.name, e?.message ?? e, JSON.stringify(e?.data ?? null));
		}
		fs.renameSync(path, `./outbox/sent/${f}`);
	}
}, 2000);

client.listen();
console.log("LISTENING");
