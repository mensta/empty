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

import web

BASE = "https://suumo.jp"
HEADERS = web.HEADERS
# 例: 東京都新宿区 (sc=13104)。他区は sc を変える。ar=030(関東) bs=040(賃貸) ta=13(東京)
SEARCH_URL = (
    "https://suumo.jp/jj/chintai/ichiran/FR301FC001/"
    "?ar=030&bs=040&ta=13&sc={sc}&cb=0.0&ct=9999999&et=9999999&cn=9999999"
    "&mb=0&mt=9999999&shkr1=03&shkr2=03&shkr3=03&shkr4=03&fw2=&page={page}"
)


def clean(s: Optional[str]) -> str:
    return " ".join(s.split()) if s else ""


def fetch(session: requests.Session, url: str, retries: int = web.RETRIES) -> BeautifulSoup:
    return web.fetch_soup(session, url, None, retries)


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



# ---------- 沿線・条件指定検索 (部屋ごと表示: div.property) ----------
LINES = {"toyoko": ("en_tokyutoyokosen", "東急東横線"), "meguro": ("en_tokyumegurosen", "東急目黒線")}
PREFS = {"tokyo": "東京都", "kanagawa": "神奈川県"}
LINE_URL = (
    "https://suumo.jp/jj/chintai/ichiran/FR301FC005/?ar=030&bs=040&ra={ra}&rn={rn}{ek}"
    "&cb=0.0&ct={rent}&et={walk}&cn=9999999&mb=0&mt=9999999&md={md}"
    "&shkr1=03&shkr2=03&shkr3=03&shkr4=03&fw2=&page={page}"
)
# SUUMO の徒歩・築年数は段階値のみ。API 側は緩めに絞り、取得後に厳密に再フィルタする。
WALK_STEPS = [1, 5, 7, 10, 15, 20]
LAYOUT_CODES = {"ワンルーム": "01", "1K": "02", "1DK": "03", "1LDK": "04", "2K": "05", "2DK": "06", "2LDK": "07"}


def yen(s: str) -> Optional[int]:
    """'15万円' / '1.5万円' / '8000円' -> 円。'-' は None"""
    m = re.match(r"([\d.]+)(万)?円", s.replace(",", ""))
    if not m:
        return None
    return int(round(float(m.group(1)) * (10000 if m.group(2) else 1)))


def line_stations(session: requests.Session, pref: str, line: str):
    """沿線ページから (ra, rn, [ek...]) を取得"""
    soup = fetch(session, f"{BASE}/chintai/{pref}/{LINES[line][0]}/")
    ra = soup.select_one("input[name=ra][value]:not([value=''])")["value"]
    rn = soup.select_one("input[name=rn][value]:not([value=''])")["value"]
    ek = [i["value"] for i in soup.select('input[name="ek"]')]
    return ra, rn, ek


# 一覧の画像カルーセルは alt に写真の種類が入る。間取り図・周辺施設・ラベルは「物件の写真」に数えない。
INTERIOR_ALTS = {"居室・リビング", "キッチン", "バス・シャワールーム", "トイレ", "収納", "洗面設備", "その他部屋・スペース", "玄関", "その他設備", "バルコニー"}
BUILDING_ALTS = {"建物外観", "セキュリティ", "その他共有部分", "エントランス", "ロビー", "眺望", "駐車場", "その他"}


def count_photos(card) -> Dict[str, int]:
    alts = [i.get("alt", "") for i in card.select(".cassette_carrousel-thumblist img")]
    n_in = sum(a in INTERIOR_ALTS for a in alts)
    return {"n_images": len(alts), "n_photos": n_in + sum(a in BUILDING_ALTS for a in alts), "n_interior": n_in}


def parse_rooms(soup: BeautifulSoup) -> Iterator[Dict]:
    for p in soup.select("div.property"):
        a = p.select_one("a.js-cassetLinkHref")
        if not a:
            continue
        texts = [clean(d.get_text(" ")) for d in p.find_all("div") if not d.find(["div", "table", "ul"])]
        rent = clean(p.select_one(".detailbox-property-point").get_text()) if p.select_one(".detailbox-property-point") else ""
        admin = next((t.split(" ", 1)[1] for t in texts if t.startswith("管理費 ")), "")
        layout = next((t for t in texts if re.fullmatch(r"ワンルーム|\d[SLDK+]+", t)), "")
        area = next((t for t in texts if re.fullmatch(r"[\d.]+m ?2?", t) or re.match(r"^[\d.]+m", t)), "")
        age_t = next((t for t in texts if re.fullmatch(r"築\d+年|新築|築不詳", t)), "")
        age = 0 if age_t == "新築" else (int(re.sub(r"\D", "", age_t)) if re.search(r"\d", age_t) else None)
        addr = next((clean(td.get_text()) for td in p.select("td.detailbox-property-col") if re.match(r"(東京都|神奈川県)", clean(td.get_text()))), "")
        access = [t for t in texts if re.search(r"/.+(駅|停) ?(歩\d+分|バス)", t)]
        rec = {
            "building": clean(a.get_text()),
            "rent_yen": yen(rent), "admin_yen": yen(admin), "rent": rent, "admin_fee": admin,
            "layout": layout, "area": area.replace(" 2", "2"),
            "age": age, "address": addr, "access_list": access,
            "url": BASE + a["href"].split("?")[0],
            **count_photos(p),
        }
        rec["total_yen"] = (rec["rent_yen"] or 0) + (rec["admin_yen"] or 0) if rec["rent_yen"] else None
        yield rec


