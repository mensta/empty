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

import web

import suumo_scraper as m

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
RC_PREFIX = ("鉄筋コン", "鉄骨鉄筋")  # RC / SRC
CACHE_VERSION = 2  # 詳細キャッシュの形式。上げると全件を取り直す
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
    opt = soup.find("div", id="bkdt-option")
    return {
        "v": CACHE_VERSION,
        "structure": tbl.get("構造", ""), "floor": tbl.get("階建", ""), "dir": pd.get("向き", ""),
        "shiki_rei": pd.get("敷金/礼金", ""), "contract": tbl.get("契約期間", ""),
        "move_in": tbl.get("入居", "").lstrip("'"), "biko": tbl.get("備考", ""),
        "hosho": tbl.get("保証会社", ""), "sonpo": tbl.get("損保", ""),
        "options": opt.get_text("、", strip=True) if opt else "",
    }


# ---------------------------------------------------------------- 初期費用の目安
def _n(s):
    return unicodedata.normalize("NFKC", s or "")


def _amount_man(token, rent):
    """'14.2万円' / '1ヶ月' / '-' -> 万円。読めなければ None"""
    t = _n(token).replace(" ", "")
    if t in ("", "-", "なし", "不要", "無"):
        return 0.0
    m = re.match(r"([\d.]+)ヶ月", t)
    if m:
        return float(m.group(1)) * rent
    m = re.match(r"([\d.]+)万", t)
    if m:
        return float(m.group(1))
    m = re.match(r"([\d,]+)円", t)
    return float(m.group(1).replace(",", "")) / 10000 if m else None


def _chukai_months(options, biko):
    """仲介手数料 (ヶ月分)。記載が無ければ上限の1.1ヶ月 (1ヶ月+税) と仮定。戻り値: (ヶ月, 仮定したか)"""
    t = _n(options + " " + biko)
    m = re.search(r"仲手\s*([\d.]+)\s*ヶ月", t) or re.search(r"仲介手数料[^。、/]{0,12}?([\d.]+)\s*(?:ヶ月|か月|カ月)", t)
    if m:
        return float(m.group(1)), False
    m = re.search(r"仲介手数料[^。]{0,12}?([\d.]+)\s*%", t)
    if m:
        return float(m.group(1)) / 100, False
    if re.search(r"仲介手数料\s*(?:無料|0円|なし)|仲手\s*(?:なし|無料)", t):
        return 0.0, False
    return 1.1, True


def _hosho_first(hosho, total):
    """初回保証料 (万円)。'初回…50%' / '請求月額の1ヶ月分' を読み、'最低○万円' があれば下限にする。読めなければ None"""
    t = _n(hosho)
    m = re.search(r"(?:初回|基本料)[^%]*?([\d.]+)\s*%", t) or re.search(r"([\d.]+)\s*%", t)
    if m:
        v = total * float(m.group(1)) / 100
    else:
        m = re.search(r"([\d.]+)\s*ヶ月分", t)
        if not m:
            return None
        v = total * float(m.group(1))
    mn = re.search(r"最低[^\d]{0,12}([\d,.]+)\s*(万)?", t)
    if mn:
        low = float(mn.group(1).replace(",", "")) / (1 if mn.group(2) else 10000)
        v = max(v, low)
    return v


def estimate_initial(d, rent, admin):
    """敷金+礼金+仲介手数料+初回保証料+掲載にある(初期)費用+火災保険(金額の記載があれば)。万円。
    前家賃・日割り家賃・記載のない鍵交換代などは含まない。戻り値: (万円, 前提のメモ)"""
    notes = []
    sk, rei = ([x.strip() for x in (d.get("shiki_rei") or "- / -").split("/")] + ["-", "-"])[:2]
    a, b = _amount_man(sk, rent), _amount_man(rei, rent)
    if a is None or b is None:
        notes.append("敷礼が不明")
    total = rent + admin
    mon, assumed = _chukai_months(d.get("options", ""), d.get("biko", ""))
    if assumed:
        notes.append("仲手は1.1ヶ月と仮定")
    g = _hosho_first(d.get("hosho", ""), total)
    if g is None:  # 保証会社の欄に無ければ、備考の「保証」を含む文を読む
        for sent in re.split(r"[。]", _n(d.get("biko", ""))):
            if "保証" in sent and (g := _hosho_first(sent, total)) is not None:
                break
    if g is None:
        notes.append("保証料は含まず")
    biko = _n(d.get("biko", ""))
    fees = sum(float(x.replace(",", "")) for x in re.findall(r"[\(（]初期[\)）]\s*([\d,]+)円", biko)) / 10000
    fees += d.get("init_fees_man", 0.0)
    if d.get("fees_unknown"):
        notes.append("鍵交換などの初期費用は含まず")
    sonpo = _amount_man(d.get("sonpo", ""), rent)
    val = (a or 0) + (b or 0) + mon * rent + (g or 0) + fees + (sonpo or 0)
    return round(val, 1), "・".join(notes)


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


