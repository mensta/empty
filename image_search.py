#!/usr/bin/env python3
"""Keyword image search over Bing (scraped) and Openverse (official API).

Standard library only. Examples:

    ./image_search.py "red panda"                      # list 10 results (both sources)
    ./image_search.py "red panda" -n 5 -s openverse    # CC-licensed images only
    ./image_search.py "red panda" -n 5 -d out/         # also download the images
    ./image_search.py "red panda" --json               # machine-readable output

Notes:
  * Bing results come from scraping the public HTML page (unofficial; may break
    when Bing changes its markup) and carry no license information. Check the
    source page before reusing an image.
  * Openverse results carry license / creator / attribution metadata.
"""
from __future__ import annotations

import argparse
import html
import json
import mimetypes
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
TIMEOUT = 30
MAX_DOWNLOAD_BYTES = 30 * 1024 * 1024


def _get(url: str, accept: str = "*/*") -> urllib.request.addinfourl:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    return urllib.request.urlopen(req, timeout=TIMEOUT)


# --------------------------------------------------------------------------- #
# Sources
# --------------------------------------------------------------------------- #
_BING_ITEM = re.compile(r'class="iusc"[^>]*\sm="([^"]+)"')


def search_bing(query: str, limit: int, safe: bool = True) -> list[dict]:
    """Scrape Bing Images. Pages are fetched with the `first` offset."""
    results: list[dict] = []
    seen: set[str] = set()
    offset = 0
    while len(results) < limit:
        params = {
            "q": query,
            "first": offset,
            "form": "HDRSC2",
            "adlt": "strict" if safe else "off",
        }
        url = "https://www.bing.com/images/search?" + urllib.parse.urlencode(params)
        page = _get(url, "text/html").read().decode("utf-8", "ignore")
        added = 0
        for m in _BING_ITEM.finditer(page):
            try:
                d = json.loads(html.unescape(m.group(1)))
            except json.JSONDecodeError:
                continue
            img = d.get("murl")
            if not img or img in seen:
                continue
            seen.add(img)
            added += 1
            results.append(
                {
                    "source": "bing",
                    "title": d.get("t") or "",
                    "url": img,
                    "thumbnail": d.get("turl"),
                    "page_url": d.get("purl"),
                    "license": None,
                    "creator": None,
                }
            )
        if added == 0:  # no more pages (or markup changed)
            break
        offset += added
    return results[:limit]


def search_openverse(query: str, limit: int, safe: bool = True) -> list[dict]:
    """Query the Openverse API (no key needed; anonymous page_size max is 20)."""
    results: list[dict] = []
    page = 1
    while len(results) < limit:
        params = {
            "q": query,
            "page": page,
            "page_size": min(20, max(limit - len(results), 1)),
            "mature": "false" if safe else "true",
        }
        url = "https://api.openverse.org/v1/images/?" + urllib.parse.urlencode(params)
        try:
            data = json.load(_get(url, "application/json"))
        except urllib.error.HTTPError as e:
            if e.code == 400:  # past the last page
                break
            raise
        items = data.get("results") or []
        if not items:
            break
        for r in items:
            lic = r.get("license") or ""
            if lic and r.get("license_version"):
                lic = f"{lic} {r['license_version']}".upper()
            results.append(
                {
                    "source": "openverse",
                    "title": r.get("title") or "",
                    "url": r.get("url"),
                    "thumbnail": r.get("thumbnail"),
                    "page_url": r.get("foreign_landing_url"),
                    "license": lic or None,
                    "creator": r.get("creator"),
                    "license_url": r.get("license_url"),
                    "attribution": r.get("attribution"),
                }
            )
        if page >= (data.get("page_count") or 1):
            break
        page += 1
    return [r for r in results if r["url"]][:limit]


SOURCES = {"bing": search_bing, "openverse": search_openverse}