def walk_on_lines(access: List[str], line_names) -> Optional[tuple]:
    """対象路線の駅のうち最短徒歩 (分, '路線/駅')。無ければ None"""
    best = None
    for t in access:
        if "バス" in t:
            continue
        m = re.match(r"(.+?)/(.+?)駅? 歩(\d+)分", t)
        if m and m.group(1) in line_names:
            w = int(m.group(3))
            if best is None or w < best[0]:
                best = (w, f"{m.group(1)}/{m.group(2)}")
    return best


def dedupe(rows: List[Dict]) -> List[Dict]:
    """同一の部屋を複数社が掲載しているため、(住所,面積,間取り,賃料) で1件にまとめる（最安の総額を採用）"""
    best: Dict[tuple, Dict] = {}
    for r in rows:
        k = (r["address"], r["area"], r["layout"], r["rent_yen"])
        r["n_listings"] = 1
        if k in best:
            n = best[k]["n_listings"] + 1
            if (r["total_yen"] or 10**9) < (best[k]["total_yen"] or 10**9):
                best[k] = r
            best[k]["n_listings"] = n
        else:
            best[k] = r
    return list(best.values())


def check_coverage(label, hits, got, pages, max_pages, log=print):
    """SUUMO が表示する該当件数 (hits) と、実際に集めた掲載数を比べる。同じ部屋の重複で、集まる数は hits より1〜2割少ないのが普通。
    大きく少ない・ページ上限で打ち切られた場合は、取りこぼし (空の応答や上限不足) を疑って止める。"""
    if hits and got < hits * 0.5:
        raise RuntimeError(f"{label}: 該当 {hits} 件に対し {got} 件しか集まっていません (空の応答で打ち切られた可能性)")
    if got and pages >= max_pages:
        raise RuntimeError(f"{label}: --max-pages={max_pages} で打ち切られました。上限を増やしてください")
    if hits and got < hits * 0.8:
        log(f"  WARNING: {label}: 該当 {hits} 件に対し {got} 件 ({got / hits:.0%})。重複を除いた数としてはやや少なめです")


def search_lines(session, lines, prefs, layout, max_rent_man, walk, max_age, delay, max_pages, log=print, min_photos=3):
    names = {LINES[l][1] for l in lines}
    wl = next((s for s in WALK_STEPS if s >= walk), 20)
    seen: Dict[str, Dict] = {}
    for pref in prefs:
        for line in lines:
            ra, rn, ek = line_stations(session, pref, line)
            ek_q = "".join(f"&ek={e}" for e in ek)
            log(f"[{PREFS[pref]} {LINES[line][1]}] stations={len(ek)}")
            before, hits_n = len(seen), 0
            for page in range(1, max_pages + 1):
                url = LINE_URL.format(ra=ra, rn=rn, ek=ek_q, rent=f"{max_rent_man:.1f}", walk=wl, md=LAYOUT_CODES[layout], page=page)
                soup = fetch(session, url)
                if page == 1:
                    log(f"  hits: {total_hits(soup)}")
                    hits_n = int(re.sub(r"\D", "", total_hits(soup)) or 0)
                got = list(parse_rooms(soup))
                if not got:
                    break
                for r in got:
                    seen.setdefault(r["url"], r)
                time.sleep(delay)
            log(f"  pages={page} unique so far={len(seen)}")
            check_coverage(f"{PREFS[pref]} {LINES[line][1]}", hits_n, len(seen) - before, page, max_pages, log)
    out = []
    few_photos = 0
    for r in seen.values():
        w = walk_on_lines(r["access_list"], names)
        # 間取り図しかない / 写真が極端に少ない掲載は除外 (同じ部屋でも写真の揃った別の掲載があれば、そちらが残る)
        if r["n_photos"] < min_photos or r["n_interior"] < 1:
            few_photos += 1
            continue
        if (r["layout"] == layout and r["rent_yen"] is not None and r["rent_yen"] <= max_rent_man * 10000
                and r["age"] is not None and r["age"] <= max_age and w and w[0] <= walk):
            r["walk_min"], r["station"] = w
            r["access"] = " / ".join(r["access_list"])
            out.append(r)
    log(f"写真が少ない掲載を除外: {few_photos} 件 (min_photos={min_photos})")
    out = dedupe(out)
    out.sort(key=lambda r: (r["total_yen"] or 0))
    return out, len(seen)


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
    ap.add_argument("--lines", nargs="*", choices=list(LINES), help="沿線指定モード (例: toyoko meguro)")
    ap.add_argument("--prefs", nargs="*", default=["tokyo", "kanagawa"], choices=list(PREFS))
    ap.add_argument("--layout", default="1LDK", choices=list(LAYOUT_CODES))
    ap.add_argument("--max-rent", type=float, default=18.0, help="家賃上限(万円)")
    ap.add_argument("--walk", type=int, default=10, help="徒歩上限(分)")
    ap.add_argument("--max-age", type=int, default=35, help="築年数上限")
    ap.add_argument("--max-pages", type=int, default=80)
    ap.add_argument("--min-photos", type=int, default=3, help="間取り図・周辺写真を除く写真の最低枚数 (0 で無効)")
    args = ap.parse_args()

    s = requests.Session()
    if args.lines:
        rows, total = search_lines(s, args.lines, args.prefs, args.layout, args.max_rent, args.walk,
                                   args.max_age, args.delay, args.max_pages, log=lambda m: print(m, file=sys.stderr), min_photos=args.min_photos)
        for r in rows[: args.detail]:
            r.update(parse_detail(fetch(s, r["url"])))
            time.sleep(args.delay)
        for r in rows:
            r.pop("access_list", None)
        keys = list({k: 0 for r in rows for k in r})
        with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(rows)
        print(f"fetched {total} unique rooms -> {len(rows)} match all filters -> {args.out}", file=sys.stderr)
        return 0
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
