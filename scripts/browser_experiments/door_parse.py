# -*- coding: utf-8 -*-
"""DOOR (door.ac) list and building page parsers.

The pages are fetched with a headless browser (see door_crawl.mjs) and saved as HTML;
this module only parses the saved HTML. Rows use the same dict shape as sites.py
(site, building, address, access, age, layout, area_m2, floor, rent_yen, admin_yen, shiki, rei, url)
so that search_sites.filter_rows and others.room_key work on them unchanged.
"""
import glob
import json
import os
import re
import sys
import unicodedata
from typing import Dict, Iterator, List, Optional

from bs4 import BeautifulSoup

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import sites  # noqa: E402

BASE = "https://door.ac"
SITE = "DOOR"


def _nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", sites.clean(s))


def _fee(s: str) -> Optional[int]:
    """'なし' / '-' -> 0, '5,000円' / '1.2万円' -> yen, anything else -> None"""
    s = _nfkc(s)
    if s in ("なし", "-", "ー", ""):
        return 0
    return sites.yen(s)


def _access(dd) -> List[str]:
    """'東急東横線 中目黒駅 徒歩5分' lines -> '東急東横線/中目黒駅 徒歩5分' (the shape the other sites use)"""
    out = []
    for chunk in dd.stripped_strings:
        t = _nfkc(chunk)
        m = re.match(r"(.+?)\s+(\S+?駅)\s*(.*)$", t)
        out.append(f"{m.group(1)}/{m.group(2)} {m.group(3)}".strip() if m else t)
    return out


