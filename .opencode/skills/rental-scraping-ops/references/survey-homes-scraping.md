# 賃貸ポータル(HOME'S / SUUMO / at home / CHINTAI)データ収集の実務調査

調査日: 2026-11-12。ワークスペースのコードは未変更。

## 1. 具体的な手法

- **requests/httpx + BeautifulSoup で一覧ページのみ取得(最多)**
  - guild-42/tokyo-rental-search-agent は 9 サイト対応。HOME'S は区ごとのスラッグ URL に `cond[sortby]=newdate&page=N` を付ける。
  - 同リポジトリの CHINTAI は `/tokyo/area/{code}/list/page{N}/?sort=2`、at home は `/chintai/tokyo/{slug}/list/?bukken-sort=newdate`。
  - https://github.com/guild-42/tokyo-rental-search-agent (src/scrapers/{base,homes,chintai,athome,suumo}.py)
- **SUUMO は plain requests で動く**
  - 一覧 URL は `/jj/chintai/ichiran/FR301FC001/?...&po1=25&pc=50&page=N` 形式(`pc` は 1 ページの件数、`po1` は並び順)。
  - 1 秒前後の sleep で全件取得する記事が多い。
  - https://qiita.com/tomyu/items/a08d3180b7cbe63667c9
  - https://qiita.com/t-hada/items/78e553371ba4f0d5b152
  - https://qiita.com/atsuken/items/23c0f0395514cafaf47d (Cloud Functions + BigQuery で毎日取得)
  - https://qiita.com/k5o/items/bd2aaa9df6049c02aa63 (Lambda + DynamoDB + LINE bot)
  - GAS の `UrlFetchApp` + Cheerio でスプレッドシートに書く例: https://github.com/renny-m/suumo-scraper
- **Playwright**
  - at home は Angular SSR で価格が不完全になる(「200万円」が「2万円」)ため Playwright 優先、という報告(売買の例)。https://qiita.com/bit-sap/items/38fca42fe1782f423c68
  - 一方、kyoto-land-tracker は同一の residential IP から SUUMO / at home を plain fetch で取得し、不動産ジャパンだけ Playwright。https://github.com/Bjork999/kyoto-land-tracker (scripts/scrape.mjs)
  - HOME'S は headed Chromium + 手動の人間確認(後述)。
- **HOME'S の隠し JSON / XHR / JSON-LD**
  - 今回の調査では HOME'S のこれらを使った事例は見つからなかった。HOME'S 事例は全て HTML セレクタ(`.prg-building`, `.bukkenName`, `.bukkenSpec`)。
- **保存検索メール通知の Gmail/GAS 解析**: 事例は見つからなかった。
- **ノーコード/SaaS**
  - Apify の japan-rent-market-scraper (SUUMO + at home + LIFULL)。README に「LIFULL は 1 ページのみ、ブロックされることがある」とあり、既定では LIFULL を外している。https://github.com/atushi1841/japan-rent-market-scraper
  - Bright Data の記事はベンダー広告色が強い。https://qiita.com/cynthia-brightdata/items/8422a63c587d6ba3581f
- **ユーザー自身が開いたページを読む方式**
  - Chrome 拡張 ie-sagashi (SUUMO/HOMES/CHINTAI/APAMAN): https://github.com/PMN-Bitcoin/ie-sagashi
  - Playwright で貼り付けた URL だけを取得する homes-app: https://github.com/DylanHHY/homes-app

## 2. ブロック対策(各ソースが実際にやっていること)

- **HOME'S の HTTP 202 は「ソフトスロットル」として扱われている。**
  - 202 の場合は 5s×1.8^n で最大 60s まで、最大 6 回リトライ。
  - 1 区ごとに try/except を分け、最もスロットルの強い渋谷区を最後に回す。
  - HOME'S の rate_limit は 3.0s、最大 5 ページ。
  - 10 分周期だと 202 で 1 サイクルが 12〜15 分に延び、サイクルを skip する。
  - 出典: tokyo-rental-search-agent の base.py / homes.py / docs/design-phase3.md
