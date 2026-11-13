# -*- coding: utf-8 -*-
"""Parsers for DOOR (door.ac) and Tokyu Housing Lease list pages (scripts/browser_experiments/door_parse.py).
The fixtures are cut down from real pages (2026-11-13)."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts", "browser_experiments"))

import door_parse as dp  # noqa: E402
import search_sites as ss  # noqa: E402

DOOR_LIST = """
<div class="building-box">
 <div class="building-box__head"><h2 class="heading"><a href="/buildings/b1">ラ・トゥール渋谷神南の賃貸物件情報</a></h2></div>
 <div class="building-box__body">
  <div class="building-box__summary-primary">
   <dl class="description-item"><dt><span>所在地</span></dt><dd>東京都渋谷区神南</dd></dl>
   <dl class="description-item"><dt><span>築年数</span></dt><dd>築8年</dd></dl>
   <dl class="description-item description-item--station"><dt><span>最寄駅</span></dt>
    <dd>東急東横線 代官山駅 徒歩9分<br/>ＪＲ山手線 渋谷駅 徒歩10分</dd></dl>
  </div>
  <table><tbody>
   <tr><td>14階</td><td><em>11.5</em>万円</td><td>なし</td><td>345万円
     /
    なし</td><td>1LDK</td><td>41.13㎡</td><td>fav</td>
     <td><a href="/buildings/b1/properties/p1?x=1" rel="nofollow">詳細を見る</a></td></tr>
   <tr><td>7階</td><td><em>9.9</em>万円</td><td>5,000円</td><td>なし / 9.9万円</td><td>2DK</td><td>45.0㎡</td><td>fav</td>
     <td><a href="/buildings/b1/properties/p2">詳細を見る</a></td></tr>
  </tbody></table>
 </div>
</div>
"""

DOOR_BUILDING = """
<dl><dt>所在地</dt><dd>東京都 大田区 田園調布</dd></dl>
<dl><dt>建階</dt><dd>2階建</dd></dl>
<dl><dt>築年月</dt><dd>1974年9月 / 築53年</dd></dl>
<dl><dt>建物構造</dt><dd>賃貸マンション/RC（鉄筋コンクリート）</dd></dl>
"""

DOOR_PROPERTY = """
<div class="properties__slideshow-image-inner"><img alt="Aの間取り写真" src="/assets/x.jpg"></div>
<div class="properties__slideshow-image-inner"><img alt="Aの外観写真" src="/assets/x.jpg"></div>
<div class="properties__slideshow-image-inner"><img alt="Aの居間写真" src="/assets/x.jpg"></div>
<div class="properties__slideshow-image-inner"><img alt="画像なし" src="/assets/x.jpg"></div>
<table><tr><th>家賃</th><th>敷金</th><th>礼金</th></tr></table>
<table><tr><th>敷金</th><td>27.2万円</td><th>礼金</th><td>なし</td></tr>
<tr><th>更新料</th><td>-</td><th>保証会社利用</th><td>必須</td></tr></table>
"""

TOKYU_LIST = """
<div class="rent_item">
 <div class="name_block"><h2><a href="/rent/8037571" title="x">ドゥーエ武蔵中原</a></h2></div>
 <div class="item_info"><div class="info"><table>
  <tr><th>物件種別</th><td colspan="3">マンション</td></tr>
  <tr><th>所在地</th><td colspan="3">神奈川県川崎市中原区下小田中3丁目18-9</td></tr>
  <tr><th>交通</th><td colspan="3">東急東横線/新丸子駅 徒歩12分</td></tr>
  <tr><th>築年月</th><td>2020年9月</td><th>構造</th><td>RC(鉄筋コンクリート)</td></tr>
 </table></div></div>
 <div class="item_rooms"><div class="item_room_table"><table class="check_table"><tbody>
  <tr><td><input type="checkbox"></td>
   <td class="tal"><div class="has_icon"><p><i>内覧可</i></p></div>105号室</td>
   <td>1LDK+S/<br/>50.29m²</td>
   <td><strong class="price">18.1万円</strong>/<br/>2万円</td>
   <td>なし /<br/>なし</td><td></td>
   <td><a href="/rent/8037571/131196"><img alt="x"></a></td></tr>
 </tbody></table></div></div>
