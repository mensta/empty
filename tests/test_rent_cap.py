# -*- coding: utf-8 -*-
"""The rent cap can be applied to rent + management fee (default) or to rent only. SUUMO's own filter ignores the fee."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import candidates as cand
import search_sites as ss
import suumo_scraper as sc
import validate


def suumo_room(n, rent, admin):
    return {"url": f"https://suumo.jp/chintai/bc_{n}/", "building": f"b{n}", "layout": "1LDK", "rent_yen": rent, "admin_yen": admin,
            "total_yen": rent + (admin or 0), "age": 10, "access_list": ["東急目黒線/不動前駅 歩5分"], "n_photos": 5, "n_interior": 3,
            "area": "40m2", "address": "東京都品川区"}


class TestSuumoCap(unittest.TestCase):
    def search(self, include_admin):
        from bs4 import BeautifulSoup
        rooms = [suumo_room(1, 180000, 5000),    # 18.5 total: inside either way
                 suumo_room(2, 189000, 20000),   # 20.9 total: rent only passes, with fee it does not
                 suumo_room(3, 190000, 0),       # exactly 19.0: inside (<=)
                 suumo_room(4, 185000, None)]    # no fee listed: counts as 0 (rent differs from room 3, or dedupe would merge them)
        orig = (sc.fetch, sc.line_stations, sc.total_hits, sc.parse_rooms, sc.walk_on_lines)
        pages = iter([rooms, []])
        try:
            sc.line_stations = lambda *a: ("ra", "rn", ["1"])
            sc.total_hits = lambda soup: "4件"
            sc.fetch = lambda *a, **k: BeautifulSoup("", "html.parser")
            sc.parse_rooms = lambda soup: iter(next(pages))
            sc.walk_on_lines = lambda access, names: (5, "不動前")
            out, _ = sc.search_lines(None, ["meguro"], ["tokyo"], "1LDK", 19, 10, 35, 0, 3, log=lambda m: None, include_admin=include_admin)
        finally:
            sc.fetch, sc.line_stations, sc.total_hits, sc.parse_rooms, sc.walk_on_lines = orig
        return sorted(r["url"][-3:-1] for r in out)

    def test_with_admin_drops_rooms_over_the_cap(self):
        self.assertEqual(self.search(True), ["_1", "_3", "_4"])

    def test_rent_only_keeps_them(self):
        self.assertEqual(self.search(False), ["_1", "_2", "_3", "_4"])


class TestOtherSitesCap(unittest.TestCase):
    BASE = {"site": "CHINTAI", "address": "東京都目黒区A", "access": ["東急目黒線/「目黒」駅 徒歩5分"], "layout": "1LDK", "age": 10, "area_m2": 40.0}

    def rows(self):
        return [{**self.BASE, "url": "a", "rent_yen": 180000, "admin_yen": 5000},
                {**self.BASE, "url": "b", "rent_yen": 189000, "admin_yen": 20000},
                {**self.BASE, "url": "c", "rent_yen": 190000, "admin_yen": None}]

    def test_filter_rows(self):
        names = lambda **kw: sorted(r["url"] for r in ss.filter_rows(self.rows(), ["meguro"], "1LDK", 19, 10, 35, 28, **kw))
        self.assertEqual(names(include_admin=True), ["a", "c"])
        self.assertEqual(names(include_admin=False), ["a", "b", "c"])
        self.assertEqual(names(), ["a", "b", "c"])  # standalone callers keep the old meaning


class TestValidateAndConditions(unittest.TestCase):
    ROW = {"id": "a", "url": "https://x/a", "area": 40.0, "rent": 18.9, "admin": 2.0, "total": 20.9, "walk": 5, "age": 10,
           "structure": "鉄筋コン", "group": "RC", "photos": 5, "layout": "1LDK", "line": "目黒", "initial": 50.0, "initial_note": "",
           "floor": "3階", "note": "", "shiki": "15", "rei": "15", "building": "b", "station": "s"}
    ARGS = dict(max_rent=19, walk=10, max_age=35, min_area=28, min_photos=3)

    def test_validate_uses_total_when_asked(self):
        errs, _ = validate.validate([self.ROW], [], [], include_admin=True, **self.ARGS)
        self.assertTrue(any("家賃が条件外" in e and "管理費込み" in e for e in errs), errs)
        errs, _ = validate.validate([self.ROW], [], [], **self.ARGS)
        self.assertFalse(any("家賃が条件外" in e for e in errs), errs)

    def test_condition_text_says_what_is_applied(self):
        args = (["1LDK"], 19.0, ["toyoko"], ["tokyo"], 10, 35, 28, 3)
        text = lambda **kw: next(c["text"] for c in cand.make_conditions(*args, **kw) if c["key"] == "rent_max")
        self.assertEqual(text(include_admin=True), "19万円以下(管理費込み)")
        self.assertEqual(text(), "19万円以下")


if __name__ == "__main__":
    unittest.main()