def search(query: str, limit: int, sources: list[str], safe: bool = True) -> list[dict]:
    """Search each source and interleave results so both are represented.

    A source that fails is reported on stderr and skipped.
    """
    columns: list[list[dict]] = []
    for name in sources:
        try:
            found = SOURCES[name](query, limit, safe)
        except urllib.error.HTTPError as e:
            hint = ""
            if e.code == 429:
                wait = e.headers.get("Retry-After")
                hint = (" (rate limited" + (f", retry after {wait}s" if wait else "")
                        + "; anonymous Openverse access is throttled per IP)")
            print(f"[warn] {name} failed: HTTP {e.code}{hint}", file=sys.stderr)
            found = []
        except Exception as e:  # noqa: BLE001 - report and continue with other sources
            print(f"[warn] {name} failed: {type(e).__name__}: {e}", file=sys.stderr)
            found = []
        else:
            if not found:
                hint = ""
                if name == "bing" and not query.isascii():
                    hint = " (Bing does not process non-ASCII queries here; use -s openverse or an English query)"
                print(f"[warn] {name} returned no results{hint}", file=sys.stderr)
        columns.append(found)

    merged: list[dict] = []
    seen: set[str] = set()
    for i in range(max((len(c) for c in columns), default=0)):
        for col in columns:
            if i < len(col) and col[i]["url"] not in seen:
                seen.add(col[i]["url"])
                merged.append(col[i])
    return merged[:limit]


# --------------------------------------------------------------------------- #
# Download
# --------------------------------------------------------------------------- #
def _slug(text: str, maxlen: int = 40) -> str:
    s = re.sub(r"[^\w]+", "-", text, flags=re.UNICODE).strip("-").lower()
    return s[:maxlen] or "image"


def _ext_for(content_type: str, url: str) -> str:
    ct = content_type.split(";")[0].strip().lower()
    if ct == "image/jpeg":
        return ".jpg"
    ext = mimetypes.guess_extension(ct) if ct else None
    if ext:
        return ext
    tail = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower()
    return tail if re.fullmatch(r"\.[a-z0-9]{2,5}", tail) else ".img"


def download_one(item: dict, dest_dir: str, index: int) -> str | None:
    """Download item['url']; return the saved path, or None if it isn't a usable image."""
    try:
        with _get(item["url"], "image/*,*/*;q=0.5") as resp:
            ctype = resp.headers.get("Content-Type", "")
            if not ctype.lower().startswith("image/"):
                raise ValueError(f"not an image (Content-Type: {ctype or 'none'})")
            data = resp.read(MAX_DOWNLOAD_BYTES + 1)
            if len(data) > MAX_DOWNLOAD_BYTES:
                raise ValueError("file too large")
    except Exception as e:  # noqa: BLE001
        print(f"[skip] {item['url']}: {e}", file=sys.stderr)
        return None
    name = f"{index:02d}-{item['source']}-{_slug(item['title'])}{_ext_for(ctype, item['url'])}"
    path = os.path.join(dest_dir, name)
    with open(path, "wb") as f:
        f.write(data)
    item["file"] = path
    return path


def download_many(results: list[dict], limit: int, dest_dir: str) -> list[dict]:
    """Download until `limit` files are saved, falling through failed candidates."""
    os.makedirs(dest_dir, exist_ok=True)
    saved: list[dict] = []
    for item in results:
        if len(saved) >= limit:
            break
        if download_one(item, dest_dir, len(saved) + 1):
            saved.append(item)
    return saved


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Image search over Bing and Openverse.")
    p.add_argument("query", help="search keywords")
    p.add_argument("-n", "--num", type=int, default=10, help="number of results (default 10)")
    p.add_argument(
        "-s", "--source", choices=["bing", "openverse", "both"], default="both",
        help="which source to use (default both)",
    )
    p.add_argument("-d", "--download", metavar="DIR", help="download images into DIR")
    p.add_argument("--json", action="store_true", help="print results as JSON")
    p.add_argument("--unsafe", action="store_true", help="disable safe-search / mature filter")
    args = p.parse_args(argv)

    sources = ["bing", "openverse"] if args.source == "both" else [args.source]
    # When downloading, fetch extra candidates so broken links can be skipped.
    fetch_n = args.num * 2 if args.download else args.num
    results = search(args.query, fetch_n, sources, safe=not args.unsafe)

    if args.download:
        results = download_many(results, args.num, args.download)
        if results:
            meta = os.path.join(args.download, "results.json")
            with open(meta, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
    else:
        results = results[: args.num]

    if args.json:
        json.dump(results, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        for i, r in enumerate(results, 1):
            print(f"{i:>2}. [{r['source']}] {r['title'] or '(untitled)'}")
            print(f"    image: {r['url']}")
            if r.get("page_url"):
                print(f"    page : {r['page_url']}")
            if r.get("license"):
                print(f"    lic  : {r['license']}" + (f"  by {r['creator']}" if r.get("creator") else ""))
            if r.get("file"):
                print(f"    saved: {r['file']}")
    if not results:
        print("no results", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
