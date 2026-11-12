# -*- coding: utf-8 -*-
"""Incremental crawl of the other portals: known-listing state, newest-first URLs, early stop."""
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import known_ids as kn
import search_sites as ss

D1, D2, D9 = datetime.date(2026, 11, 1), datetime.date(2026, 11, 2), datetime.date(2026, 11, 9)


def row(site, n):
    return {"site": site, "url": f"https://{site.replace(' ', '')}.example/{n}/"}


class TestSortParams(unittest.TestCase):
    """Each value was confirmed on the live site (the sort <select> option that became selected)."""

    def test_values_are_the_verified_ones(self):
        self.assertEqual(kn.SORT_NEW["HOME'S"], ("cond[sortby]", "newdate"))
        self.assertEqual(kn.SORT_NEW["at home"], ("sort", "33"))
        # A secondhand note said CHINTAI sort=2; on the live site that is "cheapest first". Newest-first is o=7.
        self.assertEqual(kn.SORT_NEW["CHINTAI"], ("o", "7"))

    def test_page_url_adds_sort_only_when_asked(self):
        _, p = ss.page_url("HOME'S", "https://h/", 2, 18, 7, sort_new=True)
        self.assertEqual((p["cond[sortby]"], p["page"]), ("newdate", "2"))
        self.assertNotIn("cond[sortby]", ss.page_url("HOME'S", "https://h/", 1, 18, 7)[1])
        self.assertEqual(ss.page_url("at home", "https://a/", 2, 18, 7, sort_new=True), ("https://a/page2/", {"sort": "33"}))
        self.assertEqual(ss.page_url("CHINTAI", "https://c/", 1, 18, 7, sort_new=True), ("https://c/", {"o": "7"}))
        self.assertEqual(ss.page_url("CHINTAI", "https://c/", 1, 18, 7), ("https://c/", None))


class TestUpdate(unittest.TestCase):
    def test_first_run_is_a_baseline(self):
        st, d = kn.update(kn.empty_state(), [row("CHINTAI", i) for i in range(30)], D1, {"CHINTAI"}, {"CHINTAI"})
        self.assertTrue(d.baseline)
        self.assertEqual(d.new, [])
        self.assertFalse(d.suspicious)  # 30 listings on the first run is not a burst of new ones
        self.assertEqual(st["last_full"], {"CHINTAI": "2026-11-01"})

    def test_new_gone_and_returned(self):
        st, _ = kn.update(kn.empty_state(), [row("CHINTAI", 1), row("CHINTAI", 2)], D1, {"CHINTAI"}, {"CHINTAI"})
        st, d = kn.update(st, [row("CHINTAI", 2), row("CHINTAI", 3)], D2, {"CHINTAI"}, {"CHINTAI"})
        self.assertEqual([k.split("|")[1][-3:] for k in d.new], ["/3/"])
        self.assertEqual(len(d.gone), 1)
        st, d = kn.update(st, [row("CHINTAI", 1)], D9, {"CHINTAI"}, {"CHINTAI"})
        self.assertEqual(len(d.returned), 1)

    def test_too_many_new_is_suspicious(self):
        st, _ = kn.update(kn.empty_state(), [row("CHINTAI", 0)], D1, {"CHINTAI"}, {"CHINTAI"})
        _, d = kn.update(st, [row("CHINTAI", i) for i in range(1, 15)], D2, {"CHINTAI"}, {"CHINTAI"})
        self.assertEqual(len(d.new), 14)
        self.assertTrue(d.suspicious)

    def test_failed_site_never_marks_listings_gone(self):
        st, _ = kn.update(kn.empty_state(), [row("HOME'S", 1), row("CHINTAI", 1)], D1, {"HOME'S", "CHINTAI"}, {"HOME'S", "CHINTAI"})
        # HOME'S failed (WAF challenge): only CHINTAI was fetched
        st, d = kn.update(st, [row("CHINTAI", 1)], D2, {"CHINTAI"}, {"CHINTAI"})
        self.assertEqual(d.gone, [])
        self.assertIsNone(st["listings"][kn.key("HOME'S", row("HOME'S", 1)["url"])]["gone"])
        self.assertEqual(st["last_full"]["HOME'S"], "2026-11-01")  # a failed run does not refresh the full-crawl date

    def test_incremental_run_cannot_detect_gone(self):
        st, _ = kn.update(kn.empty_state(), [row("HOME'S", 1), row("HOME'S", 2)], D1, {"HOME'S"}, {"HOME'S"})
        st, d = kn.update(st, [row("HOME'S", 3)], D2, {"HOME'S"}, full_sites=set())
        self.assertEqual(d.gone, [])
        self.assertEqual(len(d.new), 1)
        self.assertEqual(st["last_full"]["HOME'S"], "2026-11-01")

    def test_lifetimes(self):
        st, _ = kn.update(kn.empty_state(), [row("CHINTAI", 1)], D1, {"CHINTAI"}, {"CHINTAI"})
        st, _ = kn.update(st, [], D9, {"CHINTAI"}, {"CHINTAI"})
        self.assertEqual([days for _, days in kn.lifetimes(st)], [8])

    def test_foreign_state_restarts_as_baseline(self):
        self.assertEqual(kn.normalize({"version": 99, "listings": {"x": {}}}), kn.empty_state())
        self.assertEqual(kn.normalize(None), kn.empty_state())


