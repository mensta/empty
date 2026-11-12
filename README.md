# empty
empty repo

## SUUMO 賃貸スクレイパー (実験)

`suumo_scraper.py` は SUUMO 賃貸の一覧 (`div.cassetteitem`) と詳細ページを取得して CSV に出力する最小実装。

```bash
pip install -r requirements.txt
python suumo_scraper.py --sc 13104 --pages 2 --detail 3 --out out.csv
```

- 個人利用・低頻度アクセス前提（`--delay` 既定 1.5 秒）。SUUMO の利用規約を確認すること。
- 市区町村は `--sc` (例: 新宿区=13104) で指定。
- 沿線モード (`--lines toyoko meguro`) では、間取り図・周辺施設を除く写真が `--min-photos`(既定3) 枚未満、または室内写真が0枚の掲載を除外する。同じ部屋に写真の揃った別の掲載があれば、そちらが残る。

## SUUMO 以外のサイト (実験)

`sites.py` に LIFULL HOME'S / at home / CHINTAI の一覧パーサー、`search_sites.py` に東急東横線・目黒線の 1LDK を
3サイト横断で検索するスクリプトを置いている。

```bash
python search_sites.py --out sites.csv            # 3サイト × 2路線
python search_sites.py --sites "HOME'S" --out h.csv
```

- 各サイトの robots.txt で対象パスが許可されていることを確認済み（2026-11）。低頻度 (`--delay` 既定 1.5 秒) で利用すること。
- 構造 (RC など) が一覧に出るのは CHINTAI のみ。HOME'S / at home は詳細ページが必要。

## 検索から候補JSONまで (1コマンド)

```bash
python run.py        # 東横線・目黒線 / 東京都側 / 1LDK・2DK・2LDK / 19万円以下 / 徒歩10分 / 築35年 / 28㎡より広い / 木造除外 -> data/candidates.json
```

詳細は `run.py --help` と `ARTIFACT.md` (アーティファクトへの反映手順)。

## 他サイトの増分取得

```bash
python run.py --incremental-others      # 他サイトは新着順で取り、既知のページで打ち切る (7日ごと・初回は全件)
python run.py --incremental-others --full-others   # 今回は全件取得
```

HOME'S の WAF チャレンジ (202) は、リクエストが続くほど出やすい。増分取得はリクエスト数を減らすためのもの。状態は `data/known_ids.json`。
