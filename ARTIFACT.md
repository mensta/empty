# 物件候補アーティファクトの更新手順

(作業の前提は `AGENTS.md`、落とし穴は `LESSONS.md`)

- アーティファクト: https://claude.ai/artifact/FGVqc2su3LU2XfoQKZMjHX
- **画面の正本はローカルのビューア** (`viewer/`)。アーティファクトは同じ候補を見せる写し。
- ページ本体 (`artifact/index.html`) はデータを読んで描くだけ。候補の入れ替えではページを触らない。
- データは3つの JSON (行オブジェクトの配列): `data/candidates.json` / `data/plans.json` (間取り図。git 管理外) / `data/conditions.json`。`python run.py` が作り、検証 (`validate.py`) に通ったものだけ書き出す。

## 反映 (通常)

```bash
python run.py                       # データを作る (約13分。HOME'S は任意)
python scripts/build_viewer.py      # ローカルのビューアを更新 (ページを直したときだけ必要)
python scripts/sync_artifact.py     # アーティファクトへ反映 (データが変わっていれば)
```

`sync_artifact.py` の中身:
1. Claude (Haiku, headless) が3ファイルをアップロードする。道具は Artifact と Read のみ。
2. スクリプトが `artifact_docs.py` で反映用ドキュメントを作る (`data/artifact_docs/`)。
3. Claude (Haiku) が ArtifactData で datasets の version を読み、batch で更新し、古い blob を削除する。道具は ArtifactData・Artifact・Read。
4. 成功したら、スクリプトが `data/artifact_state.json` を書く (blob の id、version、データのハッシュ)。失敗したら状態は変えない。

確かめ方: `python scripts/sync_artifact.py --dry-run` で判定と指示を見る。反映後は、ArtifactData の get で `datasets/candidates` の `source.url` が新しい blob を指していることを見る。

## 注意

- `claude` がログイン済みで、Artifact / ArtifactData が使えること。使えないときは、手動の手順 (下) を使う。
- 画面の描画は、アーティファクト側では確認できない (自動チェックが返らない)。ローカルのビューアでは確認できる。
- 間取り図や写真は掲載元の著作物。アーティファクトは共有しない (共有するときは先にユーザーに聞く)。

## 手動の手順 (参考: スクリプトが使えないとき)

1. 3ファイルを、それぞれ Artifact (`url` = 上の URL、`asset: true`、`file_path` = そのファイル) でアップロードし、`/_blob/<id>` を控える。
2. `python artifact_docs.py --candidates <id> --plans <id> --conditions <id>` で反映用ドキュメントを作る。
3. ArtifactData の get で `datasets` の各 version を読み、batch で3件を update する (`if_version` に読んだ version を入れる)。
4. 古い blob を Artifact の delete (`path` = id) で消す。
5. 最後に `data/artifact_state.json` の blobs / dataset_versions / synced_sha を書き直す。
