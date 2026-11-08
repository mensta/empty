# -*- coding: utf-8 -*-
"""実際に起きた不具合を再現するテスト。実行: python -m unittest discover -s tests -v  (リポジトリの直下で)"""
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from PIL import Image

import candidates as cand
import others
import plans
import sites
import suumo_scraper as sc
import validate
import web


class FakeResp:
    def __init__(self, status, body):
        self.status_code, self.content = status, body

    def raise_for_status(self):
        pass


class FakeCookies:
    def __init__(self):
        self.cleared = 0

    def clear(self):
        self.cleared += 1


class FakeSession:
    def __init__(self, responses):
        self.responses, self.calls, self.cookies = list(responses), 0, FakeCookies()

    def get(self, *a, **k):
        self.calls += 1
        return self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]


NOWAIT = lambda: web.Pacer(clock=lambda: 0.0, sleep=lambda _: None)  # アクセス間隔の待ちを無効にしたペーサー
FULL = b"<html><body>" + b"x" * 100 + b"</body></html>"


class TestFetch(unittest.TestCase):
    """サーバーは 202 や空の 200、途中で切れた本文を返すことがある (目黒線が0件・物件が写真0枚になった原因)"""

    def test_retries_until_complete(self):
        waits = []
        s = FakeSession([FakeResp(202, b""), FakeResp(200, b""), FakeResp(200, b"<html><body>cut"), FakeResp(200, FULL)])
        soup = web.fetch_soup(s, "http://x", sleep=waits.append, pacer=NOWAIT())
        self.assertEqual(s.calls, 4)
        self.assertEqual(waits, [3, 6, 12])  # 待ち時間は段階的に延びる
        self.assertIsNotNone(soup.body)

    def test_cookies_are_dropped_before_every_attempt(self):  # Cookie を持ち越すと 202 が続く
        s = FakeSession([FakeResp(202, b""), FakeResp(200, FULL)])
        web.fetch_soup(s, "http://x", sleep=lambda _: None, pacer=NOWAIT())
        self.assertEqual(s.cookies.cleared, 2)

    def test_gives_up_with_error_instead_of_returning_empty(self):
        s = FakeSession([FakeResp(202, b"")])
        with self.assertRaises(RuntimeError):
            web.fetch_soup(s, "http://x", retries=3, sleep=lambda _: None, pacer=NOWAIT())
        self.assertEqual(s.calls, 3)


class TestPacer(unittest.TestCase):
    def test_gap_grows_after_failures_and_is_capped(self):
        slept, now = [], [0.0]
        pacer = web.Pacer(clock=lambda: now[0], sleep=slept.append)
        pacer.wait("h")                 # 最初は待たない
        self.assertEqual(slept, [])
        for _ in range(5):
            pacer.penalize("h")
        self.assertEqual(pacer.gap["h"], 10.0)   # 上限
        pacer.wait("h")                 # 直後に次のアクセス -> 間隔の分だけ待つ
        self.assertEqual(slept, [10.0])
        self.assertEqual(pacer.gap.get("other", 0), 0)   # 他のサイトには影響しない

    def test_slow_sites_start_with_a_gap(self):
        self.assertGreaterEqual(web.PACER.gap["www.homes.co.jp"], 5)


class TestParsing(unittest.TestCase):
    def test_age_formats(self):  # HOME'S は「2年 / 5階建」と「築」が付かない (築年数なし扱いで大量に除外されていた)
        for text, want in [("2年 / 5階建", 2), ("築5年4ヶ月", 5), ("1990年07月（築36年）", 36), ("新築 / 3階建", 0),
                           ("2026年3月", 0), ("1年未満", 0), ("35年 / 4階建", 35), ("築不詳", None)]:
            self.assertEqual(sites._age(text), want, text)

    def test_structure_names(self):
        for text, want in [("RC(鉄筋コンクリート)", "鉄筋コン"), ("ＲＣ", "鉄筋コン"), ("鉄筋コンクリート造", "鉄筋コン"),
                           ("SRC(鉄骨鉄筋コンクリート)", "鉄筋コン"), ("鉄筋コン", "鉄筋コン"), ("軽量鉄骨", "軽量鉄骨"),
                           ("鉄骨造", "鉄骨"), ("木造", "木造"), ("ALC", "気泡コン"), ("気泡コン", "気泡コン")]:
            self.assertEqual(cand.norm_structure(text), want, text)

    def test_same_room_key_across_sites(self):  # サイトごとに住所の書き方が違う
        k = others.room_key("東京都目黒区鷹番１", 47.33, 143000)
        self.assertEqual(k, others.room_key("目黒区鷹番1丁目", 47.331, 143000))
        self.assertEqual(k, others.room_key("東京都目黒区鷹番1丁目", 47.33, 143000))
        self.assertNotEqual(k, others.room_key("東京都目黒区鷹番1丁目", 47.33, 144000))


