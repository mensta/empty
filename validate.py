# -*- coding: utf-8 -*-
"""書き出す前の自動検証。条件に合わない行・壊れたデータが混ざっていないかを確かめる。

これまで手作業で行っていた確認 (面積・家賃・徒歩・築年数の上下限、木造の混入、重複、間取り図の対応) を毎回自動で行う。
エラーがあれば run.py は既存の出力を上書きせずに止まる。警告は表示だけ。
"""
import re


def validate(cands, plans, conds, *, max_rent, walk, max_age, min_area, min_photos, layouts=None):
    errors, warnings = [], []
    if not cands:
        return ["候補が0件"], warnings

    ids, urls = {}, {}
    for r in cands:
        name = f"{r.get('building', '?')} ({r.get('id')})"
        if r["id"] in ids:
            errors.append(f"IDの重複: {name}")
        ids[r["id"]] = r
        if r["url"] in urls:
            errors.append(f"URLの重複: {name}")
        urls[r["url"]] = r
        if not str(r["url"]).startswith("https://"):
            errors.append(f"URLが不正: {name}")
        if layouts and r.get("layout") not in layouts:
            errors.append(f"間取りが条件外 ({r.get('layout')}): {name}")
        if not (r["area"] > min_area):
            errors.append(f"広さが条件外 ({r['area']}㎡): {name}")
        if r["rent"] > max_rent + 1e-9:
            errors.append(f"家賃が条件外 ({r['rent']}万円): {name}")
        if r["walk"] > walk:
            errors.append(f"徒歩が条件外 ({r['walk']}分): {name}")
        if r["age"] > max_age:
            errors.append(f"築年数が条件外 ({r['age']}年): {name}")
        if "木造" in r["structure"] or r["structure"] == "":
            errors.append(f"構造が木造または不明 ('{r['structure']}'): {name}")
        if r["group"] not in ("RC", "鉄骨・ALC"):
            errors.append(f"構造の分類が不正 ({r['group']}): {name}")
        if abs(r["rent"] + r["admin"] - r["total"]) > 0.06:
            errors.append(f"総額が家賃+管理費と合わない: {name}")
        if min_photos and r["photos"] < min_photos:
            errors.append(f"写真が少ない ({r['photos']}枚): {name}")
        if not (5 <= r["initial"] <= 150):
            errors.append(f"初期費用が不自然 ({r['initial']}万円): {name}")
        if not r["station"] or not r["line"]:
            errors.append(f"駅・路線が空: {name}")

    # 同じ部屋が別の行になっていないか (サイト間の重複除去の漏れ)
    seen = {}
    for r in cands:
        seen.setdefault((r["station"], round(r["area"], 1), r["rent"]), []).append(r)
    for k, v in seen.items():
        sites = {x.get("site", "SUUMO") for x in v}
        if len(v) > 1 and len(sites) > 1:
            errors.append(f"別サイトの同じ部屋が重複: {k} {sorted(sites)}")
        elif len(v) > 1:
            warnings.append(f"同じ駅・広さ・家賃の部屋が{len(v)}行 (同じ建物の別の部屋か、同じ部屋の重複): {v[0]['building']}")

    plan_ids = {p["id"] for p in plans}
    for pid in plan_ids - set(ids):
        errors.append(f"候補にない間取り図: {pid}")
    cover = len(plan_ids & set(ids)) / len(cands)
    if cover < 0.8:
        warnings.append(f"間取り図がある物件が {cover:.0%} と少なめ (取得失敗や、写真が入っていた物件が多い可能性)")

    rent_cond = next((c for c in conds if c.get("key") == "rent_max"), None)
    if not rent_cond or not isinstance(rent_cond.get("value"), (int, float)):
        errors.append("条件データに家賃の上限 (rent_max) がない")
    return errors, warnings
