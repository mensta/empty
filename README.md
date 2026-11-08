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
