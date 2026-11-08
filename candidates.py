# -*- coding: utf-8 -*-
"""検索結果の行 -> アーティファクト用の候補データ (candidates.json) / 条件データ (conditions.json)。

通常は run.py から使う。単体でも動く (suumo_scraper.py の結果 CSV を渡す):
  python candidates.py RESULT.csv --max-age 20 --min-area 28 --max-walk 7

構造 (RC など) は詳細ページにしか無いので、取得結果は detail_cache.json に保存して再利用する
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
DATA = os.path.join(HERE, "data")
RC_PREFIX = ("鉄筋コン", "鉄骨鉄筋")  # RC / SRC
PREF_PREFIX = {"tokyo": "東京都", "kanagawa": "神奈川県"}


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


def load_json(path, default):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else default


def save_json(path, obj):
    """途中で失敗しても元のファイルを壊さないよう、一時ファイル経由で置き換える"""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    json.dump(obj, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def man(v):
    return round(float(v) / 10000, 2)


def build_candidates(rows, cache_path, prefix="", max_age=20, min_area=28.0, max_walk=7, delay=1.5, log=print):
    """rows: suumo_scraper の検索結果 (dict。CSV から読んだ文字列でも可)。構造の無い物件は詳細ページを取得する。"""
    pool = []
    for r in rows:
        area = float(re.match(r"[\d.]+", r["area"]).group())
        if (r["address"].startswith(prefix) and int(r["age"]) <= max_age and area > min_area
                and int(r["walk_min"]) <= max_walk):
            pool.append({**r, "_area": area})
    cache = load_json(cache_path, {})
    todo = [r for r in pool if r["url"] not in cache]
    log(f"候補プール {len(pool)} 室 (詳細ページを新規取得: {len(todo)} 件)")
    ses, failed = requests.Session(), 0
    for i, r in enumerate(todo, 1):
        try:
            cache[r["url"]] = detail_fields(m.fetch(ses, r["url"]))
        except Exception as e:  # 取れなかった物件はキャッシュせず、次回に再挑戦する
            failed += 1
            log(f"  詳細取得に失敗 (スキップ): {r['url']} {e}")
        if i % 10 == 0 or i == len(todo):
            log(f"  詳細 {i}/{len(todo)}")
            save_json(cache_path, cache)
        time.sleep(delay)
    save_json(cache_path, cache)

    out = []
    for r in sorted(pool, key=lambda r: int(r["total_yen"])):
        d = cache.get(r["url"])
        if d is None or "木造" in d["structure"] or "構造は木造" in d["biko"]:
            continue
        line, st = r["station"].replace("東急", "").split("/")
        name = unicodedata.normalize("NFKC", re.sub(r"\s*\d+号室$", "", r["building"]))
        note = []
        if re.match(r"^(東急\S+線 )?\S+駅 .*階建", name):
            note.append("物件名なし")
        if "定期借家" in d["contract"]:
            note.append("定期借家")
        sk, rei = ([x.strip().replace("万円", "").replace("万", "") for x in (d["shiki_rei"] or "- / -").split("/")] + ["-", "-"])[:2]
        out.append({
            "id": r["url"].rstrip("/").split("/")[-1],
            "group": "RC" if d["structure"].startswith(RC_PREFIX) else "鉄骨・ALC",
            "line": line.replace("線", ""), "station": st, "walk": int(r["walk_min"]),
            "building": name, "rent": man(r["rent_yen"]), "admin": man(r["admin_yen"] or 0), "total": man(r["total_yen"]),
            "area": r["_area"], "age": int(r["age"]), "structure": d["structure"], "floor": d["floor"],
            "photos": int(r["n_photos"]), "shiki": sk, "rei": rei, "move_in": d["move_in"],
            "note": "・".join(note), "url": r["url"],
        })
    return out


def make_conditions(layout, max_rent, lines, prefs, walk, max_age, min_area, min_photos):
    """画面上部の検索条件。run.py に渡した条件から作るので、表示と実際の検索条件がずれない"""
    line_names = "・".join(m.LINES[l][1] for l in lines)
    pref_names = "・".join(m.PREFS[p] for p in prefs)
    return [
        {"key": "layout", "label": "間取り", "text": layout},
        {"key": "rent_max", "label": "家賃", "text": f"{max_rent:g}万円以下", "value": max_rent},
        {"key": "line", "label": "沿線", "text": f"{line_names}({pref_names})"},
        {"key": "walk", "label": "駅徒歩", "text": f"{walk}分以内"},
        {"key": "age", "label": "築年数", "text": f"{max_age}年以内"},
        {"key": "area", "label": "広さ", "text": f"{min_area:g}㎡より広い"},
        {"key": "structure", "label": "構造", "text": "木造を除く(鉄筋コン優先)"},
        {"key": "photos", "label": "写真", "text": "間取り図のみ・極端に少ない物件を除く" if min_photos else "写真の枚数は問わない"},
    ]


def main():
    ap = argparse.ArgumentParser(description="検索結果 CSV から candidates.json を作る")
    ap.add_argument("result_csv")
    ap.add_argument("--prefix", default="東京都", help="住所の先頭 (空なら全域)")
    ap.add_argument("--max-age", type=int, default=20)
    ap.add_argument("--min-area", type=float, default=28, help="この広さ(㎡)より広い部屋だけ")
    ap.add_argument("--max-walk", type=int, default=7)
    ap.add_argument("--delay", type=float, default=1.5)
    ap.add_argument("--cache", default=os.path.join(DATA, "detail_cache.json"))
    ap.add_argument("--out", default=os.path.join(DATA, "candidates.json"))
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.result_csv, encoding="utf-8-sig")))
    out = build_candidates(rows, a.cache, a.prefix, a.max_age, a.min_area, a.max_walk, a.delay, log=lambda s: print(s, file=sys.stderr))
    save_json(a.out, out)
    print(f"-> {len(out)} candidates -> {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
