# -*- coding: utf-8 -*-
"""Known-listing state for incremental crawling of the other portals (HOME'S / at home / CHINTAI).

Why: HOME'S answers with HTTP 202 (WAF challenge) more often the more pages we request. Fetching only the
newest pages (sorted newest-first, stop at the first page whose listings are all known) cuts the request count.
Because an incremental run cannot tell that a listing disappeared, a full crawl is forced every FULL_EVERY_DAYS.

State file (data/known_ids.json):
  {"version": 1,
   "listings": {"<site>|<url>": {"first_seen": "YYYY-MM-DD", "last_seen": "...", "gone": null | "YYYY-MM-DD"}},
   "last_full": {"<site>": "YYYY-MM-DD"}}

Rules (taken from how other people run listing monitors, see LESSONS.md):
- The first run only records a baseline: nothing is reported as new.
- A run that reports more than MAX_NEW new listings is flagged as suspicious (a parser or site change is likelier than
  a real burst), so callers should not notify on it.
- A site that failed to fetch never marks its listings as gone.
"""
import datetime

VERSION = 1
FULL_EVERY_DAYS = 7
MAX_NEW = 10

# Sort-newest-first query parameter per site. Each was confirmed on the live site by checking which <option>
# of the page's sort <select> became selected (2026-11-12). Do not guess these: CHINTAI sort=2 is "cheapest first".
SORT_NEW = {
    "HOME'S": ("cond[sortby]", "newdate"),
    "at home": ("sort", "33"),
    "CHINTAI": ("o", "7"),
}


def empty_state():
    return {"version": VERSION, "listings": {}, "last_full": {}}


def normalize(state):
    """A missing or foreign-version file starts over as a baseline (safe: nothing is reported as new)."""
    if not isinstance(state, dict) or state.get("version") != VERSION:
        return empty_state()
    state.setdefault("listings", {})
    state.setdefault("last_full", {})
    return state


def key(site, url):
    return f"{site}|{url}"


def plan_incremental(state, prev_rows, site_names, today, full_every=FULL_EVERY_DAYS, force_full=False):
    """Return {site: set(known urls)} for the sites that may be crawled incrementally.
    A site is crawled in full when it has no previous rows, was never fully crawled, or the last full crawl is old."""
    out = {}
    if force_full:
        return out
    for site in site_names:
        last = state["last_full"].get(site)
        known = {r["url"] for r in prev_rows if r.get("site") == site}
        if not last or not known:
            continue
        if (today - datetime.date.fromisoformat(last)).days >= full_every:
            continue
        out[site] = known
    return out


def merge_rows(prev_rows, fresh_rows, incremental_sites, failed=()):
    """fresh rows win; previous rows of incrementally crawled sites are kept (an incremental crawl only sees the
    newest pages). A site that failed is dropped entirely, like in a full crawl, so stale rooms are never shown."""
    fresh_keys = {(r["site"], r["url"]) for r in fresh_rows}
    kept = [r for r in prev_rows
            if r["site"] in incremental_sites and r["site"] not in failed and (r["site"], r["url"]) not in fresh_keys]
    return list(fresh_rows) + kept


class Diff:
    def __init__(self):
        self.new, self.gone, self.returned = [], [], []
        self.baseline = False
        self.suspicious = False

    def summary(self):
        if self.baseline:
            return "初回のため基準として記録 (新着は数えない)"
        flag = " ※新着が多すぎる (取得の異常かもしれない)" if self.suspicious else ""
        return f"新着 {len(self.new)} / 掲載終了 {len(self.gone)} / 再掲載 {len(self.returned)}{flag}"


def update(state, rows, today, ok_sites, full_sites=(), max_new=MAX_NEW):
    """Record this run. rows: every listing (dicts with site/url) seen from the sites in ok_sites.
    full_sites: sites crawled in full this run (only these can detect disappeared listings).
    Mutates and returns (state, Diff)."""
    t = today.isoformat()
    listings, diff = state["listings"], Diff()
    diff.baseline = not listings
    seen = set()
    for r in rows:
        if r["site"] not in ok_sites:
            continue
        k = key(r["site"], r["url"])
        seen.add(k)
        e = listings.get(k)
        if e is None:
            listings[k] = {"first_seen": t, "last_seen": t, "gone": None}
            if not diff.baseline:
                diff.new.append(k)
        else:
            if e.get("gone"):
                diff.returned.append(k)
            e["last_seen"], e["gone"] = t, None
    for k, e in listings.items():
        site = k.split("|", 1)[0]
        if site in full_sites and site in ok_sites and k not in seen and not e.get("gone"):
            e["gone"] = t
            diff.gone.append(k)
    for site in full_sites:
        if site in ok_sites:
            state["last_full"][site] = t
    diff.suspicious = len(diff.new) > max_new
    return state, diff


def lifetimes(state):
    """Days each vanished listing stayed up (first_seen -> gone). A rough popularity / decoy-ad signal.
    The resolution is the run interval, so treat it as an upper bound."""
    out = []
    for k, e in state["listings"].items():
        if e.get("gone"):
            days = (datetime.date.fromisoformat(e["gone"]) - datetime.date.fromisoformat(e["first_seen"])).days
            out.append((k, days))
    return out
