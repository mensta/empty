# -*- coding: utf-8 -*-
"""suumo_scraper.py の結果 CSV から、アーティファクト用の候補データ (data/candidates.json) を作る。

  python candidates.py RESULT.csv                      # 既定: 東京都・築20年以内・35㎡以上・徒歩7分以内、木造は除外
  python candidates.py RESULT.csv --max-age 25 --min-area 40

構造 (RC など) は詳細ページにしか無いので、取得結果は data/detail_cache.json に保存して再利用する
(新しく出た物件の詳細ページだけを取りに行く)。出力は行オブジェクトの配列 (1行 = 1部屋)。
"""
import argparse
import csv
import json
import os
import re
import sys
import time
import unicodedata

import requests

import suumo_scraper as m

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data", "detail_cache.json")
OUT = os.path.join(HERE, "data", "candidates.json")
RC_PREFIX = ("鉄筋コン", "鉄骨鉄筋")  # RC / SRC


def detail_fields(soup):
    """詳細ページ -> 構造・階・向き・敷礼・契約・入居・備考"""
    tbl, pd = {}, {}
    for tr in soup.select("tr"):
        for th, td in zip(tr.find_all("th"), tr.find_all("td")):
            tbl.setdefault(m.clean(th.get_text()), m.clean(td.get_text()))
    for t in soup.select(".property_data-title"):
        b = t.find_next("div", class_="property_data-body")
        if b:
            pd.setdefault(m.clean(t.get_text()), m.clean(b.get_text()))
    return {
        "structure": tbl.get("構造", ""), "floor": tbl.get("階建", ""), "dir": pd.get("向き", ""),
        "shiki_rei": pd.get("敷金/礼金", ""), "contract": tbl.get("契約期間", ""),
        "move_in": tbl.get("入居", "").lstrip("'"), "biko": tbl.get("備考", ""),
    }


def load_cache():
    return json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}


def man(s):
    return round(float(s) / 10000, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("result_csv")
    ap.add_argument("--prefix", default="東京都", help="住所の先頭 (空なら全域)")
    ap.add_argument("--max-age", type=int, default=20)
    ap.add_argument("--min-area", type=float, default=35)
    ap.add_argument("--max-walk", type=int, default=7)
    ap.add_argument("--delay", type=float, default=1.5)
    a = ap.parse_args()

    rows = list(csv.DictReader(open(a.result_csv, encoding="utf-8-sig")))
    pool = []
    for r in rows:
        area = float(re.match(r"[\d.]+", r["area"]).group())
        if (r["address"].startswith(a.prefix) and int(r["age"]) <= a.max_age and area >= a.min_area
                and int(r["walk_min"]) <= a.max_walk):
            r["_area"] = area
            pool.append(r)
    cache, ses, fetched = load_cache(), requests.Session(), 0
    for r in pool:
        if r["url"] not in cache:
            cache[r["url"]] = detail_fields(m.fetch(ses, r["url"]))
            fetched += 1
            time.sleep(a.delay)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    out = []
    for r in sorted(pool, key=lambda r: int(r["total_yen"])):
        d = cache[r["url"]]
        if "木造" in d["structure"] or "構造は木造" in d["biko"]:
            continue
        line, st = r["station"].replace("東急", "").split("/")
        name = unicodedata.normalize("NFKC", re.sub(r"\s*\d+号室$", "", r["building"]))
        note = []
        if re.match(r"^(東急\S+線 )?\S+駅 .*階建", name):
            note.append("物件名なし")
        if "定期借家" in d["contract"]:
            note.append("定期借家")
        sk, rei = [x.strip().replace("万円", "").replace("万", "") for x in (d["shiki_rei"] or "- / -").split("/")][:2]
        out.append({
            "id": r["url"].rstrip("/").split("/")[-1],
            "group": "RC" if d["structure"].startswith(RC_PREFIX) else "鉄骨・ALC",
            "line": line.replace("線", ""), "station": st, "walk": int(r["walk_min"]),
            "building": name, "rent": man(r["rent_yen"]), "admin": man(r["admin_yen"] or 0), "total": man(r["total_yen"]),
            "area": r["_area"], "age": int(r["age"]), "structure": d["structure"], "floor": d["floor"],
            "photos": int(r["n_photos"]), "shiki": sk, "rei": rei, "move_in": d["move_in"],
            "note": "・".join(note), "url": r["url"],
        })
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(pool)} in pool ({fetched} detail pages fetched) -> {len(out)} candidates -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
