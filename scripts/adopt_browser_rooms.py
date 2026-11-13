# -*- coding: utf-8 -*-
"""ブラウザで取った HOME'S (詳細 HTML) と DOOR賃貸 (data/door_extra.json) の新しい部屋を、data/candidates.json に足す。

通信はしない (保存済みの HTML と JSON だけを読む)。使い方:
  python3 scripts/adopt_browser_rooms.py --found found.json --targets targets.json --details details/ [--write]
--write なしは試算だけ (candidates.json を書き換えない)。--write のときは、先に --backup のパスへ現状を複写する。
"""
import argparse
import json
import os
import shutil
import sys

from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import candidates as cand  # noqa: E402
import others  # noqa: E402
import sites  # noqa: E402


def homes_inputs(found_path, targets_path, details_dir):
    """詳細ページを取れた HOME'S の部屋の (一覧の行, 詳細キャッシュ)"""
    found = {r["url"]: r for r in json.load(open(found_path, encoding="utf-8"))}
    rows, cache = [], {}
    for t in json.load(open(targets_path, encoding="utf-8")):
        p = os.path.join(details_dir, t["url"].rstrip("/").split("/")[-1] + ".html")
        if t["url"] not in found or not os.path.exists(p):
            continue
        rows.append(found[t["url"]])
        cache[t["url"]] = {**sites.detail_homes(BeautifulSoup(open(p, encoding="utf-8"), "html.parser")), "v": cand.CACHE_VERSION}
    return rows, cache


def drop_existing(new_rows, existing):
    """既存の候補と同じ部屋 (駅・面積・間取り・家賃+管理費が同じ) を除く。候補には住所がないので、この近似で照合する"""
    have = {(c["station"], round(c["area"], 1), c["layout"], round(c["total"], 1)) for c in existing}
    keep = [r for r in new_rows if (r["station"], round(r["area"], 1), r["layout"], round(r["total"], 1)) not in have]
    return keep, [r for r in new_rows if r not in keep]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--found", required=True)
    ap.add_argument("--targets", required=True)
    ap.add_argument("--details", required=True)
    ap.add_argument("--door", default=os.path.join(ROOT, "data", "door_extra.json"))
    ap.add_argument("--candidates", default=os.path.join(ROOT, "data", "candidates.json"))
    ap.add_argument("--backup")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    hm_rows, cache = homes_inputs(a.found, a.targets, a.details)
    door = json.load(open(a.door, encoding="utf-8"))
    for r in door:
        cache[r["url"]] = others.door_detail(r)
    rows = hm_rows + [{k: v for k, v in r.items() if k != "detail"} for r in door]
    print(f"HOME'S {len(hm_rows)} 室 + DOOR {len(door)} 室")

    tmp = os.path.join(ROOT, "data", ".adopt_cache.json")
    cand.save_json(tmp, cache)
    try:
        new, _, _ = others.build_other_rows(rows, set(), tmp)
    finally:
        os.remove(tmp)
    existing = json.load(open(a.candidates, encoding="utf-8"))
    new, dup = drop_existing(new, existing)
    by_site = {s: sum(r["site"] == s for r in new) for s in ("HOME'S", "DOOR")}
    print(f"既存の候補と重複して除外: {len(dup)} 室 / 追加: {len(new)} 室 {by_site}")
    out = sorted(existing + new, key=lambda r: r["total"])
    print(f"候補 {len(existing)} -> {len(out)} 室")
    if a.write:
        if not a.backup:
            sys.exit("--write には --backup が要る")
        shutil.copy(a.candidates, a.backup)
        cand.save_json(a.candidates, out)
        print("書き込み済み。バックアップ:", a.backup)


if __name__ == "__main__":
    main()
