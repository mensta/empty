# -*- coding: utf-8 -*-
"""Publish the viewer to S3 (served through the existing public CloudFront distribution).

    python scripts/publish_s3.py                  # build dist/site/ and upload it
    python scripts/publish_s3.py --dry-run        # build only; print the aws commands
    python scripts/publish_s3.py --url https://<cloudfront-host>/artifacts/rental-candidates/index.html   # also check the live page

Layout on S3 (same as the previous manual publish):
    <prefix>/index.html        single page, candidates and conditions embedded as window.RENTAL_DATA
    <prefix>/plans/<id>.webp   floor plans (relative URLs from index.html)

The bucket policy and the CloudFront settings are not touched. Nothing is deleted from S3.
This replaces scripts/sync_artifact.py (the Claude artifact is no longer updated).
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_viewer  # noqa: E402

DATA = os.path.join(ROOT, "data")
VIEWER = os.path.join(ROOT, "viewer")
DEFAULT_OUT = os.path.join(ROOT, "dist", "site")
DEFAULT_BUCKET = "live-my-life"
DEFAULT_PREFIX = "artifacts/rental-candidates"
DEFAULT_PROFILE = "mensta"
DATA_URI = "data:image/webp;base64,"


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _script_safe(obj):
    """JSON for an inline <script>: a literal '</' would end the script element."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def build_site(out_dir=DEFAULT_OUT, with_plans=True, data_dir=DATA):
    """Write out_dir/index.html and out_dir/plans/*.webp. Returns (number of plan files, size of index.html in bytes)."""
    candidates = json.load(open(os.path.join(data_dir, "candidates.json"), encoding="utf-8"))
    conditions = json.load(open(os.path.join(data_dir, "conditions.json"), encoding="utf-8"))
    plans_path = os.path.join(data_dir, "plans.json")
    if with_plans and not os.path.exists(plans_path):
        raise SystemExit("data/plans.json not found (it is not in git). Get it from the previous maintainer, run `python run.py`, or pass --no-plans.")
    plans_src = json.load(open(plans_path, encoding="utf-8")) if with_plans else []

    plans_dir = os.path.join(out_dir, "plans")
    os.makedirs(plans_dir, exist_ok=True)
    for name in os.listdir(plans_dir):  # only the local build directory; S3 is never cleaned
        os.remove(os.path.join(plans_dir, name))
    plans = []
    for p in plans_src:
        img = p.get("img") or ""
        if not img.startswith(DATA_URI):
            raise SystemExit(f"plans.json: unexpected image format for {p.get('id')}")
        with open(os.path.join(plans_dir, f"{p['id']}.webp"), "wb") as f:
            f.write(base64.b64decode(img[len(DATA_URI):]))
        plans.append({"id": p["id"], "img": f"plans/{p['id']}.webp"})

    html = build_viewer.render()
    for needle, repl in (
        (" (ローカル)</title>", "</title>"),
        ('<link rel="stylesheet" href="tokens.css">', "<style>\n" + _read(os.path.join(VIEWER, "tokens.css")) + "\n</style>"),
        ('<script src="dash-shim.js"></script>',
         "<script>window.RENTAL_DATA = " + _script_safe({"candidates": candidates, "plans": plans, "conditions": conditions})
         + ";</script>\n<script>\n" + _read(os.path.join(VIEWER, "dash-shim.js")) + "\n</script>"),
    ):
        if html.count(needle) != 1:
            raise SystemExit(f"viewer template changed: {needle!r} not found exactly once")
        html = html.replace(needle, repl)
    index = os.path.join(out_dir, "index.html")
    with open(index, "w", encoding="utf-8") as f:
        f.write(html)
    return len(plans), os.path.getsize(index)


def aws_commands(out_dir, bucket, prefix, profile):
    """The upload commands, plans first so the new index.html never points at missing images."""
    base = ["aws", "--profile", profile] if profile else ["aws"]
    dest = f"s3://{bucket}/{prefix.strip('/')}"
    return [
        base + ["s3", "sync", os.path.join(out_dir, "plans"), f"{dest}/plans/", "--content-type", "image/webp",
                "--cache-control", "public, max-age=86400", "--only-show-errors"],
        base + ["s3", "cp", os.path.join(out_dir, "index.html"), f"{dest}/index.html",
                "--content-type", "text/html; charset=utf-8", "--cache-control", "no-cache", "--only-show-errors"],
    ]


def check_live(url, plan_id=None, opener=urllib.request.urlopen):
    """GET the page (and one floor plan). Returns a list of (what, status) with status an int or an error string."""
    results = []
    targets = [("index", url)]
    if plan_id:
        targets.append(("plan", url.rsplit("/", 1)[0] + f"/plans/{plan_id}.webp"))
    for what, u in targets:
        try:
            with opener(u, timeout=30) as r:
                results.append((what, r.status))
        except Exception as e:  # HTTPError carries .code
            results.append((what, getattr(e, "code", None) or str(e)[:80]))
    return results


def main(argv=None, run=subprocess.run):
    ap = argparse.ArgumentParser(description="Publish the viewer to S3")
    ap.add_argument("--bucket", default=DEFAULT_BUCKET)
    ap.add_argument("--prefix", default=DEFAULT_PREFIX)
    ap.add_argument("--profile", default=os.environ.get("AWS_PROFILE", DEFAULT_PROFILE), help="AWS CLI profile (default: $AWS_PROFILE or mensta)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="local build directory")
    ap.add_argument("--no-plans", action="store_true", help="publish without floor plans")
    ap.add_argument("--dry-run", action="store_true", help="build only; print the aws commands")
    ap.add_argument("--url", default=os.environ.get("RENTAL_PUBLIC_URL"), help="public URL of index.html; checked after the upload")
    a = ap.parse_args(argv)

    n, size = build_site(a.out, with_plans=not a.no_plans)
    print(f"built {a.out}: index.html {size // 1024} KB, {n} floor plans", file=sys.stderr)
    cmds = aws_commands(a.out, a.bucket, a.prefix, a.profile)
    if a.dry_run:
        for c in cmds:
            print(" ".join(c))
        print("dry-run: nothing was uploaded", file=sys.stderr)
        return 0
    for c in cmds:
        r = run(c, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"upload failed ({' '.join(c[:5])} ...): {(r.stderr or '').strip()[-400:]}", file=sys.stderr)
            return 1
    print(f"uploaded to s3://{a.bucket}/{a.prefix.strip('/')}/", file=sys.stderr)
    if a.url:
        first = next(iter(sorted(os.listdir(os.path.join(a.out, "plans")))), None)
        for what, status in check_live(a.url, first[:-5] if first else None):
            print(f"  {what}: {status}", file=sys.stderr)
    else:
        print("note: CloudFront may still serve the old copy; pass --url to check the live page", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
