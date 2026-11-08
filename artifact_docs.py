# -*- coding: utf-8 -*-
"""アーティファクトへ反映するときのドキュメント (JSON) を作り、ArtifactData の batch に渡す writes を表示する。

手順 (ARTIFACT.md):
  1. data/candidates.json・plans.json・conditions.json を Artifact (asset: true) で1つずつアップロードし、/_blob/<id> を得る
  2. python artifact_docs.py --candidates <id> --plans <id> --conditions <id> [--page]
  3. 表示された writes の if_version に、各ドキュメントの現在の version を入れて ArtifactData の batch に渡す
"""
import argparse
import datetime
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "artifact_docs")
DATASETS = {
    "candidates": ("候補の部屋", "条件に合う部屋を1行ずつにまとめた一覧。同じ部屋を複数社・複数サイトが掲載している場合は1件に絞っている。", "candidates.json"),
    "plans": ("間取り図", "候補の間取り図。縮小した画像を埋め込んだもの(ページは外部の画像を読み込めないため)。物件IDで候補と対応する。", "plans.json"),
    "conditions": ("絞り込み条件", "この一覧を作ったときの検索条件。家賃の上限(value)は、総額の橙色表示と絞り込みの基準にも使う。", "conditions.json"),
}


def main():
    ap = argparse.ArgumentParser()
    for k in DATASETS:
        ap.add_argument(f"--{k}", help=f"{k}.json をアップロードして得た blob の id (/_blob/<id> の <id>)")
    ap.add_argument("--page", action="store_true", help="artifact/index.html も files/index.html として反映する")
    a = ap.parse_args()
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    edit = {"via": "claude", "at": now}
    os.makedirs(OUT, exist_ok=True)
    writes = []
    for k, (title, desc, fname) in DATASETS.items():
        blob = getattr(a, k)
        if not blob:
            continue
        doc = {"title": title, "description": desc, "fixed": True, "updated": {"at": now, "by": "Claude"}, "edit": edit,
               "source": {"kind": "file", "url": f"/_blob/{blob}", "name": fname, "format": "json"}}
        path = os.path.join(OUT, f"doc_{k}.json")
        json.dump(doc, open(path, "w", encoding="utf-8"), ensure_ascii=False)
        writes.append({"op": "update", "collection": "datasets", "doc_id": k, "if_version": "<現在のversion>", "file_path": path})
    if a.page:
        path = os.path.join(OUT, "doc_index.json")
        json.dump({"text": open(os.path.join(HERE, "artifact", "index.html"), encoding="utf-8").read(), "edit": edit},
                  open(path, "w", encoding="utf-8"), ensure_ascii=False)
        writes.append({"op": "update", "collection": "files", "doc_id": "index.html", "if_version": "<現在のversion>", "file_path": path})
    print(json.dumps(writes, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
