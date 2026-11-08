# このリポジトリで作業するときの前提

東横線・目黒線の賃貸 (1LDK) を SUUMO / HOME'S / at home / CHINTAI から集め、条件で絞った候補をアーティファクトに出す。

## よく使うコマンド
- 候補を作る: `python run.py` (約8分。条件は `--help`。`--from-csv raw.csv` で検索を省略)
- テスト: `python -m unittest discover -s tests -v`
- アーティファクトへの反映: `ARTIFACT.md` の手順 (ページは読み直さない。データの JSON だけ差し替える)
- 反映用ドキュメントの生成: `python artifact_docs.py --candidates <blob id> --plans <blob id> --conditions <blob id>`

## 守ること
- 取得は低頻度で。待ち時間を詰めない (既定 1.5 秒)。HTTP 202 や空の応答が返るのは普通。`web.fetch_soup` が取り直す。
- 新しい取得処理・パーサーは `web.fetch_soup` を通し、不具合を直したら `tests/` にその再現ケースを足す。`LESSONS.md` にも追記する。
- `run.py` の検証 (`validate.py`) で止まったら、出力を上書きしていない。原因を直してから再実行する (検証を緩めない)。
- 数字は自動計算が正しいことが多い。手計算と食い違ったら、まず入力 (掲載の記載) を疑って確かめる。
- 画面 (アーティファクト) の描画は自動チェックが返らないので確認できない。確認したと言わない。
- 間取り図や写真は掲載元の著作物。アーティファクトは共有しない (共有するときは先にユーザーに聞く)。

## 構成
`run.py` (入口) → `suumo_scraper.py` (SUUMO 検索) → `candidates.py` (構造・初期費用) → `others.py` / `search_sites.py` / `sites.py` (他サイト) → `plans.py` (間取り図) → `validate.py` → `data/*.json`