</div>
<div class="rent_item">
 <div class="name_block"><h2><a href="/rent/9" title="x">店舗ビル</a></h2></div>
 <div class="info"><table><tr><th>物件種別</th><td colspan="3">店舗事務所</td></tr></table></div>
 <div class="item_room_table"><table><tbody><tr><td></td><td>1号室</td><td>1R/<br/>20m²</td><td>8万円/<br/>1万円</td><td>なし</td><td></td><td><a href="/rent/9/1">x</a></td></tr></tbody></table></div>
</div>
"""


class DoorListTest(unittest.TestCase):
    def setUp(self):
        self.rows = list(dp.parse_door_list(DOOR_LIST))

    def test_one_row_per_room_with_building_fields(self):
        self.assertEqual(len(self.rows), 2)
        r = self.rows[0]
        self.assertEqual((r["building"], r["address"], r["age"]), ("ラ・トゥール渋谷神南", "東京都渋谷区神南", 8))
        self.assertEqual((r["layout"], r["area_m2"], r["rent_yen"], r["admin_yen"], r["floor"]), ("1LDK", 41.13, 115000, 0, "14階"))

    def test_url_has_no_query_and_is_absolute(self):
        self.assertEqual(self.rows[0]["url"], "https://door.ac/buildings/b1/properties/p1")

    def test_deposit_and_key_money_are_split(self):
        self.assertEqual((self.rows[0]["shiki"], self.rows[0]["rei"]), ("345万円", "なし"))
        self.assertEqual((self.rows[1]["shiki"], self.rows[1]["rei"]), ("なし", "9.9万円"))

    def test_admin_fee_in_yen(self):
        self.assertEqual(self.rows[1]["admin_yen"], 5000)

    def test_access_is_in_the_shape_best_walk_reads(self):
        self.assertEqual(self.rows[0]["access"], ["東急東横線/代官山駅 徒歩9分", "JR山手線/渋谷駅 徒歩10分"])
        self.assertEqual(ss.best_walk(self.rows[0]["access"], ["toyoko"]), (9, "東急東横線/代官山"))

    def test_rows_work_with_filter_rows(self):
        out = ss.filter_rows(self.rows, ["toyoko"], ["1LDK", "2DK"], 19.0, 10, 35, 28.0, include_admin=True)
        self.assertEqual(len(out), 2)  # both are within 19man incl. admin, 10 min, 35 years, over 28 m2


class DoorBuildingTest(unittest.TestCase):
    def test_structure_is_read_after_the_slash(self):
        d = dp.parse_door_building(DOOR_BUILDING)
        self.assertEqual(d["structure"], "RC（鉄筋コンクリート）")
        self.assertEqual(d["floors"], "2階建")


class DoorPropertyTest(unittest.TestCase):
    def test_photos_are_counted_by_alt_text_even_when_src_is_a_placeholder(self):
        d = dp.parse_door_property(DOOR_PROPERTY)
        self.assertEqual((d["n_photos"], d["n_interior"], d["has_plan"]), (3, 1, True))  # the "no image" slot is not a photo

    def test_header_row_is_not_read_as_a_key_value_pair(self):
        d = dp.parse_door_property(DOOR_PROPERTY)
        self.assertEqual((d["敷金"], d["礼金"], d["更新料"], d["保証会社利用"]), ("27.2万円", "なし", "-", "必須"))


class TokyuListTest(unittest.TestCase):
    def test_room_row_and_building_fields(self):
        rows = list(dp.parse_tokyu_list(TOKYU_LIST))
        self.assertEqual(len(rows), 1)  # the shop/office building is skipped
        r = rows[0]
        self.assertEqual((r["building"], r["structure"], r["layout"], r["area_m2"]), ("ドゥーエ武蔵中原", "RC(鉄筋コンクリート)", "1LDK+S", 50.29))
        self.assertEqual((r["rent_yen"], r["admin_yen"], r["floor"]), (181000, 20000, "105号室"))
        self.assertEqual(r["url"], "https://rent.tokyu-housing-lease.co.jp/rent/8037571/131196")
        self.assertEqual(r["access"], ["東急東横線/新丸子駅 徒歩12分"])


if __name__ == "__main__":
    unittest.main()
