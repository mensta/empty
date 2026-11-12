# ヘッドレスブラウザで HOME'S / at home を取る実験 (2026-11-12)

この文書は、セッションをコンパクトしても続きから再開できるようにするための記録。結果、決定事項、残件、再開の手順を書く。
スクリプトはこのディレクトリにある (実験用。`run.py` にはまだ組み込んでいない)。

## 1. 目的と、ユーザーの決定

- 目的: `requests` では HOME'S の 202 (WAF チャレンジ)、at home の認証ページに当たるので、ヘッドレスブラウザで取れるか試す。
- 決定 (ユーザー): 「**安定するなら HOME'S はヘッドレスのクリック方式で取る**」。
- `AGENTS.md` から、WAF のチャレンジを突破しない旨の文言を、ユーザーが外した (HOME'S の行の「WAF のチャレンジを突破する処理は入れない」と、プロキシの行の「プロキシは経路を変えるだけで、WAF のチャレンジは突破しない」の2か所)。
- ユーザーが、stealth を「**効き目があるかの検証**」として試してよいと許可した (2026-11-12 夜)。
- 私 (Claude) が置いた境界: 出てきた人間確認のパズルを解く処理はしない。IP を変えて回避する工夫 (プロキシでの回避) はしない。弾かれたらその場で止める (取り直しで連打しない)。個人利用・低頻度に留める。各サイトの利用規約は未確認 (HOME'S も at home も)。

## 2. 環境

- root なし。Playwright は Node のグローバル版 (`/usr/local/share/npm-global/lib/node_modules/playwright`、1.64.1)。Python 版は入っていない。
- Chromium は `~/.cache/ms-playwright/` に2版ある。既定は `chromium_headless_shell-1248` (ヘッドレス専用)。完全版 `chromium-1248` もある。
- Chromium の共有ライブラリが足りない (libnspr4 など)。`python3 setup_libs.py <dir>` で、Debian ミラーから展開する (完全版には `--full` も)。
  `export LD_LIBRARY_PATH=<dir>/usr/lib/aarch64-linux-gnu:<dir>/lib/aarch64-linux-gnu` をしてから `node` を動かす。`/tmp/opencode/libs` に展開済みだが、`/tmp` は消えることがある。
- 完全版 Chromium は、さらに `libatk-bridge-2.0.so.0` と `libcups.so.2` が足りない (`setup_libs.py --full` で入る)。
- スクリプトは、作業ディレクトリに `pages/` と `details/` を作って HTML を保存する (リポジトリには入れない。掲載元の著作物)。
- この環境の IP はクラウド (データセンター)。サイトが IP の評判で判定していると、ブラウザの工夫が効かない可能性がある。

## 3. 実験の結果 (時系列)

### HOME'S

| 試したこと | 結果 |
|---|---|
| 素のヘッドレス (User-Agent が `HeadlessChrome`) で1ページ | **403** 「Request blocked」 (1回) |
| User-Agent の `HeadlessChrome` を `Chrome` に置換して1ページ | 200、1.7秒。30棟 (部屋の重複を除くと57室) |
| 60秒あけて、もう1回 | 200 |
| 巡回 (6秒間隔、画像・フォントなし、同じブラウザ)、2ページ目以降は**URLを直接開く** | 1ページ目は成功、**2ページ目と3ページ目は 405** 「Let's confirm you are human」。止めた |
| 同じ設定で、2ページ目以降を**「次ヘ」リンクのクリック**で進む (東横線 1LDK) | **6ページ全部成功** (最終ページで「次ヘ」がなくなって終了) |
| クリックで、東横線の3間取り (1LDK・2DK・2LDK) をまとめて | **7ページ全部成功** (188棟)。続けて**目黒線の1ページ目をURL直接**で開いたら **405** で止めた |

- 傾向: **URLを直接開くと弾かれ、クリックで進むと通る**。ただし各1〜2回の試行で、確率的な要素もあるので断定できない。
- 同じ IP から `requests` では HOME'S が取れる日もある (確率的に 202)。

### at home

| 試したこと | 結果 |
|---|---|
| `requests` (短時間に5〜6回、間隔なしの検証) | HTTP 200 の「認証中」ページ (0件)。通常のページでも。しばらくして回復 |
| ブラウザ (User-Agent と Client Hints を Chrome に揃えた状態)、1ページ目 URL、2ページ目は番号リンクをクリック | 1ページ目は成功 (30棟、`div.room-info` 115)。**2ページ目 (クリック) は認証ページ**。止めた (23:31) |

ログ: `results/athome_s0_2026-11-12_2331.log`。

### 予約済みで実行中だった実験 (この文書を書いた時点では結果が出ていない)

2026-11-12 23:47に、HOME'S の一覧 (東横線・目黒線、3間取り、クリック、User-Agent と Client Hints を Chrome に揃えた状態) を `hm_lists.mjs` で自動実行する予約があった。終了すると、ログが `results/homes_s0_clienthints_2026-11-12_2347.log` (と `.json`) に自動でコピーされる (コピー用の監視を別に動かしていた)。ファイルがなければ、予約が実行されなかったか、`/tmp` が消えている。見るポイント: 東横線7ページが再び通るか、目黒線の1ページ目 (URL直接) がまた405か。

## 4. 分かったこと

- **一覧の中身は、サーバー側で描画済み**。元のHTMLと、JS実行後のHTMLで、一覧は同じ。ブラウザで取っても、`requests` より多くのデータは取れない (負荷は増える。1ページで約100〜140リクエスト)。
- HOME'S の一覧は、同じ部屋への `a.prg-detailAnchor` が2つずつある (PC用とSP用)。重複を除くこと。
- HOME'S の件数表示「N 件 (総物件数: M 件)」の N は**部屋の数** (棟の数ではない)。1ページは30棟。東横線の1LDKは約6ページ、目黒線は約8ページ。3間取りまとめると、東横線は7ページ。
- HOME'S の間取りコード (フォームのラベルで確認): `cond[madori][15]`=1LDK、`[23]`=2DK、`[25]`=2LDK。複数指定できる。15は1SLDKも含むので、あとで完全一致で絞る。
- HOME'S の「次ヘ」リンク (「ヘ」がカタカナ) は `?page=2` だけで、条件のクエリを持たない。サーバーが条件を覚えているので、クリックでは条件が保たれた。`requests` で Cookie を毎回捨てる運用では、条件を毎回URLに付ける必要がある。
- HOME'S の部屋リンクは `target="_blank"` (別タブで開く)。
- at home のページ送りは、ページ番号のリンク (`.../list/page2/`)。並び替えは `?sort=33` (新着順)。リンクには `sort` が付かない。
- **User-Agent だけ変えても、`sec-ch-ua` に `HeadlessChrome` が残る** (ローカルのサーバーで確認)。`hm_common.mjs` の `open()` が、`Emulation.setUserAgentOverride` (`userAgentMetadata` つき) で、User-Agent と Client Hints を Chrome に揃える。`navigator.webdriver` は触らず `true` のまま。
  - 別タブ (popup) には、この上書きが自動では届かない。詳細ページを `target="_blank"` のクリックで開くなら、別タブの扱いに注意 (リンクの `target` を外して同じタブで開き、戻る、などを検討)。
- HOME'S から増える部屋は少ない: 東横線の一覧272室のうち、条件に合うのが152室、今の候補と重なりそうなのが約108室で、新しく詳細ページが要りそうなのは約44室 (簡易な照合)。

## 5. 次にやる実験 (stealth の効き目の検証。まだ未実施)

目的: 1つずつ足して、効くかを比べる (ユーザーの許可あり。境界は1.)。基準は、at home の「1ページ目 URL → 2ページ目 クリック」で弾かれる現状 (S0)。

| 段階 | 変更点 |
|---|---|
| S0 | 今の状態 (User-Agent と Client Hints が Chrome、ヘッドレス専用の Chromium) |
| S1 | 新しいヘッドレスモード (完全版 Chromium、`chromium.launch({ headless: true, channel: 'chromium' })`) |
| S2 | S1 + 起動引数 `--disable-blink-features=AutomationControlled` (`navigator.webdriver` を false に) |
| S3 | S2 + `puppeteer-extra-plugin-stealth` (npm 2.11.2) + `playwright-extra` (npm 4.3.6)。まだ入れていない |

- 各実験の間は約12分あける (連続すると、前の結果が次を汚す)。最後に S0 を、基準の再確認としてもう1回。
- 見ること: at home の2ページ目 (クリック) が通るか。HOME'S は、目黒線の1ページ目 (URL直接) が通るか、東横線7ページがまた通るか。
- 結果の読み方: 通れば効いた可能性。ただし1回では確率的な要素と区別できない。IP の評判が原因なら、どの段階でも効かない。

## 6. 安定していた場合の組み込み案 (HOME'S)

1. 一覧: 東横線・目黒線を、3間取りまとめて、クリックで最後まで (約15ページ)。路線の切り替えは、URL直接だと弾かれたので、サイト内のリンクで移動する方法を試す。
2. 絞り込み: 既存の `search_sites.filter_rows(..., include_admin=True)` と、今の候補との照合 (`hm_targets.py`)。
3. 詳細: 候補にない部屋だけ、一覧からリンクをクリックして開く (`hm_details.mjs`。未実行)。`sites.detail_homes` で読む。
4. Python から Node を呼ぶ薄いラッパーを `search_sites` に足し、`run.py --homes-browser` で切り替える。ブラウザが使えない環境では、これまでの `requests` に戻す。
5. 失敗したら止めて、HOME'S を外して続行する (これまで通り)。

## 7. ブラウザとは別の、未了の事項

- **未コミットの変更**: 家賃+管理費 19万円以下の判定 (`run.py --include-admin`、`suumo_scraper.py`、`search_sites.py`、`validate.py`、`candidates.py`、`tests/test_rent_cap.py`、`LESSONS.md`、`README.md`)、データ (`data/candidates.json` 280→209件、`data/conditions.json`)。`AGENTS.md` の変更はユーザー自身のもの (私の変更と混ぜない)。`data/plans.json` は git に入っていない (279→208枚に絞った)。
- **S3 は更新済み** (209件。`s3://live-my-life/artifacts/rental-candidates/`)。公開 URL (CloudFront) は未確認 (URL を聞けていない)。元の `index.html` は `/tmp/opencode/backup/s3_index_before.html` (`/tmp` なので消えるかも)。
- 構造が「その他」の5件が「鉄骨・ALC」に入っている (木造かもしれない。アーク五本木の備考に「木造」)。扱いをユーザーに確認する。
- 同じ駅・広さ・家賃で複数行の疑いが6グループ。
- 提案済み・未実装: `run.py` が段階ごとの件数 (`data/funnel.json`) を出す。at home / CHINTAI の URL での絞り込み (CHINTAI は `ct=190&j=5` で 1,869件が340件に減ることを確認済み。at home は JS に `PRICEFROM` / `PRICETO` / `EKITOHO` / `CHIKUNENSU` という名前が見つかったが、URL のクエリ名かは未確認)。リクエスト時刻をファイルに保存して、プロセスをまたいで間隔を守る (今の `web.Pacer` はプロセス内だけ)。
- 増分取得 (`known_ids.py`、`--incremental-others`) は実装・コミット済み。実サイトでの通しは、CHINTAI だけ確認済み。

## 8. 動かし方

```bash
cd <作業ディレクトリ>          # pages/ details/ が作られる
export LD_LIBRARY_PATH=...      # setup_libs.py の出力どおり
node hm_lists.mjs               # HOME'S 一覧 (クリック)。弾かれたら止まる。環境変数 GAP (秒、既定6) LINES (toyoko,meguro)
python3 hm_targets.py           # 一覧から詳細ページの対象を決める (targets.json)
node hm_details.mjs             # 詳細 (未検証。LIMIT で件数を制限できる)
node at_lists.mjs               # at home 一覧 (クリック、MAXP で最大ページ)
```

- 時間のかかる実行は、バックグラウンド (`nohup ... &`) で動かして、`grep` でログを短く確認する (ユーザーの指示)。
- 前回のアクセスから約12分あけてから、次の実験をする。
- `results/` に、実験ごとのログを残す。
