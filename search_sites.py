# -*- coding: utf-8 -*-
"""HOME'S / at home / CHINTAI を横断して、沿線 + 間取り + 条件で検索し CSV に出力する。
    python search_sites.py --out sites.csv
"""
import argparse
import csv
import re
import sys
import time

import requests

import sites

# (サイト, 路線) -> 一覧URLと追加パラメータ。ここでは東京都側の東急東横線・目黒線 1LDK。
TARGETS = {
    "HOME'S": ("https://www.homes.co.jp/chintai/tokyo/{line}/list/", {"toyoko": "tokyutoyoko-line", "meguro": "tokyumeguro-line"}, sites.parse_homes),
    "at home": ("https://www.athome.co.jp/chintai/theme/madori_1ldk/tokyo/{line}/list/", {"toyoko": "tokyutoyoko-line", "meguro": "tokyumeguro-line"}, sites.parse_athome),
    "CHINTAI": ("https://www.chintai.net/tokyo/ensen/{line}/list/1ldk/", {"toyoko": "102050", "meguro": "102048"}, sites.parse_chintai),
}
ACCESS = re.compile(r"(東急東横線|東急目黒線)\s*/?\s*「?([^\s「」/]+?)」?駅\s*徒歩(\d+)分")


def page_url(site: str, base: str, page: int, max_rent: float, walk: int):
    params = {}
    if site == "HOME'S":
        params = {"cond[madori][15]": "15", "cond[monthmoneyroomh]": f"{max_rent:g}", "cond[walkminutesh]": str(walk)}
        if page > 1:
            params["page"] = str(page)
        return base, params
    return (base if page == 1 else f"{base}page{page}/"), None


def best_walk(access):
    best = None
    for t in access:
        if "バス" in t:
            continue
        m = ACCESS.search(t)
        if m and (best is None or int(m.group(3)) < best[0]):
            best = (int(m.group(3)), f"{m.group(1)}/{m.group(2)}")
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lines", nargs="*", default=["toyoko", "meguro"])
    ap.add_argument("--max-rent", type=float, default=18.0)
    ap.add_argument("--walk", type=int, default=10)
    ap.add_argument("--max-age", type=int, default=35)
    ap.add_argument("--max-pages", type=int, default=90)
    ap.add_argument("--delay", type=float, default=1.5)
    ap.add_argument("--sites", nargs="*", default=list(TARGETS), choices=list(TARGETS))
    ap.add_argument("--out", default="sites.csv")
    a = ap.parse_args()
    ses = requests.Session()
    got = {}
    stats = {}
    for site, (tmpl, slugs, fn) in ((k, v) for k, v in TARGETS.items() if k in a.sites):
        for line in a.lines:
            seen_before = len(got)
            n_pages = 0
            ses = requests.Session()  # サイト・路線ごとに新しいセッション (Cookie の持ち越しを避ける)
            for page in range(1, a.max_pages + 1):
                url, params = page_url(site, tmpl.format(line=slugs[line]), page, a.max_rent, a.walk)
                try:
                    rows = list(fn(sites.fetch(ses, url, params)))
                except requests.HTTPError as e:
                    if e.response is not None and e.response.status_code == 404:  # 最終ページの次
                        break
                    raise
                n_pages = page
                new = [r for r in rows if (site, r["url"]) not in got]
                for r in rows:
                    got.setdefault((site, r["url"]), r)
                print(f"{site} {line} p{page}: {len(rows)} rooms ({len(new)} new)", file=sys.stderr)
                if page == 1 and not rows:
                    print(f"  WARNING: {site} {line} page 1 returned no rooms", file=sys.stderr)
                if not new:
                    break
                time.sleep(a.delay)
            stats[(site, line)] = (n_pages, len(got) - seen_before)
    out = []
    for r in got.values():
        w = best_walk(r["access"])
        if (r["layout"] == "1LDK" and r["rent_yen"] and r["rent_yen"] <= a.max_rent * 10000 and w and w[0] <= a.walk
                and r["age"] is not None and r["age"] <= a.max_age):
            r["walk_min"], r["station"] = w
            r["access"] = " / ".join(r["access"])
            out.append(r)
    keys = list({k: 0 for r in out for k in r})
    with open(a.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(out)
    print(f"collected {len(got)} -> {len(out)} match -> {a.out}", file=sys.stderr)
    print(stats, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
