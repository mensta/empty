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
import os
import subprocess
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "ja,en;q=0.8",
}
PROXY_ENV = "RENTAL_PROXY"
URBAN_JP = "urban-jp"  # special --proxy value: fetch a Japan-only Urban VPN proxy with scripts/urban/urban_proxy.mjs
URBAN_SCRIPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "urban")
PROXY_SCHEMES = ("http", "https", "socks5", "socks5h")  # socks* needs the optional PySocks package
_proxy_url = None  # set once at startup by configure_proxy()


def configure_proxy(url=None):
    """Route every session created by new_session() through the given proxy URL (http://[user:pass@]host:port).
    An empty value falls back to the RENTAL_PROXY environment variable; if that is empty too, no proxy is used.
    Returns a log-safe description (credentials removed) or None. Raises ValueError for a malformed URL."""
    global _proxy_url
    url = (url or os.environ.get(PROXY_ENV) or "").strip()
    if not url:
        _proxy_url = None
        return None
    if url == URBAN_JP:
        url = fetch_urban_jp()
    parsed = urlparse(url)
    if parsed.scheme not in PROXY_SCHEMES or not parsed.hostname:
        raise ValueError(f"invalid proxy URL (expected {'|'.join(PROXY_SCHEMES)}://[user:pass@]host:port)")
    _proxy_url = url
    return describe_proxy(url)


def fetch_urban_jp(run=subprocess.run):
    """Ask scripts/urban/urban_proxy.mjs for a working Japan proxy URL (the credential stays in this process).
    Raises ValueError with a readable message if Node or the dependencies are missing, or no server works."""
    if not os.path.isdir(os.path.join(URBAN_SCRIPT_DIR, "node_modules")):
        raise ValueError(f"{URBAN_JP}: run `npm install` in {URBAN_SCRIPT_DIR} first")
    try:
        r = run(["node", "urban_proxy.mjs"], cwd=URBAN_SCRIPT_DIR, capture_output=True, text=True, timeout=120)
    except FileNotFoundError:
        raise ValueError(f"{URBAN_JP}: node (>=20) is required") from None
    except subprocess.TimeoutExpired:
        raise ValueError(f"{URBAN_JP}: timed out while fetching a proxy") from None
    if r.returncode != 0:
        # stderr only contains server names and reasons, never the proxy URL
        last = ((r.stderr or "").strip().splitlines() or ["failed"])[-1]
        raise ValueError(f"{URBAN_JP}: {last[:300]}")
    lines = (r.stdout or "").split()
    if len(lines) != 1:
        raise ValueError(f"{URBAN_JP}: unexpected output from urban_proxy.mjs")
    return lines[0]


def describe_proxy(url):
    """scheme://host:port only. Never log the full URL: it may contain credentials."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.hostname}" + (f":{parsed.port}" if parsed.port else "")


def add_proxy_argument(ap):
    ap.add_argument("--proxy", metavar="URL",
                    help=f"send all requests through this proxy (http://[user:pass@]host:port), or '{URBAN_JP}' to fetch a Japan-only Urban VPN proxy. Default: ${PROXY_ENV} if set")


def new_session():
    """requests.Session honoring configure_proxy(). Every network entry point must create sessions here."""
    ses = requests.Session()
    if _proxy_url:
        ses.trust_env = False  # otherwise HTTP(S)_PROXY from the environment overrides the session proxy
        ses.proxies = {"http": _proxy_url, "https": _proxy_url}
    return ses


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
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                raise  # not transient: no retry. search_sites.collect treats it as "no such page" (e.g. a layout with no listings)
            last = str(e)
        except requests.RequestException as e:
            last = str(e)
        if i < retries - 1:
            sleep(min(MAX_WAIT, 3 * 2 ** i))
    raise RuntimeError(f"取得に失敗しました ({last}): {url}")