class TestInitialCost(unittest.TestCase):
    """手計算した物件と突き合わせる"""

    def test_cases(self):
        d1 = {"shiki_rei": "14.2万円 / 14.2万円", "options": "敷金1ヶ月、仲手0.55ヶ月、礼金1ヶ月", "hosho": "保証会社利用必 実費", "sonpo": "要",
              "biko": "保証委託料（賃料総額に対し、初回額50％、月額2％）。 消火剤・防災グッズ代(初期)50270円。 鍵交換代(初期)45000円。 消毒(抗菌費)(初期)25300円。 入居者サポート費用(初期)22000円。"}
        self.assertEqual(cand.estimate_initial(d1, 14.2, 0.3), (57.7, ""))  # 保証料は備考から読む
        d2 = {"shiki_rei": "- / 14万円", "options": "敷金不要", "biko": "", "sonpo": "",
              "hosho": "オリコフォレントインシュア利用必 初回保証料：請求月額の１ヶ月分（最低保証料２万円）継続保証料１万円／年"}
        self.assertEqual(cand.estimate_initial(d2, 14.0, 0.5), (43.9, "仲手は1.1ヶ月と仮定"))
        d3 = {"shiki_rei": "15.3万円 / 30.6万円", "options": "", "biko": "", "sonpo": "",
              "hosho": "保証会社利用可 初回保証委託料：６０％ （最低保証委託料：３０，０００円）、事務手数料：毎月家賃の１．８％"}
        self.assertEqual(cand.estimate_initial(d3, 15.3, 0.0), (71.9, "仲手は1.1ヶ月と仮定"))
        d4 = {"shiki_rei": "15.4万円 / 15.4万円", "options": "仲手0.55ヶ月", "biko": "", "sonpo": "", "hosho": "保証会社利用必 初回保証料：総賃料50％ 月額保証料：総賃料2％"}
        self.assertEqual(cand.estimate_initial(d4, 15.4, 0.6), (47.3, ""))

    def test_unknown_guarantee_is_flagged(self):
        d = {"shiki_rei": "1ヶ月/1ヶ月", "options": "", "biko": "", "hosho": "", "sonpo": ""}
        self.assertIn("保証料は含まず", cand.estimate_initial(d, 15.0, 0.5)[1])


def _png_like(arr):
    out = io.BytesIO()
    Image.fromarray(arr.astype("uint8")).save(out, "WEBP")
    return out.getvalue()


class TestPlanImages(unittest.TestCase):
    """掲載元が「間取り図」の欄に写真を入れていることがある。画素数では見分けられない (SUUMO が約800pxにそろえるため)"""

    def test_plan_vs_photo(self):
        plan = np.full((300, 400, 3), 255)
        plan[100:105, 50:350] = 0           # 白地に黒い線
        plan[150:250, 60:180] = (255, 230, 150)  # 色付きの部屋
        rng = np.random.default_rng(0)
        photo = np.clip(np.linspace(40, 200, 400)[None, :, None] + rng.normal(0, 9, (300, 400, 3)), 0, 255)  # 白が無く階調が連続
        self.assertFalse(plans.looks_like_photo(_png_like(plan)))
        self.assertTrue(plans.looks_like_photo(_png_like(photo)))


