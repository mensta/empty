# 引き継ぎメモ (2026-11-12 夜 時点)

東横線・目黒線の賃貸候補 (1LDK・2DK・2LDK) を集めて、ローカルのビューアで見る。公開は S3 (CloudFront 経由)。作業の前提は `AGENTS.md`、落とし穴は `LESSONS.md`。Claude のアーティファクトは今後更新しない (旧手順は `ARTIFACT.md`、参考用)。

## 続きを始めるには (このブランチだけでできる)

```bash
git clone -b claude/amazing-archimedes-skfnqc https://github.com/mensta/empty rental-search   # private のまま扱う。PAT はコミットしない
cd rental-search
pip install -r requirements.txt
python -m unittest discover -s tests          # 70件通ること
python scripts/build_viewer.py                # viewer/index.html を作る
python -m http.server 8000                    # http://localhost:8000/viewer/
```

- `data/candidates.json`・`conditions.json`・`detail_cache.json`・`known_ids.json` は git に入っている。ビューアで候補は見られる。
- **間取り図 (`data/plans.json`、約3.5MB) は git に入っていない** (掲載元の著作物)。ビューアで間取り図を出す・S3 に間取り図を上げるには、次のどちらかが要る:
  - 前の人から tar で受け取り、`data/plans.json` と `data/plans/` に置く。
  - `python run.py` を走らせて作り直す (約20分。取得は低頻度のまま。下の注意を読む)。
- 公開: `python scripts/publish_s3.py` (`--dry-run` で確認)。AWS の認証が要る (`--profile`、既定は `$AWS_PROFILE`、なければ `mensta`)。認証情報はリポジトリに入れない。

## いまの状態

- 候補 **280室** (1LDK 253 / 2DK 20 / 2LDK 7。RC 218 / 鉄骨・ALC 62)。掲載は SUUMO 275 + CHINTAI 5。
- 条件 (既定。`run.py --help`): 家賃 19万円以下 (管理費は含めない)、徒歩10分以内、築35年以内、28㎡より広い、木造除外。他サイトの間取りは完全一致 (2SLDK などは入らない)。
- 公開済み: `s3://live-my-life/artifacts/rental-candidates/` に `index.html` と `plans/` (279枚) を上げた。**公開 URL (CloudFront) での表示は未確認** (URL を聞けていない)。確認は `python scripts/publish_s3.py --url <index.html の公開URL>`。
- プロキシ: `run.py --proxy <URL>` または `--proxy urban-jp` (日本のサーバーだけ。初回 `cd scripts/urban && npm install`)。プロキシは経路を変えるだけで、WAF のチャレンジは突破しない。全工程を `urban-jp` で通した確認はまだ (手で選んだ日本のサーバーでは、目黒線だけ通した)。
- テスト 70件、すべて通過。

## 未解決・注意

- **表示の確認が全部できていない**: このコンテナには Chromium がなく、ブラウザでの描画を確かめていない (ローカルのビューア、S3 の公開ページとも)。スマホの横スクロール (`min-width: 46rem`) も実機未確認。
- **at home は認証ページ (パズル) が出て取れない状態になった** (取得が重なったため)。時間を置いてから、1回ずつ確かめる。突破はしない。
- **HOME'S** は WAF の 202 で外れる。間取りコードは 1LDK しか分からないので、2DK・2LDK は取っていない。
- **CHINTAI の 2DK** は、URL の形が分からず 404 (SUUMO の分だけ)。
- **ブランシェ目黒 (CHINTAI)** の管理費が 8.0万円で、総額 26.2万円。読み取りミスかもしれない (未確認)。
- 同じ駅・広さ・家賃の部屋が複数行で出る (アーク大岡山、ヴァンテジオ目黒Uno、ラヴィエール洗足など)。同じ建物の別の部屋か、同じ部屋の重複かは未確認。
- 家賃の上限は家賃だけにかかる。管理費込みで19万円を超える物件が71室ある。
- 初期費用は目安: 前家賃・日割り家賃を含まない。仲介手数料の記載がなければ1.1ヶ月分と仮定。保証料が読めない物件は含めない。at home は鍵交換などを含めていない。
- **同じ作業ツリーを別のセッションが同時に編集していたことがある** (`temp-user-5` の名前でコミットが入った)。作業前に `git status` と `git log` を見る。
- 間取り図の写真判定 (`plans.looks_like_photo`) はヒューリスティック。間取り図が1室ない (「図なし」)。

## 決めてもらう・次にやれること

- キッチンが LDK の中にある物件を除外したい (ユーザーの要望)。ただし1LDKは大半がそう。掲載のテキストに記載があるのは13室だけで、間取り図の目視が要る。「何を除外するか」(独立キッチンだけ残すのか) を先に決める。判定結果は `kitchen` 欄に保存し、画面でフィルタにする案。
- バストイレ別を必須条件にするか (今は条件にしていない。74室は掲載に「別」とある。CHINTAI・at home は設備欄を取っていない)。
- 管理費込みで家賃を絞るか。
- HOME'S・at home の再取得 (時間を置いて、1回ずつ)。
- いい部屋ネット (CSS のクラス名が不安定なので未実装)、神奈川県の他サイト対応、画面のメモ列。

## 増分取得 (2026-11-12 追加)

- `python run.py --incremental-others` で他サイトを新着順 + 既知ページで打ち切り (7日ごと・初回は全件)。状態は `data/known_ids.json` (git に入る。URL と日付のみ)。
- 実サイト確認済み: 並び替えのパラメータ3つ、CHINTAI の増分 (2リクエストで打ち切り)。**未確認**: HOME'S と at home の増分の通し (検証中に at home は認証ページ、HOME'S は 202 が続き、休ませた)。次に HOME'S が取れる日に `--incremental-others` を1回走らせて確かめる。
- スキル: `.opencode/skills/web-x-research` (X・Web 調査)、`.opencode/skills/rental-scraping-ops` (取得の運用、線引き、調査メモ)。opencode は再起動で読み込む。

## ヘッドレスブラウザの実験 (2026-11-12、進行中)

HOME'S / at home を、ヘッドレスブラウザの「リンクをクリックして進む」方式で取れるかの実験。結果・決定事項・次の実験・組み込み案は `scripts/browser_experiments/NOTES.md`。要点: User-Agent と Client Hints を Chrome に揃えると通る場面があり、HOME'S は「クリックで進む」と東横線7ページが通った (URL直接は405)。at home は2ページ目で弾かれた。stealth の効き目の検証 (S0〜S3) が次。ユーザーの方針: 安定するなら HOME'S はこの方式で取る。
