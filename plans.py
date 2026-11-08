# -*- coding: utf-8 -*-
"""候補の間取り図を取得し、アーティファクトに埋め込める小さな画像 (data: URI) にして plans.json にする。

アーティファクトのページは外部サイトの画像を読み込めないので、SUUMO の画像は手元で取得して変換する。
元画像は掲載ごとに大きさも縦横比もまちまちなので、縮小して WebP にそろえる (縦横比は保つ。枠への収め方は表示側で行う)。
取得した画像は cache_dir に保存し、次回は新しく出た物件の分だけ取得する。
"""
import base64
import io
import os
import time

import requests
from PIL import Image

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
MAX_SIDE = 560
QUALITY = 72


def plan_url(item_id):
    """'bc_100535325727' -> 間取り図の URL"""
    bc = item_id.split("_", 1)[1]
    return f"https://img01.suumo.com/front/gazo/fr/bukken/{bc[-3:]}/{bc}/{bc}_co.jpg"


def to_webp(content):
    im = Image.open(io.BytesIO(content))
    if im.mode not in ("RGB", "L"):  # 透過があれば白地に
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[-1])
        im = bg
    im = im.convert("RGB")
    im.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    im.save(out, "WEBP", quality=QUALITY, method=6)
    return out.getvalue()


def build_plans(candidates, cache_dir, delay=0.8, log=print):
    """candidates: candidates.json の行。戻り値: [{'id', 'img'(data URI)}] (間取り図が無い物件は含めない)"""
    os.makedirs(cache_dir, exist_ok=True)
    ses, out, fetched, missing = requests.Session(), [], 0, []
    for r in candidates:
        path = os.path.join(cache_dir, r["id"] + ".webp")
        if not os.path.exists(path):
            try:
                resp = ses.get(plan_url(r["id"]), headers=HEADERS, timeout=30)
                resp.raise_for_status()
                with open(path, "wb") as f:
                    f.write(to_webp(resp.content))
                fetched += 1
                time.sleep(delay)
            except Exception as e:  # 取れなければ表示側で「なし」の枠になる。次回に再挑戦
                missing.append(r["id"])
                log(f"  間取り図を取得できず (スキップ): {r['id']} {e}")
                continue
        with open(path, "rb") as f:
            out.append({"id": r["id"], "img": "data:image/webp;base64," + base64.b64encode(f.read()).decode()})
    log(f"間取り図 {len(out)}/{len(candidates)} 枚 (新規取得 {fetched}、取得できず {len(missing)})")
    return out