class TestPlan(unittest.TestCase):
    def setUp(self):
        self.prev = [row("HOME'S", 1), row("CHINTAI", 1)]
        self.state = kn.empty_state()
        self.state["last_full"] = {"HOME'S": "2026-11-05", "CHINTAI": "2026-10-20"}

    def test_recent_full_crawl_goes_incremental_old_one_does_not(self):
        plan = kn.plan_incremental(self.state, self.prev, ["HOME'S", "CHINTAI", "at home"], D9)
        self.assertEqual(set(plan), {"HOME'S"})  # CHINTAI: last full crawl too old; at home: never crawled
        self.assertEqual(plan["HOME'S"], {self.prev[0]["url"]})

    def test_force_full(self):
        self.assertEqual(kn.plan_incremental(self.state, self.prev, ["HOME'S"], D9, force_full=True), {})

    def test_no_previous_rows_means_full(self):
        self.assertEqual(kn.plan_incremental(self.state, [], ["HOME'S"], D9), {})


class TestMerge(unittest.TestCase):
    def test_keeps_previous_rows_of_incremental_sites_only(self):
        prev = [row("HOME'S", 1), row("HOME'S", 2), row("CHINTAI", 1)]
        fresh = [{**row("HOME'S", 2), "rent_yen": 1}, row("HOME'S", 3), row("CHINTAI", 5)]
        got = kn.merge_rows(prev, fresh, {"HOME'S"})
        urls = sorted((r["site"], r["url"][-3:]) for r in got)
        # CHINTAI was a full crawl: its old room 1 is gone. HOME'S room 1 is kept, room 2 is the fresh copy.
        self.assertEqual(urls, [("CHINTAI", "/5/"), ("HOME'S", "/1/"), ("HOME'S", "/2/"), ("HOME'S", "/3/")])
        self.assertEqual([r.get("rent_yen") for r in got if r["url"].endswith("/2/") and r["site"] == "HOME'S"], [1])

    def test_failed_site_is_dropped_even_if_incremental(self):
        prev = [row("HOME'S", 1)]
        self.assertEqual(kn.merge_rows(prev, [], {"HOME'S"}, failed=["HOME'S"]), [])


class TestCollectIncremental(unittest.TestCase):
    """Early stop: with newest-first pages, a page whose listings are all known ends the crawl."""

    def run_collect(self, pages, incremental):
        calls = []
        orig_fetch, orig_targets = ss.sites.fetch, ss.TARGETS

        def fake_fetch(ses, url, params=None):
            calls.append((url, params))
            n = int((params or {}).get("page", 1))
            return n

        def parser(page):  # page number -> listings on that page
            return [{"site": "HOME'S", "url": u} for u in pages.get(page, [])]

        try:
            ss.sites.fetch = fake_fetch
            ss.TARGETS = {"HOME'S": ("https://www.homes.co.jp/{line}/", {"toyoko": "t"}, parser)}
            rows, failed = ss.collect(["toyoko"], 18, 7, max_pages=10, delay=0, log=lambda m: None, incremental=incremental)
        finally:
            ss.sites.fetch, ss.TARGETS = orig_fetch, orig_targets
        return rows, failed, calls

    PAGES = {1: ["a", "b"], 2: ["c", "d"], 3: ["e", "f"], 4: []}

    def test_stops_at_first_fully_known_page(self):
        rows, _, calls = self.run_collect(self.PAGES, {"HOME'S": {"c", "d", "e", "f"}})
        self.assertEqual(len(calls), 2)  # page 1 has new rooms, page 2 is all known -> stop, page 3 is never requested
        self.assertEqual({r["url"] for r in rows}, {"a", "b", "c", "d"})
        self.assertTrue(all(p.get("cond[sortby]") == "newdate" for _, p in calls))

    def test_goes_on_while_pages_have_unknown_rooms(self):
        rows, _, calls = self.run_collect(self.PAGES, {"HOME'S": {"a"}})
        self.assertEqual(len(calls), 4)  # pages 1-3 each contain unknown rooms; page 4 is empty and ends the crawl
        self.assertEqual({r["url"] for r in rows}, {"a", "b", "c", "d", "e", "f"})

    def test_full_mode_does_not_sort_or_stop_early(self):
        rows, _, calls = self.run_collect(self.PAGES, None)
        self.assertEqual(len(calls), 4)
        self.assertTrue(all("cond[sortby]" not in p for _, p in calls))
        self.assertEqual(len(rows), 6)


if __name__ == "__main__":
    unittest.main()
