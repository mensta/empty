# -*- coding: utf-8 -*-
"""HOME'S / at home / CHINTAI の沿線検索 (一覧ページ)。run.py から使う。単体でも動く:
    python search_sites.py --out sites.csv
"""
import argparse
import csv
import re
import sys
import time
import unicodedata

import requests
import web

import known_ids
import sites
import suumo_scraper as sc

# サイト -> (一覧URL, 路線ごとの slug, パーサー)。東京都側の1LDKの一覧。
TARGETS = {
    "HOME'S": ("https://www.homes.co.jp/chintai/tokyo/{line}/list/", {"toyoko": "tokyutoyoko-line", "meguro": "tokyumeguro-line"}, sites.parse_homes),
    "at home": ("https://www.athome.co.jp/chintai/theme/{layout}/tokyo/{line}/list/", {"toyoko": "tokyutoyoko-line", "meguro": "tokyumeguro-line"}, sites.parse_athome),
    "CHINTAI": ("https://www.chintai.net/tokyo/ensen/{line}/list/{layout}/", {"toyoko": "102050", "meguro": "102048"}, sites.parse_chintai),
}
# Per-site URL value for a layout (None = not supported by us). Only HOME'S 1LDK has a known code; other layouts are skipped there.
LAYOUT_SLUG = {
    "HOME'S": {"1LDK": "15"}.get,
    "at home": lambda x: f"madori_{x.lower()}",
    "CHINTAI": lambda x: x.lower(),
}


def page_url(site, base, page, max_rent, walk, layout="1LDK", sort_new=False):
    """sort_new: newest-first (used by the incremental crawl, see known_ids.SORT_NEW)."""
    sort_key, sort_val = known_ids.SORT_NEW[site]
    if site == "HOME'S":  # 間取り・家賃・徒歩は URL で絞れる
        code = LAYOUT_SLUG["HOME'S"](layout)
        params = {f"cond[madori][{code}]": code, "cond[monthmoneyroomh]": f"{max_rent:g}", "cond[walkminutesh]": str(walk)}
        if sort_new:
            params[sort_key] = sort_val
        if page > 1:
            params["page"] = str(page)
        return base, params
    return (base if page == 1 else f"{base}page{page}/"), ({sort_key: sort_val} if sort_new else None)


def access_regex(lines):
    names = "|".join(re.escape(sc.LINES[l][1]) for l in lines)
    return re.compile(rf"({names})\s*/?\s*「?([^\s「」/]+?)」?駅\s*徒歩(\d+)分")


def best_walk(access, lines):
    """対象路線の駅のうち最短の徒歩 (バス除く)。(分, '路線/駅') か None"""
    rx, best = access_regex(lines), None
    for t in access:
        if "バス" in t:
            continue
        m = rx.search(t)
        if m and (best is None or int(m.group(3)) < best[0]):
            best = (int(m.group(3)), f"{m.group(1)}/{m.group(2)}")
    return best


