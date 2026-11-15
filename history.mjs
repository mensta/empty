// 会話履歴を読む(読み取り専用)。bot-qr.mjs でログイン済みの session.json を使う。
// 使い方: node history.mjs              → グループ+個人チャットの一覧(mid つき)
//         node history.mjs <mid> [件数]  → そのチャットの直近メッセージ(新しい順)
import { loginWithAuthToken, TalkMessage } from "@evex-dev/linejs";
import { FileStorage } from "@evex-dev/linejs/storage";

const storage = new FileStorage("./session.json");
const token = await storage.get("userAuthToken");
if (!token) throw new Error("session.json がありません。先に bot-qr.mjs でログインしてください");
const client = await loginWithAuthToken(token, { device: "ANDROIDSECONDARY", storage });

const boxes = (await client.base.talk.getMessageBoxes({ messageBoxListRequest: {} })).messageBoxes;
const [mid, limit = "20"] = process.argv.slice(2);

async function open(id) {
	return id.startsWith("u") ? await client.getUser(id) : await client.getChat(id);
}

if (!mid) {
	for (const b of boxes) {
		let name = "?";
		try { const o = await open(b.id); name = o.name ?? o.raw?.displayName ?? o.raw?.name ?? "?"; } catch {}
		console.log(b.id.startsWith("u") ? "個人" : "グループ", b.id, name);
	}
	console.log(`(${boxes.length} 件)`);
} else {
	const box = boxes.find((b) => b.id === mid);
	if (!box) throw new Error("そのチャットのメッセージボックスがありません");
	const raws = await client.base.talk.getRecentMessagesV2({ messageBoxId: box.id, messagesCount: Number(limit) });
	console.log(`(${raws.length} 件取得)`);
	for (const raw of raws) {
		let text;
		try { text = (await TalkMessage.fromRawTalk(raw, client)).text; } catch (e) { text = `(復号失敗: ${e.message})`; }
		console.log(new Date(Number(raw.createdTime)).toLocaleString("ja-JP"), raw.from === client.base.profile?.mid ? "自分" : "相手", "|", text ?? "(テキスト以外)");
	}
}
process.exit(0);
