# -*- coding: utf-8 -*-
"""DOOR賃貸の取り込み (others.door_detail)、サイト間の同一部屋の統合、既存候補との重複除去"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import candidates as cand  # noqa: E402
import others  # noqa: E402
import adopt_browser_rooms as adopt  # noqa: E402


def door(**kw):
    r = {"site": "DOOR", "building": "テスト荘", "address": "東京都目黒区碑文谷", "layout": "1LDK", "area_m2": 35.0,
         "floor": "4階", "floors": "5階建（地下1階）", "rent_yen": 150000, "admin_yen": 5000, "age": 10, "walk_min": 5,
         "station": "東急東横線/学芸大学", "url": "https://door.ac/buildings/b/properties/p1", "structure": "RC（鉄筋コンクリート）",
         "detail": {"n_photos": 10, "n_interior": 5, "敷金": "なし", "礼金": "15万円", "入居・引渡期間": "'26年11月中旬"}}
    r.update(kw)
    return r


def homes(**kw):
    r = {"site": "HOME'S", "building": "テスト荘", "address": "東京都目黒区碑文谷2丁目1-1", "layout": "1LDK", "area_m2": 35.0,
         "rent_yen": 150000, "admin_yen": 5000, "age": 10, "walk_min": 5, "station": "東急東横線/学芸大学",
         "url": "https://www.homes.co.jp/chintai/room/abc/"}
    r.update(kw)
    return r


class DoorTest(unittest.TestCase):
    def test_door_detail(self):
        d = others.door_detail(door())
        self.assertEqual(d["floor"], "4階/5階建")
        self.assertEqual(d["shiki_rei"], "-/15万円")
        self.assertEqual(d["move_in"], "26年11月中旬")
        self.assertTrue(d["fees_unknown"])
        self.assertEqual((d["n_photos"], d["n_interior"]), (10, 5))

    def _build(self, rows, tmp):
        cache = {r["url"]: others.door_detail(door()) for r in rows if r["site"] == "DOOR"}
        cache["https://www.homes.co.jp/chintai/room/abc/"] = {**others.door_detail(door()), "floor": "4階/5階建"}
        path = os.path.join(tmp, "c.json")
        cand.save_json(path, cache)
        return others.build_other_rows(rows, set(), path, log=lambda *_: None)

    def test_row_and_photo_rule(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            good = door()
            few = door(url="https://door.ac/buildings/b2/properties/p2", area_m2=40.0,
                       detail={"n_photos": 2, "n_interior": 1})
            noint = door(url="https://door.ac/buildings/b3/properties/p3", area_m2=41.0,
                         detail={"n_photos": 6, "n_interior": 0})
            rows = [good, few, noint]
            cache = {r["url"]: others.door_detail(r) for r in rows}
            path = os.path.join(tmp, "c.json")
            cand.save_json(path, cache)
            out, _, _ = others.build_other_rows(rows, set(), path, log=lambda *_: None)
        self.assertEqual([r["id"] for r in out], ["dr_p1"])
        r = out[0]
        self.assertEqual((r["site"], r["rent"], r["admin"], r["total"], r["group"]), ("DOOR", 15.0, 0.5, 15.5, "RC"))

    def test_same_room_across_sites_is_one(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out, _, present = self._build([homes(), door()], tmp)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["site"], "HOME'S")
        self.assertEqual(out[0]["also"], "DOOR")

    def test_same_room_when_address_differs(self):
        # 住所の粒度が違って room_key が合わなくても、面積・家賃+管理費・間取りが同じなら1室
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out, _, _ = self._build([homes(address="東京都世田谷区"), door()], tmp)
        self.assertEqual(len(out), 1)

    def test_same_site_twins_are_kept(self):
        groups = {("a", 35.0, 1): [homes()], ("b", 35.0, 2): [homes(url="x")]}
        self.assertEqual(len(others.merge_across_sites(groups)), 2)

    def test_drop_existing(self):
        have = [{"station": "学芸大学", "area": 35.0, "layout": "1LDK", "total": 15.5}]
        new = [{"station": "学芸大学", "area": 35.0, "layout": "1LDK", "total": 15.5},
               {"station": "学芸大学", "area": 36.0, "layout": "1LDK", "total": 15.5}]
        keep, dup = adopt.drop_existing(new, have)
        self.assertEqual((len(keep), len(dup)), (1, 1))


if __name__ == "__main__":
    unittest.main()