def norm_structure(text):
    """サイトごとの構造表記 ('RC(鉄筋コンクリート)' / 'ＲＣ' / '鉄筋コンクリート造' など) を SUUMO の表記にそろえる"""
    t = _n(text)
    if t.startswith(("RC", "SRC")) or "鉄筋コン" in t or "鉄骨鉄筋" in t:
        return "鉄筋コン"
    if "軽量鉄骨" in t:
        return "軽量鉄骨"
    if "ALC" in t or "気泡" in t:
        return "気泡コン"
    if "木造" in t or t.startswith("W"):
        return "木造"
    return "鉄骨" if "鉄骨" in t or t.startswith("S") else t


def is_wood(d):
    return "木造" in _n(d.get("structure", "")) or "構造は木造" in d.get("biko", "") or norm_structure(d.get("structure", "")) == "木造"


def make_row(*, id, site, also, url, building, line, station, walk, rent_yen, admin_yen, total_yen, area, age, photos, d, layout=""):
    """SUUMO でも他サイトでも、候補1行を同じ形に組み立てる。d は詳細ページから読んだ内容 (構造・敷礼・保証・契約など)"""
    structure = norm_structure(d["structure"])
    name = unicodedata.normalize("NFKC", re.sub(r"\s*\d+号室$", "", building))
    name = re.sub(r"\s*\d+階建$", "", name)
    note = []
    if re.match(r"^(東急\S+線 )?\S+駅 (.*階建|徒歩\d+分)", name):
        note.append("物件名なし")
    if "定期借家" in d["contract"]:
        note.append("定期借家")
    sk, rei = ([x.strip().replace("万円", "").replace("万", "") for x in (d["shiki_rei"] or "- / -").split("/")] + ["-", "-"])[:2]
    initial, initial_note = estimate_initial(d, man(rent_yen), man(admin_yen or 0))
    return {
        "id": id, "site": site, "also": also,
        "group": "RC" if structure == "鉄筋コン" else "鉄骨・ALC",
        "line": line.replace("線", ""), "station": station, "walk": int(walk),
        "layout": layout, "building": name, "rent": man(rent_yen), "admin": man(admin_yen or 0), "total": man(total_yen),
        "area": area, "age": int(age), "structure": structure, "floor": d["floor"],
        "photos": int(photos), "shiki": sk, "rei": rei, "move_in": d["move_in"],
        "initial": initial, "initial_note": initial_note,
        "note": "・".join(note), "url": url,
    }


def build_candidates(rows, cache_path, prefix="", max_age=20, min_area=28.0, max_walk=7, delay=1.5, log=print):
    """rows: suumo_scraper の検索結果 (dict。CSV から読んだ文字列でも可)。構造の無い物件は詳細ページを取得する。"""
    pool = []
    for r in rows:
        area = float(re.match(r"[\d.]+", r["area"]).group())
        if (r["address"].startswith(prefix) and int(r["age"]) <= max_age and area > min_area
                and int(r["walk_min"]) <= max_walk):
            pool.append({**r, "_area": area})
    cache = load_json(cache_path, {})
    todo = [r for r in pool if cache.get(r["url"], {}).get("v") != CACHE_VERSION or not cache[r["url"]].get("structure")]
    log(f"候補プール {len(pool)} 室 (詳細ページを新規取得: {len(todo)} 件)")
    ses, failed = web.new_session(), 0
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
        if d is None or is_wood(d):
            continue
        line, st = r["station"].replace("東急", "").split("/")
        out.append(make_row(
            id=r["url"].rstrip("/").split("/")[-1], site="SUUMO", also="", url=r["url"], building=r["building"],
            line=line, station=st, walk=r["walk_min"], rent_yen=r["rent_yen"], admin_yen=r["admin_yen"] or 0,
            total_yen=r["total_yen"], area=r["_area"], age=r["age"], photos=r["n_photos"], d=d, layout=r.get("layout", "")))
    return out


def make_conditions(layout, max_rent, lines, prefs, walk, max_age, min_area, min_photos, sites="SUUMO"):
    """画面上部の検索条件。run.py に渡した条件から作るので、表示と実際の検索条件がずれない"""
    line_names = "・".join(m.LINES[l][1] for l in lines)
    pref_names = "・".join(m.PREFS[p] for p in prefs)
    return [
        {"key": "sites", "label": "掲載サイト", "text": sites},
        {"key": "layout", "label": "間取り", "text": layout if isinstance(layout, str) else "・".join(layout)},
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
    web.add_proxy_argument(ap)
    a = ap.parse_args()
    try:
        web.configure_proxy(a.proxy)
    except ValueError as e:
        ap.error(str(e))
    rows = list(csv.DictReader(open(a.result_csv, encoding="utf-8-sig")))
    out = build_candidates(rows, a.cache, a.prefix, a.max_age, a.min_area, a.max_walk, a.delay, log=lambda s: print(s, file=sys.stderr))
    save_json(a.out, out)
    print(f"-> {len(out)} candidates -> {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
