// QR ログイン版: パスワード不要。表示された URL をサブ機で開いて承認し、PIN をアプリに入力する。
import { loginWithQR, loginWithAuthToken } from "@evex-dev/linejs";
import { FileStorage } from "@evex-dev/linejs/storage";

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

client.on("message", async (m) => {
	console.log("受信:", m.text);
	if (m.text === "!ping") await m.reply("pong!");
});
client.on("square:message", async (m) => {
	if (m.text === "!ping") await m.reply("pong!");
});
client.listen();
console.log("LISTENING");
