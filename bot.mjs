// LINEJS 最小サンプル: メール+パスワードで初回ログイン → authToken を保存 → 次回以降はトークンで再ログイン
// 使い方: LINE_EMAIL=... LINE_PASSWORD=... node bot.mjs
import { Client } from "@evex-dev/linejs";
import { BaseClient } from "@evex-dev/linejs/base";
import { FileStorage } from "@evex-dev/linejs/storage";

const storage = new FileStorage("./session.json"); // 秘密情報。コミット禁止(.gitignore済み)
const TOKEN_KEY = "userAuthToken";
const base = new BaseClient({ device: "IOSIPAD", storage });

// トークンはログイン中にローテーションされることがあるので、ログイン前にリスナーを付ける
let pendingSave = Promise.resolve();
base.on("update:authtoken", (token) => {
	base.authToken = token;
	pendingSave = pendingSave
		.then(() => storage.set(TOKEN_KEY, token))
		.catch(() => console.error("トークンの保存に失敗しました"));
});
// 初回ログイン時、表示された PIN を LINE アプリ側で入力する(E2EE鍵の用意)
base.on("pincall", (pin) => console.log("LINEアプリでこの PIN を入力してください:", pin));

const saved = await storage.get(TOKEN_KEY);
if (typeof saved === "string" && saved) {
	await base.loginProcess.login({ authToken: saved });
} else {
	const { LINE_EMAIL: email, LINE_PASSWORD: password } = process.env;
	if (!email || !password) throw new Error("LINE_EMAIL / LINE_PASSWORD を環境変数で指定してください");
	await base.loginProcess.login({ email, password });
}
await pendingSave;

const client = new Client(base);

client.on("message", async (message) => {
	console.log("受信:", message.text);
	if (message.text === "!ping") await message.reply("pong!");
});
client.on("square:message", async (message) => {
	if (message.text === "!ping") await message.reply("pong!");
});

client.listen();
console.log("待受開始 (Ctrl+C で終了)");
