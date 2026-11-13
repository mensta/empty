# -*- coding: utf-8 -*-
"""Turn saved DOOR list pages into raw rows, filter them with the repo conditions, drop rooms that SUUMO or the other
sites already have, and print what is new.  Usage (from the repo root):

    GAP=4 OUT=/tmp/pages/door node scripts/browser_experiments/door_crawl.mjs      # step 1: list pages
    python3 scripts/browser_experiments/door_report.py --pages /tmp/pages/door --ids /tmp/pages/door_ids.json
    OUT=/tmp/pages/door_b node scripts/browser_experiments/door_buildings.mjs /tmp/pages/door_ids.json   # step 2
    python3 scripts/browser_experiments/door_report.py --pages /tmp/pages/door --buildings /tmp/pages/door_b --out data/door_extra.json

DOOR lists the same room once per brokerage, so rooms are de-duplicated with others.room_key before anything is counted.
"""
import argparse
import collections
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path[:0] = [HERE, ROOT]
import candidates as cand  # noqa: E402
import door_parse as dp  # noqa: E402
import others  # noqa: E402
import search_sites as ss  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", required=True, help="directory with the saved list pages (several directories: comma separated)")
    ap.add_argument("--buildings", help="directory with saved building pages (step 2)")
    ap.add_argument("--ids", help="write the building ids that still need a structure to this JSON file (step 1)")
    ap.add_argument("--out", help="write the new, non-wood rooms to this JSON file (step 2)")
    ap.add_argument("--max-rent", type=float, default=19.0)
    ap.add_argument("--walk", type=int, default=10)
    ap.add_argument("--max-age", type=int, default=35)
    ap.add_argument("--min-area", type=float, default=28.0)
    ap.add_argument("--layout", nargs="+", default=["1LDK", "2DK", "2LDK"])
    a = ap.parse_args()

    raw = {}
    for d in a.pages.split(","):
        for f in sorted(glob.glob(os.path.join(d, "*.html"))):
            for r in dp.parse_door_list(open(f, encoding="utf-8").read()):
                raw.setdefault(r["url"], r)
    raw = list(raw.values())
    found = ss.filter_rows(raw, ["toyoko", "meguro"], a.layout, a.max_rent, a.walk, a.max_age, a.min_area, include_admin=True)
    groups = {}
    for r in found:
        groups.setdefault(others.room_key(r["address"], r["area_m2"], r["rent_yen"]), []).append(r)
    print(f"list rows {len(raw)} -> match conditions {len(found)} -> distinct rooms {len(groups)}")

    cands = cand.load_json(os.path.join(ROOT, "data", "candidates.json"), [])
    cand_keys = {(round(c["area"], 1), round(c["total"] * 10), c["layout"]) for c in cands}
    oth = cand.load_json(os.path.join(ROOT, "data", "others_raw.json"), [])
    oth_keys = {others.room_key(r["address"], r["area_m2"], r["rent_yen"]) for r in oth if r.get("area_m2") and r.get("rent_yen")}

    def total_key(r):
        return (round(r["area_m2"], 1), round((r["rent_yen"] + (r["admin_yen"] or 0)) / 1000), r["layout"])

    new = [dict(v[0], listings=len(v)) for k, v in groups.items() if total_key(v[0]) not in cand_keys and k not in oth_keys]
    seen = sum(1 for k, v in groups.items() if total_key(v[0]) in cand_keys)
    print(f"already SUUMO candidates: {seen}; already in other sites: {sum(1 for k in groups if k in oth_keys)}; new: {len(new)}")
    if a.ids:
        json.dump(sorted({r["building_id"] for r in new}), open(a.ids, "w"))
        print(f"{len({r['building_id'] for r in new})} building pages are needed -> {a.ids}")
    if a.buildings:
        keep, wood, miss = [], 0, 0
        for r in new:
            p = os.path.join(a.buildings, r["building_id"] + ".html")
            if not os.path.exists(p):
                miss += 1
                continue
            b = dp.parse_door_building(open(p, encoding="utf-8").read())
            if not b.get("structure"):
                miss += 1
                continue
            r = dict(r, structure=b["structure"], floors=b.get("floors"))
            if cand.is_wood(r):
                wood += 1
            else:
                keep.append(r)
        print(f"new rooms {len(new)}: wood {wood}, no structure {miss}, kept {len(keep)}", collections.Counter(cand.norm_structure(r["structure"]) for r in keep))
        for r in sorted(keep, key=lambda r: r["rent_yen"] + (r["admin_yen"] or 0)):
            print(f"  {r['building'][:22]:24s} {r['layout']:5s} {r['area_m2']:6.2f}m2 {(r['rent_yen'] + (r['admin_yen'] or 0)) / 10000:5.1f}man age {r['age']:>2} {r['url']}")
        if a.out:
            json.dump(keep, open(a.out, "w"), ensure_ascii=False, indent=1)
            print("saved", a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
