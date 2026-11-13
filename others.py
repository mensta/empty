# -*- coding: utf-8 -*-
"""HOME'S / DOOR賃貸 / at home / CHINTAI の結果を、SUUMO の候補と同じ形の行にして取り込む。

- 同じ部屋 (住所の町名・面積・賃料が同じ) が SUUMO の候補にあれば、SUUMO の行を残し、「also」に掲載サイトを足すだけ。
- SUUMO の候補にない部屋だけ、詳細ページで構造・初期費用・間取り図・写真の枚数を調べて候補に加える。
- 複数の他サイトに同じ部屋があれば、構造が一覧に出る CHINTAI、HOME'S、at home の順に1件を選ぶ。
"""
import json
import re
import time
import unicodedata

import web

import candidates as cand
import sites

ORDER = ["CHINTAI", "HOME'S", "DOOR", "at home"]
PREFIX = {"HOME'S": "hm_", "at home": "ah_", "CHINTAI": "ch_", "DOOR": "dr_"}


def room_key(address, area, rent_yen):
    """同じ部屋の判定キー: (町名[数字なし], 面積, 賃料)。サイトごとの住所表記ゆれ (丁目・全角) を吸収する"""
    a = unicodedata.normalize("NFKC", address or "")
    a = re.sub(r"^(東京都|神奈川県)", "", a).replace("丁目", "")
    a = re.sub(r"[\d\s\-ー]", "", a)
    return (a, round(float(area), 1), int(rent_yen))


def row_id(site, url):
    return PREFIX[site] + url.rstrip("/").split("/")[-1].split("?")[0].replace("bk-", "")


def door_detail(r):
    """data/door_extra.json の1室 (ブラウザで取った DOOR賃貸) -> 詳細キャッシュと同じ形 (sites.detail_* の戻り値と同じキー)。
    DOOR は部屋ページを `build_other_rows` から取りに行かない (取得済みの内容を使う)。
    フロアは「4階」と建物の「5階建（地下1階）」から「4階/5階建」にする。保証会社は金額が書かれていないので、初期費用に保証料は入らない。"""
    d = r["detail"]
    floors = re.match(r"\d+階建", unicodedata.normalize("NFKC", r.get("floors") or ""))
    floor = r.get("floor") or ""
    return {
        "structure": r.get("structure") or d.get("建物構造", ""),
        "floor": f"{floor}/{floors.group()}" if floors and floor else floor,
        "shiki_rei": f"{_dash(d.get('敷金'))}/{_dash(d.get('礼金'))}",
        "hosho": "", "biko": "", "sonpo": "", "options": "",
        "contract": "", "move_in": (d.get("入居・引渡期間") or "").lstrip("'"),
        "init_fees_man": 0.0, "fees_unknown": True,
        "plan_url": "", "n_photos": int(d["n_photos"]), "n_interior": int(d["n_interior"]),
        "v": cand.CACHE_VERSION,
    }


def _dash(x):
    return "-" if (x or "").strip() in ("", "なし", "無", "-", "--") else x.strip()


def merge_across_sites(groups):
    """room_key が違っても、(面積, 家賃+管理費, 間取り) が同じで掲載サイトが重ならない部屋は同じ部屋とみなして1つにまとめる
    (サイトごとに住所の粒度が違う場合の取りこぼしを拾う)。同じサイトの2室 (同じ建物の別の部屋) は、まとめない"""
    def key2(rows):
        r = rows[0]
        return (round(float(r["area_m2"]), 1), r["rent_yen"] + (r["admin_yen"] or 0), r["layout"])
    out, seen = {}, {}
    for k, rows in groups.items():
        sites_here = {r["site"] for r in rows}
        for k0 in seen.get(key2(rows), []):
            if not sites_here & {r["site"] for r in out[k0]}:
                out[k0] = out[k0] + rows
                break
        else:
            out[k] = list(rows)
            seen.setdefault(key2(rows), []).append(k)
    return out


def build_other_rows(rows, suumo_keys, cache_path, min_photos=3, delay=1.5, log=print):
    """rows: search_sites.filter_rows の結果。戻り値: (候補に加える行, {id: 間取り図URL}, {キー: 掲載サイト一覧})"""
    groups = {}
    for r in rows:
        groups.setdefault(room_key(r["address"], r["area_m2"], r["rent_yen"]), []).append(r)
    groups = merge_across_sites(groups)
    present = {k: sorted({r["site"] for r in v}, key=ORDER.index) for k, v in groups.items()}
    new_keys = [k for k in groups if k not in suumo_keys]
    log(f"他サイトの部屋 {len(groups)} 室のうち、SUUMO の候補にない部屋: {len(new_keys)} 室")

    cache = cand.load_json(cache_path, {})
    ses, out, plan_urls = web.new_session(), [], {}
    skipped = {"木造": 0, "写真が少ない": 0, "取得失敗": 0}
    for k in new_keys:
        r = min(groups[k], key=lambda x: ORDER.index(x["site"]))
        e = cache.get(r["url"])
        if e is None or e.get("v") != cand.CACHE_VERSION or not e.get("structure"):
            try:
                e = {**sites.DETAIL_PARSERS[r["site"]](sites.fetch(ses, r["url"])), "v": cand.CACHE_VERSION}
                if not e["structure"]:
                    raise ValueError("構造が読めない (ページの形が想定と違う)")
                cache[r["url"]] = e
            except Exception as ex:
                skipped["取得失敗"] += 1
                log(f"  詳細取得に失敗 (スキップ): {r['url']} {ex}")
                continue
            time.sleep(delay)
        if cand.is_wood(e):
            skipped["木造"] += 1
            continue
        if e["n_photos"] < min_photos or e["n_interior"] < 1:
            skipped["写真が少ない"] += 1
            continue
        line, st = r["station"].replace("東急", "").split("/")
        rid = row_id(r["site"], r["url"])
        row = cand.make_row(
            id=rid, site=r["site"], also="・".join(s for s in present[k] if s != r["site"]), url=r["url"],
            building=r["building"], line=line, station=st, walk=r["walk_min"], rent_yen=r["rent_yen"],
            admin_yen=r["admin_yen"] or 0, total_yen=r["rent_yen"] + (r["admin_yen"] or 0), area=r["area_m2"],
            age=r["age"], photos=e["n_photos"], d=e, layout=r["layout"])
        out.append(row)
        if e.get("plan_url"):
            plan_urls[rid] = e["plan_url"]
    cand.save_json(cache_path, cache)
    log(f"  取り込み {len(out)} 室 (除外: {', '.join(f'{k} {v}' for k, v in skipped.items() if v) or 'なし'})")
    return out, plan_urls, present
