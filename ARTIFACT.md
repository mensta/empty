# 物件候補アーティファクトの更新手順

- アーティファクト: https://claude.ai/artifact/FGVqc2su3LU2XfoQKZMjHX （Dashboard タイプ。ページ本体とデータは別）
- ページ (`files/index.html`) は **データを読んで描くだけ**。候補の入れ替えでは触らない。
- データは3つの JSON ファイル (行オブジェクトの配列)。それぞれ `datasets/<名前>` が参照する:

  | 名前 | ファイル | 中身 |
  |---|---|---|
  | `candidates` | `data/candidates.json` | 候補の部屋 (1行 = 1部屋) |
  | `plans` | `data/plans.json` | 間取り図 (縮小 WebP の data: URI、物件IDで candidates と対応。約1MB。git 管理外) |
  | `conditions` | `data/conditions.json` | 画面上部の検索条件。`rent_max` の `value` は総額の橙色表示と「総額○万円以内」の基準にも使う |

  すべて `python run.py` が作る。`data/detail_cache.json` は詳細ページのキャッシュ、`data/plans/` は間取り図のキャッシュ。
- ページは外部サイトの画像を読み込めない (CSP) ので、間取り図は手元で取得して縮小し、データとして持たせている。
  掲載元が「間取り図」の欄に写真を登録していることがあるため、白地の割合と階調の変化で写真らしい画像は外す (`plans.py` の `looks_like_photo`。
  元画像の画素数では見分けられなかった: SUUMO が画像を約800pxにそろえているため。完全ではないので、気づいたら除外する物件を教えてもらう)。
- `candidates.json` の `initial` は初期費用の目安 (万円)。敷金+礼金+仲介手数料+初回保証料+掲載にある(初期)費用+金額記載のある火災保険。
  `initial_note` に前提 (仲手を1.1ヶ月と仮定 / 保証料は含まず) が入る。詳細キャッシュの形式を変えたら `candidates.py` の `CACHE_VERSION` を上げる。
- `artifact/index.html` : ページのバックアップ。正本はアーティファクト側 (ページを直したら手で合わせる)。

## 候補を入れ替える (ページは読み直さない)

1. データを作る (検索 -> 候補 -> 間取り図 -> 条件を1コマンドで。約7分)
   ```bash
   python run.py                              # 既定: 東横線・目黒線 / 東京都側 / 1LDK / 18万円以下 / 徒歩7分 / 築20年 / 28㎡より広い
   python run.py --prefs tokyo kanagawa --walk 10 --max-age 35   # 条件を変える (画面上部の条件表示も自動で変わる)
   python run.py --from-csv raw.csv           # 検索済みの結果 (--raw raw.csv で保存) から候補以降を作り直す。数秒
   ```
   検索結果や候補が0件のときは何も上書きしない。少しの修正 (1行消す・メモを足す) なら `data/candidates.json` を直接編集してよい。
2. JSON を1つずつ `Artifact` (`url` = 上のURL, `asset: true`, `file_path` = そのファイル) でアップロード → `/_blob/<id>` が返る。
   JSON は1回の呼び出しに1ファイルずつ。`candidates.json` / `plans.json` / `conditions.json` の3回。
3. `ArtifactData` の `batch` で `datasets/candidates`・`datasets/plans`・`datasets/conditions` を `update`
   (`if_version` は各ドキュメントの現在の version。分からなければ `get` で読む。ドキュメントは小さい):
   `{"source": {"kind": "file", "url": "/_blob/<id>", "name": "<file>", "format": "json"}, "updated": {"at": "<UTC ISO>", "by": "Claude"}, "edit": {"via": "claude", "at": "<UTC ISO>"}}`
4. 古い `/_blob/<id>` を `Artifact` の `action: delete` + `path: <id>` で削除 (参照されなくなったので)。

## ページを直す

- 小さな修正: `ArtifactData` の `str_replace` で `files/index.html` の `text` の該当箇所だけを置き換える。
- まとまった修正: `artifact/index.html` を直し、`{"text": <html全文>, "edit": {...}}` の JSON ファイルを作って
  `ArtifactData` の `update` に `file_path` で渡す (全文を会話に載せない)。
