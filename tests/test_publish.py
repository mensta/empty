# -*- coding: utf-8 -*-
"""Publishing to S3: the built page is self-contained and the upload order is safe. No AWS call is made."""
import base64
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import publish_s3 as pub


def write_data(d, plan_bytes=b"RIFFxxxxWEBP"):
    json.dump([{"id": "bc_1", "building": "x</script><b>", "layout": "1LDK"}], open(os.path.join(d, "candidates.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump([{"key": "layout", "label": "L", "text": "1LDK"}], open(os.path.join(d, "conditions.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump([{"id": "bc_1", "img": pub.DATA_URI + base64.b64encode(plan_bytes).decode()}], open(os.path.join(d, "plans.json"), "w"))


class TestBuildSite(unittest.TestCase):
    def test_page_is_self_contained_and_plans_are_files(self):
        with tempfile.TemporaryDirectory() as data, tempfile.TemporaryDirectory() as out:
            write_data(data)
            n, size = pub.build_site(out, data_dir=data)
            html = open(os.path.join(out, "index.html"), encoding="utf-8").read()
            self.assertEqual(n, 1)
            self.assertEqual(open(os.path.join(out, "plans", "bc_1.webp"), "rb").read(), b"RIFFxxxxWEBP")
            self.assertIn("window.RENTAL_DATA = ", html)
            self.assertIn('"img": "plans/bc_1.webp"', html)
            self.assertNotIn('href="tokens.css"', html)
            self.assertNotIn('src="dash-shim.js"', html)
            self.assertNotIn("(ローカル)", html)
            self.assertNotIn("data:image/webp", html)  # images are separate files, not embedded
            self.assertEqual(html.count("</script>"), html.count("<script"))  # the title text did not close a script

    def test_no_plans_option(self):
        with tempfile.TemporaryDirectory() as data, tempfile.TemporaryDirectory() as out:
            write_data(data)
            n, _ = pub.build_site(out, with_plans=False, data_dir=data)
            self.assertEqual(n, 0)
            self.assertEqual(os.listdir(os.path.join(out, "plans")), [])

    def test_rejects_unexpected_image_format(self):
        with tempfile.TemporaryDirectory() as data, tempfile.TemporaryDirectory() as out:
            write_data(data)
            json.dump([{"id": "bc_1", "img": "https://x/y.png"}], open(os.path.join(data, "plans.json"), "w"))
            with self.assertRaises(SystemExit):
                pub.build_site(out, data_dir=data)


class TestUpload(unittest.TestCase):
    def test_plans_are_uploaded_before_index(self):
        cmds = pub.aws_commands("/o", "b", "p/q/", "prof")
        self.assertIn("sync", cmds[0])
        self.assertTrue(cmds[0][-1] == "--only-show-errors" and "s3://b/p/q/plans/" in cmds[0])
        self.assertIn("cp", cmds[1])
        self.assertIn("s3://b/p/q/index.html", cmds[1])
        self.assertIn("no-cache", cmds[1])
        self.assertTrue(all("--delete" not in c and "rm" not in c for c in cmds))  # nothing is ever deleted

    def test_stops_when_an_upload_fails(self):
        calls = []

        class R:
            returncode, stderr = 1, "AccessDenied"

        def fake_run(cmd, **k):
            calls.append(cmd)
            return R()

        with tempfile.TemporaryDirectory() as data:
            write_data(data)
            orig = pub.DATA
            try:
                import publish_s3
                real_build = publish_s3.build_site
                publish_s3.build_site = lambda out, with_plans=True: real_build(out, with_plans, data_dir=data)
                with tempfile.TemporaryDirectory() as out:
                    rc = pub.main(["--out", out, "--profile", "x"], run=fake_run)
            finally:
                publish_s3.build_site = real_build
        self.assertEqual(rc, 1)
        self.assertEqual(len(calls), 1)  # index.html is not uploaded after the plans failed

    def test_check_live_reports_status_or_error(self):
        class Ok:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def opener(u, timeout):
            if u.endswith(".webp"):
                raise OSError("boom")
            return Ok()

        got = pub.check_live("https://h/a/index.html", "bc_1", opener=opener)
        self.assertEqual(got[0], ("index", 200))
        self.assertEqual(got[1][0], "plan")


if __name__ == "__main__":
    unittest.main()
