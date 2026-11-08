# -*- coding: utf-8 -*-
"""SUUMO 賃貸の一覧・詳細ページを取得する最小スクレイパー（個人利用・低頻度アクセス前提）。

依存: requests, beautifulsoup4
使い方:
    python suumo_scraper.py --pages 2 --detail 3 --out out.csv
"""
import argparse
import csv
import re
import sys
import time
from typing import Dict, Iterator, List, Optional

import requests
from bs4 import BeautifulSoup

BASE = "https://suumo.jp"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "ja,en;q=0.8",
}
# 例: 東京都新宿区 (sc=13104)。他区は sc を変える。ar=030(関東) bs=040(賃貸) ta=13(東京)
SEARCH_URL = (
    "https://suumo.jp/jj/chintai/ichiran/FR301FC001/"
    "?ar=030&bs=040&ta=13&sc={sc}&cb=0.0&ct=9999999&et=9999999&cn=9999999"
    "&mb=0&mt=9999999&shkr1=03&shkr2=03&shkr3=03&shkr4=03&fw2=&page={page}"
)


def clean(s: Optional[str]) -> str:
    return " ".join(s.split()) if s else ""


def fetch(session: requests.Session, url: str, retries: int = 3) -> BeautifulSoup:
    for i in range(retries):
        try:
            r = session.get(url, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return BeautifulSoup(r.content, "html.parser")
        except requests.RequestException as e:
            if i == retries - 1:
                raise
            time.sleep(2 ** (i + 1))
    raise RuntimeError("unreachable")


def parse_list(soup: BeautifulSoup) -> Iterator[Dict[str, str]]:
    """一覧ページ → 部屋単位のレコード（建物情報を各部屋に付与）"""
    for it in soup.select("div.cassetteitem"):
        building = clean(it.select_one(".cassetteitem_content-title").get_text())
        address = clean(it.select_one(".cassetteitem_detail-col1").get_text())
        access = [clean(x.get_text()) for x in it.select(".cassetteitem_detail-col2 .cassetteitem_detail-text")]
        col3 = [clean(x.get_text()) for x in it.select(".cassetteitem_detail-col3 div")]
        for tr in it.select("table.cassetteitem_other tbody tr"):
            a = tr.select_one("a.js-cassette_link_href")
            if not a:
                continue
            g = lambda cls: clean(tr.select_one(cls).get_text()) if tr.select_one(cls) else ""
            yield {
                "building": building,
                "address": address,
                "access": " / ".join(access),
                "age": col3[0] if col3 else "",
                "stories": col3[1] if len(col3) > 1 else "",
                "floor": clean(tr.find_all("td")[2].get_text()),
                "rent": g(".cassetteitem_price--rent"),
                "admin_fee": g(".cassetteitem_price--administration"),
                "deposit": g(".cassetteitem_price--deposit"),
                "gratuity": g(".cassetteitem_price--gratuity"),
                "layout": g(".cassetteitem_madori"),
                "area": g(".cassetteitem_menseki"),
                "url": BASE + a["href"],
            }


def parse_detail(soup: BeautifulSoup) -> Dict[str, str]:
    """詳細ページ → th/td の表をそのまま辞書化 + 主要項目"""
    table: Dict[str, str] = {}
    for tr in soup.select("tr"):
        ths, tds = tr.find_all("th"), tr.find_all("td")
        for th, td in zip(ths, tds):
            table[clean(th.get_text())] = clean(td.get_text())
    h1 = soup.find("h1", class_="section_h1-header-title")
    feat = soup.find("div", id="bkdt-option")
    return {
        "detail_name": clean(h1.get_text()) if h1 else "",
        "detail_features": clean(feat.get_text()) if feat else "",
        **{f"detail_{k}": v for k, v in table.items() if k in ("構造", "階建", "入居", "条件", "総戸数", "損保", "駐車場", "仲介手数料", "取引態様", "保証会社")},
    }


def total_hits(soup: BeautifulSoup) -> str:
    t = soup.select_one(".paginate_set-hit") or soup.select_one(".pagination_set-hit")
    return clean(t.get_text())[:20] if t else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sc", default="13104", help="市区町村コード (default: 新宿区)")
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--detail", type=int, default=0, help="先頭N件の詳細ページも取得")
    ap.add_argument("--delay", type=float, default=1.5, help="リクエスト間隔(秒)")
    ap.add_argument("--out", default="out.csv")
    args = ap.parse_args()

    s = requests.Session()
    rows: List[Dict[str, str]] = []
    for p in range(1, args.pages + 1):
        soup = fetch(s, SEARCH_URL.format(sc=args.sc, page=p))
        if p == 1:
            print("総件数:", total_hits(soup), file=sys.stderr)
        got = list(parse_list(soup))
        print(f"page {p}: {len(got)} rooms", file=sys.stderr)
        rows += got
        time.sleep(args.delay)
    for r in rows[: args.detail]:
        r.update(parse_detail(fetch(s, r["url"])))
        time.sleep(args.delay)

    keys = list({k: 0 for r in rows for k in r})
    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
