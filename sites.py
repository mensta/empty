# -*- coding: utf-8 -*-
"""SUUMO 以外の賃貸ポータル (LIFULL HOME'S / at home / CHINTAI) の一覧ページ・パーサー。

どのサイトも共通の辞書形式で返す:
  site, building, address, access(list), age, layout, area_m2, floor,
  rent_yen, admin_yen, shiki, rei, url
個人利用・低頻度アクセス前提。各サイトの利用規約・robots.txt を確認すること。
"""
import datetime
import re
from typing import Dict, Iterator, List, Optional

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "ja,en;q=0.8",
}


def clean(s: Optional[str]) -> str:
    return " ".join(s.split()) if s else ""


def yen(s: str) -> Optional[int]:
    """'12 万円' / '18.8' (万円前提で呼ぶ側が付与) / '18,000円' -> 円"""
    s = clean(s).replace(",", "").replace(" ", "")
    m = re.search(r"([\d.]+)万円?", s)
    if m:
        return int(round(float(m.group(1)) * 10000))
    m = re.search(r"([\d.]+)円", s)
    return int(m.group(1).split(".")[0]) if m else None


def fetch(session: requests.Session, url: str, params=None) -> BeautifulSoup:
    r = session.get(url, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.content, "html.parser")


def _age(s: str) -> Optional[int]:
    """'築5年' / '新築' / '1年未満' / '建築中' / '2026年3月' (築年表記なしの竣工年月) -> 築年数"""
    m = re.search(r"築(\d+)年", s)
    if m:
        return int(m.group(1))
    if re.search(r"新築|未満|建築中", s):
        return 0
    m = re.search(r"(?<!\d)(\d{1,2})年(?!築|月|\d)", s)  # HOME'S: '2年 / 5階建'
    if m:
        return int(m.group(1))
    m = re.search(r"(20\d\d)年", s)
    return max(0, datetime.date.today().year - int(m.group(1))) if m else None


def _area(s: str) -> Optional[float]:
    m = re.search(r"([\d.]+)\s*m", s)
    return float(m.group(1)) if m else None


# ---------------------------------------------------------------- LIFULL HOME'S
def parse_homes(soup: BeautifulSoup) -> Iterator[Dict]:
    for b in soup.select("div.prg-building"):
        name = b.select_one(".bukkenName")
        info = {clean(th.get_text()): td for th in b.select("table th") if (td := th.find_next_sibling("td"))}
        access = [clean(x.get_text()) for x in b.select(".prg-stationText")]
        age = _age(clean(info["築年数/階数"].get_text())) if "築年数/階数" in info else None
        for tr in b.select("table.unitSummary tr"):
            price, layout = tr.select_one("td.price"), tr.select_one("td.layout")
            a = tr.select_one("a.prg-detailAnchor")
            if not (price and layout and a):
                continue
            ptxt = clean(price.get_text(" "))
            parts = ptxt.split("/", 1)
            tail = parts[1].split() if len(parts) > 1 else []
            sk = tail[1].split("/") if len(tail) > 1 else []
            yield {
                "site": "HOME'S", "building": clean(name.get_text()) if name else "",
                "address": clean(info["所在地"].get_text()) if "所在地" in info else "",
                "access": access, "age": age,
                "layout": clean(layout.get_text(" ")).split(" ")[0], "area_m2": _area(layout.get_text()),
                "floor": clean(tr.select_one("td.floar").get_text(" ")).split(" ")[0] if tr.select_one("td.floar") else "", "structure": "",
                "rent_yen": yen(parts[0]), "admin_yen": yen(tail[0]) if tail else None,
                "shiki": sk[0] if len(sk) > 0 else "", "rei": sk[1] if len(sk) > 1 else "",
                "url": a["href"].split("?")[0],
            }


# ---------------------------------------------------------------- at home
def parse_athome(soup: BeautifulSoup) -> Iterator[Dict]:
    for c in soup.select("div.property-card"):
        title = c.select_one("h2.property-title")
        loc = c.select_one("li.info-item--location")
        st = [clean(p.get_text()) for p in c.select("li.info-item--station p")]
        typ = clean(c.select_one("li.info-item--type").get_text(" ")) if c.select_one("li.info-item--type") else ""
        age = _age(typ)
        for r in c.select("div.room-info"):
            a = r.find_parent("a", href=True)
            rv = r.select_one("span.rent-value")
            if not (a and rv):
                continue
            li = {k: r.select_one(f"li.{k}") for k in ("room-number", "price", "fees", "layout-size")}
            price_txts = [clean(x.get_text()) for x in li["price"].select("span.room-info-item__text")]
            admin = next((t for t in price_txts if "万" not in t and t.endswith("円")), "")
            fees = [clean(x.get_text()) for x in li["fees"].select("span.room-info-item__text")] if li["fees"] else []
            ls = clean(li["layout-size"].get_text(" ")) if li["layout-size"] else ""
            yield {
                "site": "at home", "building": clean(title.get_text()) if title else "",
                "address": clean(loc.get_text()) if loc else "", "access": st, "age": age,
                "layout": ls.split(" ")[0], "area_m2": _area(ls), "floor": "", "structure": "",
                "rent_yen": yen(rv.get_text() + "万円"), "admin_yen": yen(admin) if admin else None,
                "shiki": fees[0] if fees else "", "rei": fees[1] if len(fees) > 1 else "",
                "url": "https://www.athome.co.jp" + a["href"].split("?")[0],
            }


# ---------------------------------------------------------------- CHINTAI
def parse_chintai(soup: BeautifulSoup) -> Iterator[Dict]:
    """建物ごとの表 (section.cassette_item.build): 住所/交通/築年/階建/構造 + 部屋行 (td.price ...)。PR枠は除く。"""
    for it in soup.select("section.cassette_item.build"):
        info = {clean(th.get_text()): clean(th.find_next_sibling("td").get_text(" "))
                for th in it.select("th") if th.find_next_sibling("td")}
        ttl = it.select_one(".cassette_ttl")
        name = re.sub(r"^(賃貸\S+)\s+", "", clean(ttl.get_text(" "))) if ttl else ""
        access = re.findall(r"\S+?/\S+?(?:駅|停)\s*(?:徒歩\d+分|バス\S+)", info.get("交通", ""))
        age = _age(info.get("築年", ""))
        for tr in it.select("tr"):
            p = tr.select_one("td.price")
            if not p:
                continue
            a = tr.select_one("td.detail a[href^='/detail/']")
            ptxt = clean(p.get_text(" "))
            pm = re.match(r"([\d.]+)\s*万円\s*(--|-|[\d,]+円)?", ptxt)
            sr = clean(tr.select_one("td.other_price").get_text(" ")).split(" ") if tr.select_one("td.other_price") else []
            lay = next((clean(td.get_text(" ")) for td in tr.find_all("td") if re.search(r"m²", td.get_text())), "")
            if not (pm and a):
                continue
            yield {
                "site": "CHINTAI", "building": name, "address": info.get("住所", "").replace(" 周辺地図", ""),
                "access": access, "age": age, "structure": info.get("構造", ""),
                "layout": lay.split(" ")[0], "area_m2": _area(lay),
                "floor": clean(tr.select_one("td.floar").get_text(" ")).split(" ")[0] if tr.select_one("td.floar") else "",
                "rent_yen": yen(pm.group(1) + "万円"),
                "admin_yen": yen(pm.group(2)) if pm.group(2) and pm.group(2).endswith("円") else None,
                "shiki": sr[0] if sr else "", "rei": sr[1] if len(sr) > 1 else "",
                "url": "https://www.chintai.net" + a["href"].split("?")[0],
            }
