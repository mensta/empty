# -*- coding: utf-8 -*-
"""検索から候補JSONまでを1コマンドで行う。

    python run.py                                   # 既定: 東急東横線・目黒線 / 東京都側 / 1LDK・2DK・2LDK / 19万円以下 / 徒歩10分 / 築35年 / 28㎡より広い
    python run.py --prefs tokyo kanagawa --walk 10  # 条件を変える
    python run.py --from-csv result.csv             # 検索済みの CSV から候補だけ作り直す (検索を省く)

出力 (--out-dir、既定 data/):
    candidates.json  候補の部屋 (1行 = 1部屋。木造を除外、RC / 鉄骨・ALC に分類)
    others_raw.json  他サイト (HOME'S / at home / CHINTAI) の検索結果 (--reuse-others で再利用)
    plans.json       間取り図 (縮小した WebP を data: URI で。ページは外部画像を読めないため)
    conditions.json  画面上部に出す検索条件 (このコマンドに渡した条件から作る)
    detail_cache.json  詳細ページのキャッシュ (次回は新しく出た物件の分だけ取得)

検索結果が0件、または取得に失敗したときは、既存の出力を上書きしない。
できたら ARTIFACT.md の手順でアーティファクトに反映する。
"""
import argparse
import csv
import datetime
import os
import re
import sys
import time

import web

import candidates as cand
import known_ids
import others
import plans
import search_sites as ss
import validate
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


def collect_others(a, raw_path, out_dir):
    """他サイトの一覧を取得し、known_ids の状態を更新して others_raw.json に保存する。
    --incremental-others のときは、全件取得の期限内のサイトだけ新着ページだけを取り、前回の結果と合わせる。"""
    state_path = os.path.join(out_dir, "known_ids.json")
    state = known_ids.normalize(cand.load_json(state_path, None))
    today = datetime.date.today()
    prev = cand.load_json(raw_path, [])
    plan = {}
    if a.incremental_others:
        plan = known_ids.plan_incremental(state, prev, list(ss.TARGETS), today, force_full=a.full_others)
        for site in ss.TARGETS:
            log(f"      {site}: " + ("増分 (新着順、既知のページで打ち切り)" if site in plan else "全件取得"))
    fresh, failed = ss.collect(a.lines, a.max_rent, a.walk, a.max_pages, a.delay, log=log, layouts=a.layout, incremental=plan)
    raw = known_ids.merge_rows(prev, fresh, set(plan), failed)
    ok = set(ss.TARGETS) - set(failed)
    full = ok - set(plan)
    _, diff = known_ids.update(state, fresh, today, ok, full)  # fresh = rows actually seen this run
    log(f"      掲載の変化: {diff.summary()}")
    cand.save_json(state_path, state)
    cand.save_json(raw_path, raw)
    return raw


