# -*- coding: utf-8 -*-
"""Unpack the shared libraries headless Chromium needs into a directory, without root (apt is not usable here).

    python3 setup_libs.py /tmp/opencode/libs            # chrome-headless-shell (Playwright default)
    python3 setup_libs.py /tmp/opencode/libs --full     # also what the full Chromium needs (new headless mode)
    export LD_LIBRARY_PATH=/tmp/opencode/libs/usr/lib/aarch64-linux-gnu:/tmp/opencode/libs/lib/aarch64-linux-gnu

It downloads the Debian package index, resolves the dependencies that are not installed, and unpacks the .deb files with dpkg -x.
On a machine where `npx playwright install --with-deps` works, you do not need this.
"""
import argparse
import lzma
import os
import re
import subprocess
import urllib.request

BASE = ["libnspr4", "libnss3", "libatk1.0-0", "libdbus-1-3", "libxcomposite1", "libxdamage1", "libxfixes3", "libxrandr2",
        "libgbm1", "libxkbcommon0", "libasound2", "libatspi2.0-0"]
FULL = ["libatk-bridge2.0-0", "libcups2"]  # the full Chromium (chromium-XXXX/chrome-linux*/chrome) also needs these


def installed(name):
    out = subprocess.run(["dpkg-query", "-W", "-f=${Status}", name], capture_output=True, text=True).stdout
    return out.endswith("installed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dest")
    ap.add_argument("--full", action="store_true")
    a = ap.parse_args()
    arch = subprocess.run(["dpkg", "--print-architecture"], capture_output=True, text=True).stdout.strip()
    codename = re.search(r"VERSION_CODENAME=(\w+)", open("/etc/os-release").read()).group(1)
    index_url = f"https://deb.debian.org/debian/dists/{codename}/main/binary-{arch}/Packages.xz"
    os.makedirs(a.dest, exist_ok=True)
    pk = {}
    for blk in lzma.decompress(urllib.request.urlopen(index_url, timeout=120).read()).decode("utf-8", "ignore").split("\n\n"):
        d = dict(re.findall(r"^([A-Za-z\-]+): (.*)$", blk, re.M))
        if "Package" in d:
            pk[d["Package"]] = d
    todo, seen = [], set()

    def add(name):
        if name in seen or name not in pk:
            return
        seen.add(name)
        if installed(name):
            return
        todo.append(name)
        for dep in pk[name].get("Depends", "").split(","):
            add(re.sub(r"\s*\(.*\)", "", dep.split("|")[0].strip()))

    for n in BASE + (FULL if a.full else []):
        add(n)
    print("packages:", todo)
    for n in todo:
        fn = pk[n]["Filename"]
        deb = os.path.join(a.dest, os.path.basename(fn))
        if not os.path.exists(deb):
            urllib.request.urlretrieve("https://deb.debian.org/debian/" + fn, deb)
        subprocess.run(["dpkg", "-x", deb, a.dest], check=True)
    print("done. export LD_LIBRARY_PATH=%s/usr/lib/%s-linux-gnu:%s/lib/%s-linux-gnu  (adjust the triplet for your arch)" % (a.dest, "aarch64", a.dest, "aarch64"))


if __name__ == "__main__":
    main()
