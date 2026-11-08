# -*- coding: utf-8 -*-
"""検索から候補JSONまでを1コマンドで行う。

    python run.py                                   # 既定: 東急東横線・目黒線 / 東京都側 / 1LDK / 18万円以下 / 徒歩7分 / 築20年 / 35㎡以上
    python run.py --prefs tokyo kanagawa --walk 10  # 条件を変える
    python run.py --from-csv result.csv             # 検索済みの CSV から候補だけ作り直す (検索を省く)

出力 (--out-dir、既定 data/):
    candidates.json  候補の部屋 (1行 = 1部屋。木造を除外、RC / 鉄骨・ALC に分類)
    conditions.json  画面上部に出す検索条件 (このコマンドに渡した条件から作る)
    detail_cache.json  詳細ページのキャッシュ (次回は新しく出た物件の分だけ取得)

検索結果が0件、または取得に失敗したときは、既存の出力を上書きしない。
できたら ARTIFACT.md の手順でアーティファクトに反映する。
"""
import argparse
import csv
import os
import sys
import time

import requests

import candidates as cand
import suumo_scraper as sc


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def write_raw(path, rows):
    rows = [{k: v for k, v in r.items() if k != "access_list"} for r in rows]
    keys = list({k: 0 for r in rows for k in r})
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="SUUMO の沿線検索 -> 候補JSON")
    ap.add_argument("--lines", nargs="+", default=["toyoko", "meguro"], choices=list(sc.LINES))
    ap.add_argument("--prefs", nargs="+", default=["tokyo"], choices=list(sc.PREFS))
    ap.add_argument("--layout", default="1LDK", choices=list(sc.LAYOUT_CODES))
    ap.add_argument("--max-rent", type=float, default=18.0, help="家賃の上限(万円)")
    ap.add_argument("--walk", type=int, default=7, help="駅徒歩の上限(分)")
    ap.add_argument("--max-age", type=int, default=20, help="築年数の上限")
    ap.add_argument("--min-area", type=float, default=35.0, help="専有面積の下限(㎡)")
    ap.add_argument("--min-photos", type=int, default=3, help="間取り図・周辺写真を除く写真の最低枚数 (0 で無効)")
    ap.add_argument("--max-pages", type=int, default=130)
    ap.add_argument("--delay", type=float, default=1.5, help="リクエスト間隔(秒)")
    ap.add_argument("--from-csv", help="検索を省き、この CSV (--raw で保存したもの) から候補を作る")
    ap.add_argument("--raw", help="検索結果を CSV でも保存する")
    ap.add_argument("--out-dir", default=cand.DATA)
    ap.add_argument("--cache", help="詳細ページのキャッシュ (既定: <out-dir>/detail_cache.json)")
    a = ap.parse_args()
    t0 = time.time()
    out_dir = a.out_dir
    cache = a.cache or os.path.join(out_dir, "detail_cache.json")

    # 1) 検索
    if a.from_csv:
        rows = list(csv.DictReader(open(a.from_csv, encoding="utf-8-sig")))
        log(f"[1/3] 検索を省略: {a.from_csv} から {len(rows)} 件")
    else:
        log("[1/3] SUUMO を検索")
        rows, total = sc.search_lines(requests.Session(), a.lines, a.prefs, a.layout, a.max_rent, a.walk, a.max_age,
                                      a.delay, a.max_pages, log=log, min_photos=a.min_photos)
        log(f"      掲載 {total} 件を取得 -> 条件に合う部屋 {len(rows)} 室")
        if a.raw and rows:
            write_raw(a.raw, rows)
            log(f"      検索結果を保存: {a.raw}")
    if not rows:
        log("条件に合う部屋が0件でした。既存の出力は変更していません。条件を見直してください。")
        return 1

    # 2) 候補 (詳細ページで構造を調べ、木造を除く)
    log("[2/3] 候補を作る")
    prefix = cand.PREF_PREFIX[a.prefs[0]] if len(a.prefs) == 1 else ""
    out = cand.build_candidates(rows, cache, prefix, a.max_age, a.min_area, a.walk, a.delay, log=log)
    if not out:
        log("候補が0件でした (全て木造、または条件外)。既存の出力は変更していません。")
        return 1

    # 3) 書き出し (前回との差も表示)
    log("[3/3] 書き出し")
    cand_path = os.path.join(out_dir, "candidates.json")
    prev = {r["id"] for r in cand.load_json(cand_path, [])}
    cand.save_json(cand_path, out)
    cand.save_json(os.path.join(out_dir, "conditions.json"),
                   cand.make_conditions(a.layout, a.max_rent, a.lines, a.prefs, a.walk, a.max_age, a.min_area, a.min_photos))
    now = {r["id"] for r in out}
    groups = {g: sum(r["group"] == g for r in out) for g in ("RC", "鉄骨・ALC")}
    log(f"完了 ({time.time() - t0:.0f} 秒): 候補 {len(out)} 室 (RC {groups['RC']} / 鉄骨・ALC {groups['鉄骨・ALC']})"
        + (f" | 前回比: 新規 {len(now - prev)} 室、なくなった {len(prev - now)} 室" if prev else ""))
    log(f"出力: {cand_path} と conditions.json -> アーティファクトへの反映は ARTIFACT.md を参照")
    return 0


if __name__ == "__main__":
    sys.exit(main())
