# -*- coding: utf-8 -*-
"""Search X (Twitter) without authentication through the FxTwitter API and save compact JSON.

    python3 xsearch.py --out x_raw.json "query one" "query two"
    python3 xsearch.py --out x_raw.json --min-likes 2 --show 25 "HOME'S スクレイピング"

Each query is run as feed=top and feed=latest, de-duplicated by post id, sorted by likes.
Be polite: a pause of >= 1.5 s between calls (--sleep). Public data only, no login.
"""
import argparse
import json
import re
import time
import urllib.parse
import urllib.request

API = "https://api.fxtwitter.com/2/search"


def search(q, feed="top", count=40):
    url = API + "?" + urllib.parse.urlencode({"q": q, "feed": feed, "count": min(count, 100)})
    req = urllib.request.Request(url, headers={"User-Agent": "research-script"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("results", [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("queries", nargs="+")
    ap.add_argument("--out", default="x_raw.json")
    ap.add_argument("--feeds", nargs="+", default=["top", "latest"], choices=["top", "latest", "media"])
    ap.add_argument("--count", type=int, default=40)
    ap.add_argument("--sleep", type=float, default=1.5)
    ap.add_argument("--min-likes", type=int, default=0)
    ap.add_argument("--keep", help="regex; only print posts whose text matches")
    ap.add_argument("--show", type=int, default=0, help="print the top N posts")
    a = ap.parse_args()
    seen = {}
    for q in a.queries:
        for feed in a.feeds:
            try:
                results = search(q, feed, a.count)
            except Exception as e:  # keep going: one failing query should not lose the others
                print(f"ERR {q!r} {feed}: {e}")
                continue
            for s in results:
                if s.get("id") in seen:
                    continue
                seen[s["id"]] = {"url": s["url"], "date": s["created_at"], "likes": s.get("likes") or 0,
                                 "author": s["author"]["screen_name"], "text": s["text"].replace("\n", " ")}
            time.sleep(a.sleep)
    out = sorted(seen.values(), key=lambda x: -x["likes"])
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(out)} posts -> {a.out}")
    rx = re.compile(a.keep) if a.keep else None
    shown = 0
    for x in out:
        if x["likes"] < a.min_likes or (rx and not rx.search(x["text"])):
            continue
        if shown >= a.show:
            break
        shown += 1
        print(f'[{x["likes"]}] {x["date"][4:16]} @{x["author"]} {x["url"]}\n  {x["text"][:240]}\n')


if __name__ == "__main__":
    main()
