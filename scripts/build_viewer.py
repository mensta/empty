# -*- coding: utf-8 -*-
"""artifact/index.html (ページの正本) から、ローカル表示用の viewer/index.html を作る。

    python scripts/build_viewer.py
    python -m http.server 8000   # リポジトリ直下で起動し、http://localhost:8000/viewer/ を開く

ページ本体の描画コードは一つだけ。ローカルでは viewer/dash-shim.js が dash の代わりをし、
viewer/tokens.css が見た目の変数を用意する。ページを直したら、このスクリプトを再実行する。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "artifact", "index.html")
DST = os.path.join(ROOT, "viewer", "index.html")

HEAD = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>東横線・目黒線の1LDK候補 (ローカル)</title>
<link rel="stylesheet" href="tokens.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
</head>
<body>
"""
TAIL = "\n</body>\n</html>\n"
SHIM = '<script src="dash-shim.js"></script>\n<script>'


def build(src=SRC, dst=DST) -> None:
    body = open(src, encoding="utf-8").read()
    body = body.replace('<meta name="dash-one-writer">\n', "", 1)
    if body.count("\n<script>\n") != 1:
        raise SystemExit("ページのインラインの <script> が1つではありません。build_viewer.py を直してください。")
    body = body.replace("\n<script>\n", "\n" + SHIM + "\n", 1)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(HEAD + body + TAIL)


if __name__ == "__main__":
    build()
    print(f"作成: {DST}  (http://localhost:8000/viewer/ で開く)", file=sys.stderr)