def main() -> int:
    ap = argparse.ArgumentParser(description="SUUMO の沿線検索 -> 候補JSON")
    ap.add_argument("--lines", nargs="+", default=["toyoko", "meguro"], choices=list(sc.LINES))
    ap.add_argument("--prefs", nargs="+", default=["tokyo"], choices=list(sc.PREFS))
    ap.add_argument("--layout", nargs="+", default=["1LDK", "2DK", "2LDK"], choices=list(sc.LAYOUT_CODES), help="room layouts to include (any of them)")
    ap.add_argument("--max-rent", type=float, default=19.0, help="家賃の上限(万円)")
    ap.add_argument("--walk", type=int, default=10, help="駅徒歩の上限(分)")
    ap.add_argument("--max-age", type=int, default=35, help="築年数の上限")
    ap.add_argument("--min-area", type=float, default=28.0, help="専有面積がこの値(㎡)より広い部屋だけ")
    ap.add_argument("--min-photos", type=int, default=3, help="間取り図・周辺写真を除く写真の最低枚数 (0 で無効)")
    ap.add_argument("--max-pages", type=int, default=130)
    ap.add_argument("--delay", type=float, default=1.5, help="リクエスト間隔(秒)")
    ap.add_argument("--from-csv", help="検索を省き、この CSV (--raw で保存したもの) から候補を作る")
    ap.add_argument("--raw", help="検索結果を CSV でも保存する")
    ap.add_argument("--no-others", action="store_true", help="HOME'S / at home / CHINTAI を使わず、SUUMO だけにする")
    ap.add_argument("--reuse-others", action="store_true", help="他サイトは検索せず、<out-dir>/others_raw.json を使う")
    ap.add_argument("--incremental-others", action="store_true",
                    help=f"他サイトは新着順で取り、既知のページで打ち切る (前回の結果と合わせる)。{known_ids.FULL_EVERY_DAYS}日ごと、または初回は全件取得")
    ap.add_argument("--full-others", action="store_true", help="--incremental-others を付けていても、今回は他サイトを全件取得する")
    ap.add_argument("--out-dir", default=cand.DATA)
    ap.add_argument("--cache", help="詳細ページのキャッシュ (既定: <out-dir>/detail_cache.json)")
    web.add_proxy_argument(ap)
    a = ap.parse_args()
    try:
        proxy = web.configure_proxy(a.proxy)
    except ValueError as e:
        ap.error(str(e))
    if proxy:
        log(f"proxy: {proxy}")
    t0 = time.time()
    out_dir = a.out_dir
    cache = a.cache or os.path.join(out_dir, "detail_cache.json")

    # 1) 検索
    if a.from_csv:
        rows = list(csv.DictReader(open(a.from_csv, encoding="utf-8-sig")))
        log(f"[1/5] 検索を省略: {a.from_csv} から {len(rows)} 件")
    else:
        log("[1/5] SUUMO を検索")
        rows, total = sc.search_lines(web.new_session(), a.lines, a.prefs, a.layout, a.max_rent, a.walk, a.max_age,
                                      a.delay, a.max_pages, log=log, min_photos=a.min_photos)
        log(f"      掲載 {total} 件を取得 -> 条件に合う部屋 {len(rows)} 室")
        if a.raw and rows:
            write_raw(a.raw, rows)
            log(f"      検索結果を保存: {a.raw}")
    if not rows:
        log("条件に合う部屋が0件でした。既存の出力は変更していません。条件を見直してください。")
        return 1

    # 2) 候補 (詳細ページで構造を調べ、木造を除く)
    log("[2/5] 候補を作る")
    prefix = cand.PREF_PREFIX[a.prefs[0]] if len(a.prefs) == 1 else ""
    out = cand.build_candidates(rows, cache, prefix, a.max_age, a.min_area, a.walk, a.delay, log=log)
    if not out:
        log("候補が0件でした (全て木造、または条件外)。既存の出力は変更していません。")
        return 1

    # 3) 他サイト: SUUMO にない部屋だけを追加し、SUUMO の行には「他にも載っているサイト」を付ける
    plan_urls, site_names = {}, "SUUMO"
    if a.no_others:
        log("[3/5] 他サイトは使わない (--no-others)")
    elif a.prefs != ["tokyo"]:
        log("[3/5] 他サイトは東京都のみ対応のため、今回は使わない")
    else:
        log("[3/5] 他サイト (HOME'S / at home / CHINTAI)")
        raw_path = os.path.join(out_dir, "others_raw.json")
        if a.reuse_others and os.path.exists(raw_path):
            raw = cand.load_json(raw_path, [])
            log(f"      検索を省略: {raw_path} から {len(raw)} 件")
        else:
            raw = collect_others(a, raw_path, out_dir)
        found = ss.filter_rows(raw, a.lines, a.layout, a.max_rent, a.walk, a.max_age, a.min_area)
        log(f"      条件に合う部屋: {len(found)} 件")
        by_url = {r["url"]: r for r in rows}
        suumo_key = {}
        for r in out:
            s = by_url[r["url"]]
            suumo_key[r["id"]] = others.room_key(s["address"], float(re.match(r"[\d.]+", s["area"]).group()), int(s["rent_yen"]))
        extra, plan_urls, present = others.build_other_rows(found, set(suumo_key.values()), cache, a.min_photos, a.delay, log=log)
        for r in out:  # SUUMO の部屋が他サイトにも載っていれば記録
            r["also"] = "・".join(present.get(suumo_key[r["id"]], []))
        out = sorted(out + extra, key=lambda r: r["total"])
        used = [n for n in ("HOME'S", "at home", "CHINTAI") if any(r["site"] == n for r in raw)]
        site_names = "・".join(["SUUMO"] + used)  # 実際に取得できたサイトだけを表示に出す
        log(f"      使ったサイト: {site_names}")

    # 4) 間取り図
    log("[4/5] 間取り図を取得")
    plan_rows = plans.build_plans(out, os.path.join(out_dir, "plans"), log=log, plan_urls=plan_urls)

    # 5) 検証してから書き出す (前回との差も表示)
    log("[5/5] 検証と書き出し")
    conds = cand.make_conditions(a.layout, a.max_rent, a.lines, a.prefs, a.walk, a.max_age, a.min_area, a.min_photos, site_names)
    errors, warns = validate.validate(out, plan_rows, conds, max_rent=a.max_rent, walk=a.walk, max_age=a.max_age,
                                      min_area=a.min_area, min_photos=a.min_photos, layouts=a.layout)
    for w in warns:
        log(f"  警告: {w}")
    if errors:
        for e in errors[:20]:
            log(f"  エラー: {e}")
        log(f"検証エラーが {len(errors)} 件あるため、既存の出力は変更していません。")
        return 1
    cand_path = os.path.join(out_dir, "candidates.json")
    prev = {r["id"] for r in cand.load_json(cand_path, [])}
    cand.save_json(cand_path, out)
    cand.save_json(os.path.join(out_dir, "plans.json"), plan_rows)
    cand.save_json(os.path.join(out_dir, "conditions.json"), conds)
    now = {r["id"] for r in out}
    groups = {g: sum(r["group"] == g for r in out) for g in ("RC", "鉄骨・ALC")}
    n_other = sum(r["site"] != "SUUMO" for r in out)
    log(f"完了 ({time.time() - t0:.0f} 秒): 候補 {len(out)} 室 (RC {groups['RC']} / 鉄骨・ALC {groups['鉄骨・ALC']}、うち他サイトのみ {n_other})"
        + (f" | 前回比: 新規 {len(now - prev)} 室、なくなった {len(prev - now)} 室" if prev else ""))
    log(f"出力: {out_dir}/ の candidates.json・plans.json・conditions.json -> アーティファクトへの反映は ARTIFACT.md を参照")
    return 0


if __name__ == "__main__":
    sys.exit(main())
