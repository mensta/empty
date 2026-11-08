# 物件候補アーティファクトの更新手順

- アーティファクト: https://claude.ai/artifact/FGVqc2su3LU2XfoQKZMjHX （Dashboard タイプ。ページ本体とデータは別）
- ページ (`files/index.html`) は **データを読んで描くだけ**。候補の入れ替えでは触らない。
- データは2つのファイル (行オブジェクトの JSON):
  - `data/candidates.json` : 候補の部屋 (1行 = 1部屋)。`candidates.py` が生成する。
  - `data/conditions.json` : 画面上部の検索条件。`rent_max` の `value` は総額の橙色表示と「総額○万円以内」の基準にも使う。
- `data/detail_cache.json` : 物件の詳細ページ (構造など) のキャッシュ。新しい物件の分だけ取得する。
- `artifact/index.html` : ページのバックアップ。正本はアーティファクト側 (ページを直したら手で合わせる)。

## 候補を入れ替える (ページは読み直さない)

1. データを作る (検索 -> 候補 -> 条件の3つを1コマンドで。約5分)
   ```bash
   python run.py                              # 既定: 東横線・目黒線 / 東京都側 / 1LDK / 18万円以下 / 徒歩7分 / 築20年 / 35㎡以上
   python run.py --prefs tokyo kanagawa --walk 10 --max-age 35   # 条件を変える (画面上部の条件表示も自動で変わる)
   python run.py --from-csv raw.csv           # 検索済みの結果 (--raw raw.csv で保存) から候補だけ作り直す。数秒
   ```
   `data/candidates.json` と `data/conditions.json` ができる。検索結果が0件のときは何も上書きしない。
   少しの修正 (1行消す・メモを足す) なら `data/candidates.json` を直接編集してよい。
2. `Artifact` (`url` = 上のURL, `asset: true`, `file_path` = `data/candidates.json`) でアップロード → `/_blob/<id>` が返る。
3. `ArtifactData` `update` で `datasets/candidates` を更新 (`if_version` は直前の `set`/`update` の結果の version):
   `{"source": {"kind": "file", "url": "/_blob/<id>", "name": "candidates.json", "format": "json"}, "updated": {"at": "<UTC ISO>", "by": "Claude"}, "edit": {"via": "claude", "at": "<UTC ISO>"}}`
4. 古い `/_blob/<id>` を `Artifact` `action: delete` + `path: <id>` で削除 (どこからも参照されなくなったので)。
5. 条件を変えて `run.py` を実行したときは、`data/conditions.json` についても同じ 2〜4 を `datasets/conditions` に行う。

## ページを直す

`ArtifactData` `str_replace` で `files/index.html` の `text` の該当箇所だけを置き換える (全文を読み直さない)。