class TestSearchGuards(unittest.TestCase):
    def test_coverage_check(self):
        sc.check_coverage("x", 891, 842, 31, 130)                    # 重複分の差は正常
        with self.assertRaises(RuntimeError):
            sc.check_coverage("x", 891, 100, 5, 130)                 # 大きく足りない = 空の応答で打ち切られた疑い
        with self.assertRaises(RuntimeError):
            sc.check_coverage("x", 891, 800, 130, 130)               # ページ上限で打ち切られた

    def test_dedupe_keeps_cheapest(self):
        a = {"address": "A", "area": "40m2", "layout": "1LDK", "rent_yen": 150000, "total_yen": 160000, "url": "u1"}
        b = {**a, "total_yen": 155000, "url": "u2"}
        out = sc.dedupe([a, b])
        self.assertEqual(len(out), 1)
        self.assertEqual((out[0]["url"], out[0]["n_listings"]), ("u2", 2))


def _row(**kw):
    r = {"id": "bc_1", "site": "SUUMO", "also": "", "group": "RC", "line": "東横", "station": "祐天寺", "walk": 5, "building": "A",
         "rent": 15.0, "admin": 1.0, "total": 16.0, "area": 40.0, "age": 10, "structure": "鉄筋コン", "floor": "2階/4階建",
         "photos": 12, "shiki": "15", "rei": "15", "move_in": "即", "initial": 55.0, "initial_note": "", "note": "", "url": "https://suumo.jp/chintai/bc_1/"}
    r.update(kw)
    return r


class TestValidate(unittest.TestCase):
    ARGS = dict(max_rent=18, walk=7, max_age=20, min_area=28, min_photos=3)
    CONDS = [{"key": "rent_max", "value": 18}]

    def run_v(self, rows, plan_ids=None):
        plans_ = [{"id": i} for i in (plan_ids if plan_ids is not None else [r["id"] for r in rows])]
        return validate.validate(rows, plans_, self.CONDS, **self.ARGS)

    def test_ok(self):
        errors, _ = self.run_v([_row()])
        self.assertEqual(errors, [])

    def test_rejects_out_of_condition_rows(self):
        for bad in (dict(area=28.0), dict(walk=8), dict(age=21), dict(rent=18.5, total=19.5), dict(structure="木造"),
                    dict(photos=2), dict(initial=2.0), dict(total=20.0)):
            errors, _ = self.run_v([_row(**bad)])
            self.assertTrue(errors, bad)

    def test_cross_site_duplicate(self):
        errors, _ = self.run_v([_row(), _row(id="ch_2", site="CHINTAI", url="https://www.chintai.net/detail/2/")])
        self.assertTrue(any("別サイト" in e for e in errors))

    def test_orphan_plan(self):
        errors, _ = self.run_v([_row()], plan_ids=["bc_1", "bc_999"])
        self.assertTrue(any("候補にない間取り図" in e for e in errors))


if __name__ == "__main__":
    unittest.main()


class TestCollectDegrades(unittest.TestCase):
    """あるサイトが取得できなくても、他のサイトの結果は使って続ける (取得できなかったサイトは丸ごと外す)"""

    def test_failed_site_is_dropped_and_others_kept(self):
        import search_sites as ss
        orig_fetch, orig_targets = ss.sites.fetch, ss.TARGETS
        try:
            def fake_fetch(ses, url, params=None):
                if "homes" in url:
                    raise RuntimeError("202が続いた")
                return url
            ss.sites.fetch = fake_fetch
            ss.TARGETS = {
                "HOME'S": ("https://www.homes.co.jp/{line}/", {"toyoko": "t", "meguro": "m"}, lambda u: []),
                "CHINTAI": ("https://www.chintai.net/{line}/", {"toyoko": "t", "meguro": "m"},
                            lambda u: [{"url": u, "site": "CHINTAI"}] if "page" not in u else []),
            }
            rows, failed = ss.collect(["toyoko", "meguro"], 18, 7, max_pages=3, delay=0, log=lambda m: None)
        finally:
            ss.sites.fetch, ss.TARGETS = orig_fetch, orig_targets
        self.assertEqual(failed, ["HOME'S"])
        self.assertTrue(rows and all(r["site"] == "CHINTAI" for r in rows))
