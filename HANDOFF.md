# 引き継ぎメモ (2026-11-12 時点)

東横線・目黒線の1LDK候補を集めて、ローカルのビューアで見る。アーティファクトにも写しを反映する。作業の前提は `AGENTS.md`、落とし穴は `LESSONS.md`、反映手順は `ARTIFACT.md`。

## いまの状態

- 候補 **78室** (鉄筋コン 56 / 鉄骨・ALC 22)。掲載は SUUMO・at home・CHINTAI。
- **HOME'S は今回も取れていない**。任意扱い。WAF のチャレンジ (202) が確率的に出る。取れなくても続行する。
- ローカルのビューア (`viewer/`) は、ヘッドレス Chromium で描画を確認済み (デスクトップ・スマホ幅、件数・チップ・散布図の点78、横のはみ出しなし)。
- アーティファクトは **v6 (candidates) / v5 (plans, conditions)** に反映済み。ArtifactData の get で、candidates が新しい blob を指していることを確認済み。
- 反映の状態は `data/artifact_state.json` (blob の id、version、データのハッシュ)。現在の blob: candidates `a81b95af…`、plans `fcf0c238…`、conditions `e39a0025…`。
- テスト 32件 (`python -m unittest discover -s tests -v`) すべて通過。

## 移すもの

git で移るもの: コード、テスト、ドキュメント、`data/candidates.json`、`data/conditions.json`、`data/detail_cache.json`、`data/artifact_state.json`、`viewer/`。

git に入れないもの (著作物・大きい・再生成に時間がかかる) は、tar で手渡す:
- `data/plans.json` (約925KB。間取り図)
- `data/plans/` (間取り図のキャッシュ)
- `data/others_raw.json` (他サイトの生データ。HOME'S は今回入っていない)

**リポジトリは必ず private に。** 間取り図と写真が含まれる。

## 移行の手順 (手元の PC の devcontainer)

1. GitHub で private のリポジトリを作る (例: `rental-search`)。
2. 今のブランチを `main` として push する (下の例)。
3. tar の中身を、clone した先の `data/` に展開する。
4. devcontainer を開く (`.devcontainer/devcontainer.json`)。`postCreateCommand` で依存関係と Claude Code の CLI を入れ、ビューアを作る。
5. 下の「最初に確かめること」を順に行う。

```bash
# 例: このブランチを、自分の private リポジトリの main として送る (手元の PC で)
git clone -b claude/amazing-archimedes-skfnqc https://github.com/mensta/empty rental-search
cd rental-search
git remote set-url origin https://github.com/<あなた>/rental-search.git
git push -u origin claude/amazing-archimedes-skfnqc:main
```

## 最初に確かめること

```bash
python -m unittest discover -s tests -v       # 32件通ること
python scripts/build_viewer.py                # viewer/index.html を作る
python -m http.server 8000                    # http://localhost:8000/viewer/ で候補が出ること
claude -p --model claude-haiku-5-5 "ok とだけ返して"   # Claude Code がログイン済みで Haiku が使えること
python scripts/sync_artifact.py --dry-run     # 判定と指示が出ること (変更がなければ「変更なし」)
```

Claude Code の初回ログインは、devcontainer の中で `claude` を起動して行う (ブラウザで認証)。アーティファクトの反映には、Artifact / ArtifactData が使えるアカウントが必要。使えないことが分かったら、反映は手動の手順 (`ARTIFACT.md`) に切り替える。

## 未解決・注意

- **アーク大岡山** が、同じ駅・広さ・家賃の2行で出ている。同じ建物の別の部屋か、同じ部屋の重複かは未確認。
- **HOME'S** が取れない。取れる日に `python run.py` を走らせると加わる。
- **画面の描画 (アーティファクト側)** は確認できていない。ローカルでは確認済み。
- **間取り図の写真判定** (`plans.looks_like_photo`) はヒューリスティック。外観写真が混ざることがある (見つけたら教えてもらう)。
- **at home の初期費用** は、鍵交換などを含めていない (掲載の記載が少ない)。
- **仲介手数料の記載がない物件** は、1.1ヶ月分と仮定している (画面の注記に出る)。
- 間取り図が1室ない (「図なし」と表示)。

## 次にやれること (候補)

- HOME'S の再取得 (時間をおいて、一回ずつ確かめる)。
- いい部屋ネット (CSS のクラス名が不安定なので未実装)。
- 神奈川県の他サイト対応。
- 画面にメモ列を足す (データの `memo` を編集できるように)。
