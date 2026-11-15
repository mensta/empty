// 会話履歴を読む(読み取り専用)。bot-qr.mjs でログイン済みの session.json を使う。
// 使い方: node history.mjs            → 参加中のチャット一覧
//         node history.mjs <番号> [件数] → そのチャットの直近メッセージ(新しい順)
import { loginWithAuthToken } from "@evex-dev/linejs";
import { FileStorage } from "@evex-dev/linejs/storage";

const storage = new FileStorage("./session.json");
const token = await storage.get("userAuthToken");
if (!token) throw new Error("session.json がありません。先に bot-qr.mjs でログインしてください");

const client = await loginWithAuthToken(token, { device: "ANDROIDSECONDARY", storage });
const chats = await client.fetchJoinedChats();

const [idx, limit = "20"] = process.argv.slice(2);
if (idx === undefined) {
	chats.forEach((c, i) => console.log(i, c.name ?? c.mid));
} else {
	const chat = chats[Number(idx)];
	if (!chat) throw new Error("その番号のチャットはありません");
	for (const m of await chat.fetchMessages(Number(limit))) {
		console.log(new Date(Number(m.raw.createdTime)).toLocaleString("ja-JP"), m.raw.from, "|", m.text ?? "(テキスト以外)");
	}
}
process.exit(0);
