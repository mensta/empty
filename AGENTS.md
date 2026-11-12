# このリポジトリで作業するときの前提

東横線・目黒線の賃貸 (既定: 1LDK・2DK・2LDK。`--layout` で変更) を SUUMO / HOME'S / at home / CHINTAI から集め、条件で絞った候補を、ローカルのビューアで見る。アーティファクト (Claude) にも同じ候補を反映できる。

## よく使うコマンド
- 候補を作る: `python run.py` (約13分。条件は `--help`。`--from-csv raw.csv` で検索を省略)
- テスト: `python -m unittest discover -s tests -v`
- 画面をローカルで見る: `python scripts/build_viewer.py` のあと、リポジトリ直下で `python -m http.server 8000`、ブラウザで http://localhost:8000/viewer/ (ページ `artifact/index.html` を直したら build を再実行)
- アーティファクトへ反映: `python scripts/sync_artifact.py` (データが変わっていなければ何もしない。`--dry-run` で判定と指示だけ表示。`--force` で変わっていなくても反映)
  - 内部で `claude -p --model claude-haiku-5-5` を二回呼ぶ。`claude` がログイン済みで、Artifact / ArtifactData が使えることが前提。
  - 状態は `data/artifact_state.json` (blob の id、version、データのハッシュ)。手で書き換えない。
- 反映用ドキュメントだけ作る: `python artifact_docs.py --candidates <blob id> --plans <blob id> --conditions <blob id>`

## 守ること
- 取得は低頻度で。待ち時間を詰めない (既定 1.5 秒)。HTTP 202 や空の応答が返るのは普通。`web.fetch_soup` が取り直す。
- HOME'S は任意 (取れなくてよい)。CloudFront の WAF が確率的にチャレンジ (202) を返すためで、`collect` は取れなければそのサイトを外して続行する。取れなくても失敗扱い・やり直しをしない。WAF のチャレンジを突破する処理は入れない。
- プロキシ経由で取得するときは `python run.py --proxy http://[user:pass@]host:port` (環境変数 `RENTAL_PROXY` でも可。`candidates.py` / `search_sites.py` / `suumo_scraper.py` の単体実行にも `--proxy` がある)。セッションは必ず `web.new_session()` で作る (`requests.Session()` を直接呼ばない)。URL は認証情報を含むので、ログには `web.describe_proxy` の結果だけを出す。プロキシは経路を変えるだけで、WAF のチャレンジは突破しない。
- `--proxy urban-jp` は Urban VPN の日本のサーバーだけから1台選んで使う (`scripts/urban/urban_proxy.mjs`。他の国にはフォールバックしない。SUUMO / HOME'S は日本以外の出口を 503 / 403 で拒否する)。初回だけ `cd scripts/urban && npm install` が必要 (Node 20 以上)。選んだ後に suumo.jp:443 への CONNECT を確認し、通らなければ別のサーバーを試す。ラッパー (`@becauseyes/urbanvpn-api-wrapper`) は AGPL-3.0 なので、このディレクトリの別プロセスでだけ使い、Python 側に取り込まない。
- 新しい取得処理・パーサーは `web.fetch_soup` を通し、不具合を直したら `tests/` にその再現ケースを足す。`LESSONS.md` にも追記する。
- `run.py` の検証 (`validate.py`) で止まったら、出力を上書きしていない。原因を直してから再実行する (検証を緩めない)。
- 数字は自動計算が正しいことが多い。手計算と食い違ったら、まず入力 (掲載の記載) を疑って確かめる。
- 画面の確認: ローカルのビューアは、ヘッドレス Chromium で描画を確かめられる。アーティファクト側の描画は確認できない。確認していないことを確認したと言わない。
- 間取り図や写真は掲載元の著作物。リポジトリは private に保ち、アーティファクトは共有しない (共有するときは先にユーザーに聞く)。
- ページ本体 (`artifact/index.html`) は、ローカルとアーティファクトの両方で使う。`dash` を新しく呼ぶときは `viewer/dash-shim.js` にも同じ API を足す。

## 構成
`run.py` (入口) → `suumo_scraper.py` (SUUMO 検索) → `candidates.py` (構造・初期費用) → `others.py` / `search_sites.py` / `sites.py` → `plans.py` (間取り図) → `validate.py` → `data/*.json`

- 画面: `artifact/index.html` (正本) → `scripts/build_viewer.py` → `viewer/index.html` (+ `viewer/dash-shim.js`, `viewer/tokens.css`)
- アーティファクト反映: `scripts/sync_artifact.py` → `artifact_docs.py` → (Claude に `scripts/sync_upload_prompt.md` / `scripts/sync_apply_prompt.md` の指示を渡す)

## 注意 (Claude の道具について)
- `Artifact` / `ArtifactData` は Claude の道具。opencode などからは直接使えない。反映は必ず `scripts/sync_artifact.py` 経由で行う。
- 手で反映する場合の手順は `ARTIFACT.md` を参照 (参考用)。