def collect(lines, max_rent, walk, max_pages=90, delay=1.5, only=None, log=print, layouts=("1LDK",), incremental=None):
    """3サイトの一覧を最後のページまで集める。戻り値: (物件のリスト, 取得できなかったサイト)。
    あるサイトで取得に失敗し続けたら (アクセス制限など)、そのサイトは今回は丸ごと外して続ける。
    SUUMO が本体で、他サイトは補助のため。取得できなかったことは呼び出し側が表示に反映する。

    incremental: {サイト名: 既知の URL の集合}。そのサイトは新着順で取り、ページ内の物件がすべて既知なら
    そこで打ち切る (リクエスト数を減らす)。このとき戻り値は新しいページ分だけなので、呼び出し側が
    known_ids.merge_rows で前回の結果と合わせる。"""
    got, failed, incremental = {}, [], incremental or {}
    for site, (tmpl, slugs, fn) in TARGETS.items():
        if only and site not in only:
            continue
        slug_of = LAYOUT_SLUG.get(site, lambda x: x.lower())
        usable = [x for x in layouts if slug_of(x)]
        if len(usable) < len(layouts):
            log(f"  {site}: 未対応の間取りは取得しません ({'・'.join(x for x in layouts if x not in usable)})")
        for line in lines:
            for layout in usable:
                if site in failed:
                    break
                known = incremental.get(site)  # None = 全ページ取得
                ses, n_before = web.new_session(), len(got)  # new connection per site / line / layout
                try:
                    for page in range(1, max_pages + 1):
                        url, params = page_url(site, tmpl.format(line=slugs[line], layout=slug_of(layout)), page, max_rent, walk, layout, sort_new=known is not None)
                        try:
                            rows = list(fn(sites.fetch(ses, url, params)))
                        except requests.HTTPError as e:
                            if e.response is not None and e.response.status_code == 404:  # 最終ページの次 (or no listings for this layout)
                                break
                            raise
                        new = [r for r in rows if (site, r["url"]) not in got]
                        for r in rows:
                            got.setdefault((site, r["url"]), r)
                        if page == 1 and not rows:
                            raise RuntimeError("1ページ目が空でした")
                        if not new:
                            break
                        if known is not None and all(r["url"] in known for r in rows):
                            break  # 新着順なので、これより先はすべて既知
                        time.sleep(delay)
                    log(f"  {site} {line} {layout}: {page} ページ、{len(got) - n_before} 件" + (" (増分)" if known is not None else ""))
                except RuntimeError as e:
                    failed.append(site)
                    where = f"{line} {layout} の {page} ページ目"  # page は for の変数 (ここへは取得中にしか来ない)
                    log(f"  WARNING: {site} は取得できませんでした。今回は {site} を含めません ({where}で: {str(e).split(': http')[0][:90]})")
    got = {k: v for k, v in got.items() if k[0] not in failed}
    return list(got.values()), failed


def filter_rows(rows, lines, layout, max_rent, walk, max_age, min_area, pref_prefix="東京都"):
    """条件に合う物件だけ残し、最寄り駅 (station) と徒歩 (walk_min) を付ける。layout は名前または名前のリスト (完全一致。2SLDK などは含めない)"""
    layouts = sc.as_layouts(layout)
    out = []
    for r in rows:
        w = best_walk(r["access"], lines)
        addr = unicodedata.normalize("NFKC", r["address"])
        in_pref = addr.startswith(pref_prefix) or (r["site"] == "at home" and not re.match(r"(東京都|神奈川県|埼玉県|千葉県)", addr))
        if (r["layout"] in layouts and r["rent_yen"] and r["rent_yen"] <= max_rent * 10000 and w and w[0] <= walk
                and r["age"] is not None and r["age"] <= max_age and r["area_m2"] and r["area_m2"] > min_area and in_pref):
            out.append({**r, "walk_min": w[0], "station": w[1]})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lines", nargs="*", default=["toyoko", "meguro"])
    ap.add_argument("--layout", nargs="+", default=["1LDK"], choices=list(sc.LAYOUT_CODES))
    ap.add_argument("--max-rent", type=float, default=18.0)
    ap.add_argument("--walk", type=int, default=7)
    ap.add_argument("--max-age", type=int, default=20)
    ap.add_argument("--min-area", type=float, default=28.0)
    ap.add_argument("--delay", type=float, default=1.5)
    ap.add_argument("--out", default="sites.csv")
    web.add_proxy_argument(ap)
    a = ap.parse_args()
    try:
        web.configure_proxy(a.proxy)
    except ValueError as e:
        ap.error(str(e))
    rows, _ = collect(a.lines, a.max_rent, a.walk, delay=a.delay, log=lambda m: print(m, file=sys.stderr), layouts=a.layout)
    out = filter_rows(rows, a.lines, a.layout, a.max_rent, a.walk, a.max_age, a.min_area)
    for r in out:
        r["access"] = " / ".join(r["access"])
    keys = list({k: 0 for r in out for k in r})
    with open(a.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(out)
    print(f"collected {len(rows)} -> {len(out)} match -> {a.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
