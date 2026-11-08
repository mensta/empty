# -*- coding: utf-8 -*-
"""ページ取得の共通処理 (SUUMO・HOME'S・at home・CHINTAI 共通)。

実際に起きたこと (HOME'S で確認。他サイトも同様に備える):
1. サーバーは HTTP 202 や、200 でも本文が空 (0バイト) の応答を返すことがある (Cookie なしで10回に2回ほど)。
   そのまま解析すると「0件」「構造が空」「写真0枚」になり、例外が出ないので気づきにくい。
   (目黒線の一覧が0件になったのも、物件が「写真が少ない」と誤判定されたのも、これが原因だった。)
2. Cookie を保持した Session で続けて取得すると、最初の1回だけ通り、以降は何度待っても 202 のままになる。
   そこで取得のたびに Cookie を捨てる (接続の再利用は残す)。
本文の末尾が </html> で終わる応答だけを受け入れ、そうでなければ待ち時間を延ばして取り直す。
"""
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "ja,en;q=0.8",
}
RETRIES = 8          # 待ち時間は 3, 6, 12, 24, 30, 30, 30 秒
MAX_WAIT = 30


class Pacer:
    """サイト (ホスト) ごとのアクセス間隔。202 や空の応答が出たら、そのサイトへの間隔を自動で広げる。
    HOME'S は短時間に続けて取得すると、数十秒のあいだ 202 を返し続けることがあった (成功が数回続いたあとにまとめて失敗する)。"""

    def __init__(self, clock=time.monotonic, sleep=time.sleep, initial=None):
        self.gap, self.last, self.clock, self.sleep = dict(initial or {}), {}, clock, sleep

    def wait(self, host):
        need = self.gap.get(host, 0) - (self.clock() - self.last.get(host, -1e9))
        if need > 0:
            self.sleep(need)
        self.last[host] = self.clock()

    def penalize(self, host):
        self.gap[host] = min(10.0, max(4.0, self.gap.get(host, 0) * 1.5))


# HOME'S は1分に十数回を超えると、しばらく 202 を返し続ける (推測。1.5秒間隔の取得や、切り分けの試験の直後に起きた)。最初から約6秒あける
SLOW_SITES = {"www.homes.co.jp": 6.0}
PACER = Pacer(initial=SLOW_SITES)


def is_complete(status_code: int, content: bytes) -> bool:
    return status_code == 200 and b"</html" in content[-3000:].lower()


def fetch_soup(session, url, params=None, retries=RETRIES, sleep=time.sleep, pacer=None) -> BeautifulSoup:
    """完全な応答が返るまで取り直して解析する。続けて失敗したら RuntimeError (呼び出し側は結果を書き出さずに止まる)"""
    last, host, pacer = "不明", urlparse(url).netloc, pacer or PACER
    for i in range(retries):
        pacer.wait(host)
        if hasattr(session, "cookies"):
            session.cookies.clear()  # Cookie を持ち越すと 202 が続く (上の 2.)
        try:
            r = session.get(url, params=params, headers=HEADERS, timeout=30)
            r.raise_for_status()
            if is_complete(r.status_code, r.content):
                return BeautifulSoup(r.content, "html.parser")
            last = f"空または途中で切れた応答 (HTTP {r.status_code}, {len(r.content)} バイト)"
            pacer.penalize(host)
        except requests.RequestException as e:
            last = str(e)
        if i < retries - 1:
            sleep(min(MAX_WAIT, 3 * 2 ** i))
    raise RuntimeError(f"取得に失敗しました ({last}): {url}")