def parse_door_list(html: str) -> Iterator[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    for box in soup.select(".building-box"):
        a = box.select_one(".building-box__head h2 a")
        if not a:
            continue
        name = re.sub(r"の賃貸物件情報$", "", sites.clean(a.get_text()))
        info = {}
        for dl in box.select("dl.description-item"):
            label = sites.clean(dl.select_one("dt").get_text())
            dd = dl.select_one("dd")
            info[label] = dd
        if not info.get("所在地"):
            continue
        address = _nfkc(info["所在地"].get_text())
        age = sites._age(_nfkc(info["築年数"].get_text())) if info.get("築年数") else None
        access = _access(info["最寄駅"]) if info.get("最寄駅") else []
        bid = a["href"].rstrip("/").split("/")[-1]
        for tr in box.select("tbody tr"):
            tds = tr.find_all("td", recursive=False)
            link = tr.select_one("a[href*='/properties/']")
            if len(tds) < 6 or not link:
                continue
            shiki, _, rei = (_nfkc(tds[3].get_text(" ")).partition("/"))
            yield {
                "site": SITE, "building": name, "building_id": bid, "address": address, "access": access, "age": age,
                "layout": _nfkc(tds[4].get_text()), "area_m2": sites._area(_nfkc(tds[5].get_text())),
                "floor": _nfkc(tds[0].get_text()), "rent_yen": sites.yen(_nfkc(tds[1].get_text())),
                "admin_yen": _fee(tds[2].get_text()), "shiki": sites.clean(shiki), "rei": sites.clean(rei),
                "url": BASE + link["href"].split("?")[0],
            }


def parse_door_building(html: str) -> Dict:
    """Building page -> {'structure': 'RC(...)', 'floors': '12階建', 'built': '2015年9月 / 築10年'}"""
    soup = BeautifulSoup(html, "html.parser")
    d = {}
    for dl in soup.select("dl"):
        dt, dd = dl.find("dt"), dl.find("dd")
        if not dt or not dd:
            continue
        label, val = sites.clean(dt.get_text()), sites.clean(dd.get_text(" "))
        if label == "建物構造":
            d["structure"] = val.split("/", 1)[-1].strip()
        elif label == "建階":
            d["floors"] = val
        elif label == "築年月":
            d["built"] = val
    return d


def load_list_pages(pages_dir: str) -> List[Dict]:
    """All saved list pages (toyoko_001.html ...) -> de-duplicated rows"""
    seen, rows = set(), []
    for f in sorted(glob.glob(os.path.join(pages_dir, "*.html"))):
        with open(f, encoding="utf-8") as fh:
            for r in parse_door_list(fh.read()):
                if r["url"] not in seen:
                    seen.add(r["url"])
                    rows.append(r)
    return rows


if __name__ == "__main__":
    pages = sys.argv[1] if len(sys.argv) > 1 else "/tmp/opencode/probe/pages/door"
    rows = load_list_pages(pages)
    print(len(rows), "rows;", len({r["building_id"] for r in rows}), "buildings")
    print(json.dumps(rows[:2], ensure_ascii=False, indent=1))


def parse_door_property(html: str) -> Dict:
    """Room page -> photo counts, floor plan, deposit/key money, renewal fee, guarantor company, contract type, equipment."""
    soup = BeautifulSoup(html, "html.parser")
    d = {"n_photos": 0, "n_interior": 0, "has_plan": False}
    # The src of every image is a placeholder while images are blocked in the browser, so count by the alt text.
    for img in soup.select(".properties__slideshow-image-inner img"):
        alt = img.get("alt") or ""
        if "写真" not in alt:
            continue
        d["n_photos"] += 1
        if re.search(r"内装|居間|キッチン|風呂|トイレ|玄関|洗面|収納|バルコニー|設備", alt):
            d["n_interior"] += 1
        if "間取" in alt:
            d["has_plan"] = True
    for tr in soup.select("tr, dl"):
        if tr.name == "tr" and not tr.find("td"):
            continue  # header row: its th cells are not key/value pairs
        cells = [sites.clean(c.get_text(" ")) for c in tr.find_all(["th", "td", "dt", "dd"], recursive=False)]
        for i in range(0, len(cells) - 1, 2):
            k, v = cells[i], cells[i + 1]
            if k in ("更新料", "保証会社利用", "契約形態", "保証会社費用", "建物構造", "設備", "敷金", "礼金", "入居・引渡期間") and k not in d:
                d[k] = v
    return d


# ---------------------------------------------------------------- Tokyu Housing Lease (rent.tokyu-housing-lease.co.jp)
TOKYU_BASE = "https://rent.tokyu-housing-lease.co.jp"
TOKYU_SITE = "東急住宅リース"


def _man(s: str) -> Optional[int]:
    """'18.1万円' / '2万円' / 'なし' -> yen (なし = 0)"""
    s = _nfkc(s)
    return 0 if s in ("なし", "-", "") else sites.yen(s)


def parse_tokyu_list(html: str) -> Iterator[Dict]:
    """One row per room. The list page already has structure, built year and every vacant room of the building."""
    soup = BeautifulSoup(html, "html.parser")
    for item in soup.select(".rent_item"):
        a = item.select_one("h2 a")
        if not a:
            continue
        name = sites.clean(a.get_text())
        info = {}
        for tr in item.select(".info table tr"):
            cells = tr.find_all(["th", "td"], recursive=False)
            for i in range(0, len(cells) - 1, 2):
                if cells[i].name == "th":
                    info[sites.clean(cells[i].get_text())] = sites.clean(cells[i + 1].get_text(" "))
        if info.get("物件種別") and not re.search(r"マンション|アパート|一戸建|テラス", info["物件種別"]):
            continue  # shops and offices
        access = [_nfkc(x) for x in [info.get("交通", "")] if x]
        built = _nfkc(info.get("築年月", ""))
        for tr in item.select(".item_room_table tbody tr"):
            tds = tr.find_all("td", recursive=False)
            link = tr.select_one("a[href^='/rent/']")
            if len(tds) < 6 or not link:
                continue
            m = re.search(r"(\S+号室)", sites.clean(tds[1].get_text(" ")))
            room = m.group(1) if m else ""
            layout, _, area = _nfkc(tds[2].get_text(" ")).partition("/")
            rent, _, admin = _nfkc(tds[3].get_text(" ")).partition("/")
            shiki, _, rei = _nfkc(tds[4].get_text(" ")).partition("/")
            yield {
                "site": TOKYU_SITE, "building": name, "building_id": a["href"].rstrip("/").split("/")[-1],
                "address": _nfkc(info.get("所在地", "")), "access": access, "age": sites._age(built) if built else None,
                "structure": info.get("構造"), "layout": layout.strip(), "area_m2": sites._area(area), "floor": room,
                "rent_yen": sites.yen(rent), "admin_yen": _man(admin), "shiki": sites.clean(shiki), "rei": sites.clean(rei),
                "url": TOKYU_BASE + link["href"].split("?")[0],
            }


def load_tokyu_pages(pages_dir: str) -> List[Dict]:
    seen, rows = set(), []
    for f in sorted(glob.glob(os.path.join(pages_dir, "*.html"))):
        with open(f, encoding="utf-8") as fh:
            for r in parse_tokyu_list(fh.read()):
                if r["url"] not in seen:
                    seen.add(r["url"])
                    rows.append(r)
    return rows