- **at home** は負荷時に「認証中」ページを HTTP 200・0 件で返す。同リポジトリでは区単位で分離して扱う。
- **homes-app** は headed Chrome でトップページを先に開いてから対象 URL へ移動する。"Let's confirm you are human" が出たら最大 120 秒待ち、ユーザーが手動で「Begin」を押す。物件間は 3 秒待つ。
- **汎用パターン**
  - UA ローテーションやブラウザ風ヘッダ、指数バックオフ、ブロック文言の検知、Playwright と通常取得の相互フォールバック(https://qiita.com/bit-sap/items/9b85e164c8e1084019fc)。
  - 同記事は「200→502→403→challenge の順で段階的に締め出される」と述べる。
- **クラウド VM の IP は弾かれ、住宅回線の IP なら通る**という報告(Akamai の銀行サイト。HOME'S の話ではない)。https://zenn.dev/ikahan/articles/akamai-datacenter-ip-403
- 作法として UA に bot 名と連絡先を書く、1 秒以上空ける、429/503 では `Retry-After` に従う、続くなら撤収する、という主張もある。https://qiita.com/zumiraku/items/95070856b6300caaee66
- 自分の環境から実測した結果:
  - `www.homes.co.jp/robots.txt` は 200 で取得できた。
  - 同サイトのトップ、規約候補 URL、`sitemap-bukken-detail-chintai.xml` は curl で 403。
  - webfetch での HOME'S 規約 URL は空応答だった。

## 3. 規約・法的見解

- **HOME'S の robots.txt**(実読):
  - `/chintai/` 一覧は Disallow されていない(`/chintai/b-*/tour/` のみ)。
  - 賃貸の sitemap(`sitemap-bukken-room-chintai.xml`, `sitemap-bukken-detail-chintai.xml`)が列挙されている。
  - Crawl-delay の記載はない。
- **SUUMO 規約**(実読。https://cdn.p.recruit.co.jp/terms/suu-t-1003/index.html):
  - 私的利用の範囲を超える使用を禁止(第2条)。
  - 商業目的利用の禁止(第3条(7))、運営を妨げる行為の禁止(第3条(6))。
  - 「スクレイピング」という語は無い。
  - robots.txt は `/chintai/*/__JJ_FR301FC001` などを Disallow。
- **HOME'S 利用規約**: 本文は読めていない。
- **Comfy 事件**
  - 個人開発の賃貸検索 Comfy が他サイトのデータを無断取得していたが、利用許諾を得られず閉鎖(2021/7/30)。
  - 開発者は弁護士に相談のうえ、規約が非商用を禁止していない SUUMO を取得元に変えた。SUUMO 側の回答は「規約を確認して」。
  - https://levtech.jp/media/article/focus/detail_493/
  - https://note.com/torum/n/n135306c1c118
- **不動産業界の立場**(torum、意見)
  - 個人利用で過剰負荷をかけなければ問題ないとする。
  - 取得データの再公開は、元付業者の広告承諾やおとり広告の観点でリスクがある。
  - 他社データへの依存は規約変更に弱いとも述べる。
  - https://note.com/torum/n/n135306c1c118
  - https://note.com/torum/n/nd6661f335008
- **対照例**: 個人検証用途に限定し、楽待のように規約でクローラーを明示禁止しているサイトは対象外にしている。https://github.com/JP-Mitsubachi/lpm-real-estate-aggregator

## 4. 効率化のコツ

- **新着順ソート + 早期停止**
  - SUUMO は `po1=25` + `pc=50`。「本日の新着」バッジが無いページで打ち切る(atsuken)。
  - HOME'S は `cond[sortby]=newdate`、CHINTAI は `sort=2`、at home は `bukken-sort=newdate`。
  - 条件は URL に埋め込む(家賃上限 `cond[monthmoneyroomh]=20.0`)。
- **SUUMO はページ数に上限(約 50 ページ)がある。** 区 × 間取り × 賃料帯に分割して各クエリを上限内に収める(tokyo-rental-search-agent の suumo.py)。
- **取得ページ数・合計件数の検証:** 「X件（総物件数：Y件）」を解析して取得率を警告する。
- **増分管理と通知の安全装置**
  - `known_ids.json` に物件 ID と初出日を持ち、NEW 判定に使う(kyoto-land-tracker)。
  - 初回はベースライン扱いで通知しない。1 回に 10 件超の「新着」は異常とみなして通知しない(bit-sap の safety valve)。
  - 一覧の content hash が同一ならパースを省略する。
- **条件付きリクエスト:** ETag / `If-None-Match`(zumiraku)。サーバが対応していれば有効だが、HOME'S / SUUMO が対応しているかは未検証。
- **サイト間 dedup**
  - 住所 + 賃料 + 間取り + 面積 の sha256(tokyo-rental-search-agent の dedup.py)。
  - SUUMO を優先して指紋が重複する他サイトの物件を落とす(kyoto-land-tracker)。
- **保存検索メール通知**: 実務での利用や解析の事例は未確認。

## 5. 公式/準公式データ

- **LIFULL HOME'S データセット(NII IDR)**
  - 賃貸スナップショット(2015/9、約 533 万件 + 画像)。
  - 月次データ(2015/7〜2017/6)。
  - 掲載期間データ(2018/10〜2024/3。賃貸 928 万件、掲載開始・終了日つき。2025/5 追加)。
  - 提供対象は大学・公的研究機関の研究者のみ、民間は不可、情報学の学術研究に限る。
  - 申請は利用申請書(Word)を idr@nii.ac.jp に送り、同意書に公印を押して返送する。
  - https://www.nii.ac.jp/dsc/idr/lifull/
- **LIFULL HOME'S Public API**: OAuth2 client credentials で、client_id/secret は LIFULL が提供する(公開サンプルの README / app.rb)。https://github.com/lifull/sample-public-api-ruby 。提供条件は未確認。
- **国交省 不動産情報ライブラリ API**
  - 取引価格・地価公示・防災・都市計画が中心で、賃貸の募集データではない。
  - 利用申請が必要。`Ocp-Apim-Subscription-Key` ヘッダで認証する。
  - https://www.reinfolib.mlit.go.jp/help/apiManual/
  - https://qiita.com/AzukiImo/items/da60c0e5872c027829e7
- **HOME'S Archive**(`homes.co.jp/archive/b-<建物ID>/`): 建物単位の賃貸掲載履歴ページ。Chrome 拡張の README で存在を確認した。https://github.com/hidehiro98/chromeextension_lifull_homes_archive

## 確信度

- **ページ本文を実際に読んだもの**
  - NII ページ、SUUMO 規約、各サイトの robots.txt。
  - Qiita: bit-sap の 2 本、atsuken、tomyu、k5o、t-hada、zumiraku。
  - levtech Comfy、note torum の 3 本、Zenn ikahan / fp16。
  - GitHub: tokyo-rental-search-agent(ソース)、homes-app(ソース)、kyoto-land-tracker、lpm-real-estate-aggregator、japan-rent-market-scraper の README、Public API のサンプル。
- **未検証**
  - HOME'S 利用規約本文。
  - Reddit(取得不可)。
  - Bing と Google の検索(無関係な結果)。
  - 保存検索メール、ETag の対応状況。
  - HOME'S の JSON 埋め込みの有無。
