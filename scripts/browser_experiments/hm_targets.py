# Decide which HOME'S rooms need a detail page, from the list pages saved by hm_lists.mjs.
import glob, json, re, sys, collections as C
sys.path.insert(0, "/workspace/rental-search")
from bs4 import BeautifulSoup
import sites, search_sites as ss

rows, where = {}, {}
for f in sorted(glob.glob("pages/L_*_*.html"), key=lambda p: (re.search(r"L_(\w+)_", p).group(1), int(re.search(r"_(\d+)\.html", p).group(1)))):
    line, n = re.search(r"L_(\w+)_(\d+)\.html", f).groups()
    for r in sites.parse_homes(BeautifulSoup(open(f, encoding="utf-8"), "html.parser")):
        if r["url"] not in rows:
            rows[r["url"]] = r; where[r["url"]] = (line, int(n))
rows = list(rows.values())
print("list rows (unique):", len(rows), "| by layout:", dict(C.Counter(r["layout"] for r in rows)))
found = ss.filter_rows(rows, ["toyoko", "meguro"], ["1LDK", "2DK", "2LDK"], 19, 10, 35, 28, include_admin=True)
print("after the usual conditions (rent+admin <= 19, walk, age, area, layout):", len(found), dict(C.Counter(r["layout"] for r in found)))
cand = json.load(open("/workspace/rental-search/data/candidates.json"))
have = {(c["station"], round(c["area"], 1), c["rent"]) for c in cand}
cache = json.load(open("/workspace/rental-search/data/detail_cache.json"))
key = lambda r: (r["station"].split("/")[1], round(r["area_m2"], 1), round(r["rent_yen"] / 10000, 2))
targets = []
for r in found:
    if key(r) in have: continue
    if cache.get(r["url"], {}).get("structure"): continue
    line, n = where[r["url"]]
    targets.append({"url": r["url"], "line": line, "page": n, "building": r["building"], "layout": r["layout"]})
print("already in candidates (station/area/rent match):", sum(key(r) in have for r in found))
print("detail pages needed:", len(targets), dict(C.Counter((t["line"], t["layout"]) for t in targets)))
json.dump(targets, open("targets.json", "w"), ensure_ascii=False, indent=1)
json.dump(found, open("found.json", "w"), ensure_ascii=False, indent=1)
