# VM 中継（Cloudflare Workers）

クラウド VM（外から入れない環境）で動かしたサーバーを、認証つきの URL で外から開けるようにする中継です。
VM から **外向きの WebSocket（443）** をつなぐだけなので、プロキシ経由の 443 しか出られない環境でも動きます。

```
ブラウザ ─→ Cloudflare Access（ログイン）─→ Worker ─→ Durable Object ←─ WebSocket ─ VM の expose.mjs ─→ localhost:PORT
```

- `worker/` … 中継の Worker（Durable Object 1 つ。WebSocket Hibernation 使用）
- `client/expose.mjs` … VM で動かすクライアント。HTTP と WebSocket（HMR など）、SSE、大きなファイルを中継する
- `client/test/` … ローカルでの通しテスト（ダミーサーバー / e2e / JWT 検証）

## 認証の仕組み（2 系統）
| 方向 | 方法 |
|---|---|
| ブラウザ → Worker | Cloudflare Access。Worker 側でも `Cf-Access-Jwt-Assertion` の署名・aud・iss・exp を検証する。**`ACCESS_TEAM` / `ACCESS_AUD` が未設定だと全て 403（フェイルクローズ）** |
| VM → Worker | `X-Tunnel-Key` ヘッダー（`TUNNEL_KEY` と一致）。`/_tunnel/connect` だけが対象 |

## デプロイ手順
1. **Worker をデプロイ**（どちらか）
   - Cloudflare ダッシュボード → Workers & Pages → Create → Import a repository → このリポジトリ。
     Root directory は `tunnel/worker`、Deploy command は `npx wrangler deploy`。
   - または Node のある環境で `cd tunnel/worker && npm i && npx wrangler deploy`。
2. **Worker の変数**（Settings → Variables and Secrets）
   - `TUNNEL_KEY`（Secret）: 長いランダム文字列。例: `openssl rand -hex 32`
   - `ACCESS_TEAM`（Text）: 例 `myteam.cloudflareaccess.com`
   - `ACCESS_AUD`（Text）: 手順 3 で作る Access アプリケーションの Application Audience (AUD) Tag
3. **Cloudflare Access をかける**（Zero Trust → Access → Applications → Self-hosted）
   - Worker のホスト名（`vm-relay.<アカウント>.workers.dev`。Workers の Settings → Domains & Routes の Cloudflare Access も使える）を登録し、
     自分のメールだけを Allow するポリシーを作る。
   - VM のクライアントが Access で止まらないよう、次のどちらかにする。
     - **A. サービストークン（推奨）**: Access → Service Auth でトークンを作り、ポリシーに `Service Auth` を追加。クライアントに `CF_ACCESS_CLIENT_ID` / `CF_ACCESS_CLIENT_SECRET` を渡す。
     - **B. パスのバイパス**: `/_tunnel/connect` だけを Bypass ポリシーの別アプリケーションにする（合言葉 `X-Tunnel-Key` だけで守られる）。
4. **VM で公開**
   ```bash
   cd tunnel/client && npm install
   TUNNEL_URL=wss://vm-relay.<アカウント>.workers.dev/_tunnel/connect node expose.mjs 3000
   ```
   合言葉やサービストークンは、環境のネットワークシークレット（ヘッダー自動挿入）に登録すると、VM 側で値を扱わずに済む。
   その場合 `TUNNEL_KEY` などの環境変数は不要。

## ローカルで試す（Cloudflare 不要）
```bash
cd tunnel/worker && printf 'TUNNEL_KEY=testkey\nALLOW_PUBLIC=1\n' > .dev.vars && npx wrangler dev --port 8787 &
cd tunnel/client && node test/dummy.mjs 8099 &
TUNNEL_URL=ws://127.0.0.1:8787/_tunnel/connect TUNNEL_KEY=testkey node expose.mjs 8099 &
node test/e2e.mjs      # 11 項目
node test/jwt.mjs      # Access JWT 検証の単体テスト
```
`ALLOW_PUBLIC=1` はテスト専用（Access なしで通す）。本番の Worker には設定しないこと。

## 仕様と制限
- 公開できるのは 1 つのローカルポート（1 本のトンネル）。`Host` はローカルアプリ向けに `localhost:PORT` へ、`Origin` は `http://localhost:PORT` へ書き換える（`--keep-origin` で保持）。
- VM が起動していて `expose.mjs` が動いている間だけ公開される。切断時は 502（再接続は自動）。
- 応答開始まで 60 秒で 504。HTTP / WebSocket が対象で、生の TCP は不可。
- 無料プラン: Workers は 1 日 10 万リクエスト、CPU 約 10ms/回。Durable Object は SQLite 型のみ。ポーリング間隔の短い画面を開きっぱなしにしない。
