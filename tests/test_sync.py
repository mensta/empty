import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import sync_artifact as sa  # noqa: E402

OLD = {"candidates": "a" * 32, "plans": "b" * 32, "conditions": "c" * 32}
NEW = {"candidates": "1" * 32, "plans": "2" * 32, "conditions": "3" * 32}
HASHES = {"candidates": "h1", "plans": "h2", "conditions": "h3"}
STATE = {"url": "https://example.invalid/x", "blobs": OLD, "dataset_versions": {"candidates": 5, "plans": 4, "conditions": 4},
         "synced_sha": HASHES, "stale_blobs": []}


class ChangeDetection(unittest.TestCase):
    def test_same_hashes_mean_no_change(self):
        self.assertFalse(sa.changed(STATE, dict(HASHES)))

    def test_one_changed_file_means_change(self):
        self.assertTrue(sa.changed(STATE, {**HASHES, "plans": "other"}))

    def test_old_blobs_include_current_and_stale(self):
        st = {**STATE, "stale_blobs": ["d" * 32]}
        self.assertEqual(sa.old_blobs(st), sorted(["d" * 32] + list(OLD.values())))


class UploadCheck(unittest.TestCase):
    def test_good_upload_passes(self):
        self.assertEqual(sa.check_upload({"ok": True, "blobs": NEW, "errors": []}), [])

    def test_empty_blob_id_is_rejected(self):
        errs = sa.check_upload({"ok": True, "blobs": {**NEW, "plans": ""}, "errors": []})
        self.assertTrue(any("plans" in e for e in errs))

    def test_ok_false_is_rejected_and_errors_are_kept(self):
        errs = sa.check_upload({"ok": False, "blobs": NEW, "errors": ["拒否された"]})
        self.assertTrue(any("拒否された" in e for e in errs))
        self.assertTrue(any("ok=false" in e for e in errs))


class ApplyCheck(unittest.TestCase):
    def test_good_apply_passes(self):
        r = {"ok": True, "versions": {"candidates": 6, "plans": 5, "conditions": 5}, "deleted": [], "errors": []}
        self.assertEqual(sa.check_apply(r), [])

    def test_missing_version_is_rejected(self):
        r = {"ok": True, "versions": {"candidates": 6, "plans": None, "conditions": 5}, "deleted": [], "errors": []}
        self.assertTrue(any("plans" in e for e in sa.check_apply(r)))


class NewState(unittest.TestCase):
    def test_success_replaces_blobs_and_deletes_old(self):
        versions = {"candidates": 6, "plans": 5, "conditions": 5}
        st = sa.new_state(STATE, {"candidates": "n1", "plans": "n2", "conditions": "n3"}, NEW, versions,
                          set(OLD.values()), now="t")
        self.assertEqual(st["blobs"], NEW)
        self.assertEqual(st["dataset_versions"], versions)
        self.assertEqual(st["stale_blobs"], [])
        self.assertEqual(st["synced_at"], "t")

    def test_undeleted_old_blob_is_kept_as_stale(self):
        versions = {"candidates": 6, "plans": 5, "conditions": 5}
        st = sa.new_state(STATE, HASHES, NEW, versions, {OLD["candidates"]}, now="t")
        self.assertEqual(st["stale_blobs"], sorted([OLD["plans"], OLD["conditions"]]))


class Prompts(unittest.TestCase):
    def test_upload_prompt_has_no_leftover_placeholders(self):
        text = sa.fill(sa.UPLOAD_PROMPT, {"__URL__": "U", "__CANDIDATES__": "c", "__PLANS__": "p", "__CONDITIONS__": "d"})
        for token in ("__URL__", "__CANDIDATES__", "__PLANS__", "__CONDITIONS__"):
            self.assertNotIn(token, text)

    def test_apply_prompt_has_no_leftover_placeholders(self):
        repl = {"__URL__": "U", "__DOC_CANDIDATES__": "a", "__DOC_PLANS__": "b", "__DOC_CONDITIONS__": "c",
                "__OLD_BLOBS__": "x", "__NEW_BLOBS__": "y"}
        text = sa.fill(sa.APPLY_PROMPT, repl)
        for token in repl:
            self.assertNotIn(token, text)

    def test_claude_command_restricts_tools_and_model(self):
        cmd = sa.claude_command(sa.UPLOAD_TOOLS, sa.UPLOAD_SCHEMA)
        self.assertIn("claude-haiku-5-5", cmd)
        i = cmd.index("--tools")
        self.assertEqual(cmd[i + 1:i + 1 + len(sa.UPLOAD_TOOLS)], sa.UPLOAD_TOOLS)
        self.assertNotIn("Bash", cmd[i:])


class StateFile(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "s.json")
            sa.save_state(STATE, p)
            self.assertEqual(sa.load_state(p), STATE)
            self.assertFalse(os.path.exists(p + ".tmp"))


if __name__ == "__main__":
    unittest.main()
