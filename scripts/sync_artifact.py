# -*- coding: utf-8 -*-
"""データ (data/*.json) の変更を、物件候補アーティファクトへ反映する。

Claude (既定は Haiku) を headless で二回だけ呼ぶ。Claude にさせるのは、次の機械的な作業だけ:
  1回目 (道具: Artifact, Read)           : 3ファイルのアップロード
  2回目 (道具: ArtifactData, Artifact)   : datasets の更新と、古い blob の削除
その間の反映用ドキュメントの生成 (artifact_docs.py) と、状態の保存はスクリプトが行う。
ページ本体 (files/index.html) は変えない。状態は data/artifact_state.json に保存する。

    python scripts/sync_artifact.py              # データが変わっていれば反映 (変わっていなければ何もしない)
    python scripts/sync_artifact.py --force      # 変わっていなくても反映する
    python scripts/sync_artifact.py --dry-run    # Claude を呼ばず、判定と送る指示を表示する

前提: `claude` コマンドがログイン済みで、Artifact / ArtifactData が使えること。
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "data", "artifact_state.json")
UPLOAD_PROMPT = os.path.join(ROOT, "scripts", "sync_upload_prompt.md")
APPLY_PROMPT = os.path.join(ROOT, "scripts", "sync_apply_prompt.md")
MODEL = "claude-haiku-5-5"
BUDGET_USD = "0.5"  # 1回あたり
FILES = {"candidates": "data/candidates.json", "plans": "data/plans.json", "conditions": "data/conditions.json"}
DOCS = {k: f"data/artifact_docs/doc_{k}.json" for k in FILES}
BLOB_RE = re.compile(r"^[0-9a-f]{32}$")

UPLOAD_TOOLS = ["Artifact", "Read"]
APPLY_TOOLS = ["ArtifactData", "Artifact", "Read"]
UPLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "ok": {"type": "boolean"},
        "blobs": {"type": "object", "properties": {k: {"type": "string"} for k in FILES}, "required": list(FILES)},
        "errors": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["ok", "blobs", "errors"],
}
APPLY_SCHEMA = {
    "type": "object",
    "properties": {
        "ok": {"type": "boolean"},
        "versions": {"type": "object", "properties": {k: {"type": "integer"} for k in FILES}, "required": list(FILES)},
        "deleted": {"type": "array", "items": {"type": "string"}},
        "errors": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["ok", "versions", "deleted", "errors"],
}


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def current_hashes(root=ROOT):
    return {k: sha256(os.path.join(root, v)) for k, v in FILES.items()}


def load_state(path=STATE):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_state(state, path=STATE):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def changed(state, hashes):
    return any(state.get("synced_sha", {}).get(k) != h for k, h in hashes.items())


def old_blobs(state):
    """次の反映で消す古い blob: 今使っているもの + 前回消せなかったもの"""
    return sorted(set(state.get("stale_blobs", [])) | set(state.get("blobs", {}).values()))


def fill(path, repl):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    for k, v in repl.items():
        text = text.replace(k, v)
    return text


def claude_command(tools, schema):
    # --tools と --allowedTools は可変長の引数。指示は stdin で渡す。
    return ["claude", "-p", "--model", MODEL, "--no-session-persistence", "--output-format", "json",
            "--json-schema", json.dumps(schema, ensure_ascii=False),
            "--permission-mode", "bypassPermissions", "--tools", *tools,
            "--max-budget-usd", BUDGET_USD]


def run_claude(prompt, tools, schema, root=ROOT):
    proc = subprocess.run(claude_command(tools, schema), input=prompt, capture_output=True, text=True,
                          cwd=root, timeout=1800)
    if proc.returncode != 0:
        raise SystemExit(f"claude が失敗しました (終了コード {proc.returncode}): {proc.stderr[-800:]}")
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise SystemExit(f"claude の出力を読めません: {proc.stdout[-800:]}")
    if out.get("is_error") or out.get("subtype") != "success":
        raise SystemExit(f"claude の実行が正常に終わりませんでした: {out.get('subtype')}")
    result = out.get("structured_output")
    if result is None:
        result = json.loads(out.get("result") or "{}")
    return result


def check_upload(r):
    """アップロードの結果が、次の段階に進めてよい形かを確かめる。問題の一覧を返す (空なら OK)"""
    if not isinstance(r, dict):
        return ["結果の形式が違います"]
    errs = [f"アップロードの結果: {e}" for e in (r.get("errors") or [])]
    if r.get("ok") is not True:
        errs.append("アップロードが ok=false でした")
    blobs = r.get("blobs") or {}
    for k in FILES:
        if not BLOB_RE.match(str(blobs.get(k, ""))):
            errs.append(f"blob id が不正です: {k}={blobs.get(k)!r}")
    return errs


def check_apply(r):
    if not isinstance(r, dict):
        return ["結果の形式が違います"]
    errs = [f"反映の結果: {e}" for e in (r.get("errors") or [])]
    if r.get("ok") is not True:
        errs.append("反映が ok=false でした")
    versions = r.get("versions") or {}
    for k in FILES:
        if not isinstance(versions.get(k), int):
            errs.append(f"version が不正です: {k}={versions.get(k)!r}")
    return errs


def new_state(state, hashes, blobs, versions, deleted, now=None):
    """成功した反映の結果から、次の状態を作る。消せなかった古い blob は stale_blobs に残す"""
    stale = sorted(b for b in old_blobs(state) if b not in blobs.values() and b not in deleted)
    return {
        "url": state["url"],
        "blobs": {k: blobs[k] for k in FILES},
        "dataset_versions": {k: versions[k] for k in FILES},
        "synced_sha": hashes,
        "stale_blobs": stale,
        "synced_at": now or time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }


def main():
    ap = argparse.ArgumentParser(description="データを物件候補アーティファクトへ反映する (Claude Haiku を headless で使う)")
    ap.add_argument("--force", action="store_true", help="データが変わっていなくても反映する")
    ap.add_argument("--dry-run", action="store_true", help="Claude を呼ばず、判定と送る指示を表示する")
    a = ap.parse_args()

    state = load_state()
    hashes = current_hashes()
    if not a.force and not changed(state, hashes):
        log("変更なし: data/*.json は前回の反映から変わっていません。反映は不要です。")
        return 0

    repl_up = {"__URL__": state["url"], **{"__" + k.upper() + "__": os.path.join(ROOT, v) for k, v in FILES.items()}}
    if a.dry_run:
        print(fill(UPLOAD_PROMPT, repl_up))
        print("--- 次の段階 (反映) は、アップロード後に artifact_docs.py で作った data/artifact_docs/ を使う")
        print("--- 1回目の実行:", " ".join(claude_command(UPLOAD_TOOLS, UPLOAD_SCHEMA)))
        log("dry-run: Claude は呼んでいません。")
        return 0

    # 1) アップロード (Claude)
    log(f"1/3 アップロード (モデル: {MODEL})")
    up = run_claude(fill(UPLOAD_PROMPT, repl_up), UPLOAD_TOOLS, UPLOAD_SCHEMA)
    errs = check_upload(up)
    if errs:
        log("反映は完了していません。状態ファイルは変更していません:")
        for e in errs:
            log(f"  - {e}")
        return 1
    blobs = {k: up["blobs"][k] for k in FILES}

    # 2) 反映用ドキュメントの生成 (スクリプト)
    log("2/3 反映用ドキュメントを作る")
    cmd = ["python3", os.path.join(ROOT, "artifact_docs.py"),
           "--candidates", blobs["candidates"], "--plans", blobs["plans"], "--conditions", blobs["conditions"]]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    missing = [p for p in DOCS.values() if not os.path.exists(os.path.join(ROOT, p))]
    if proc.returncode != 0 or missing:
        log(f"  artifact_docs.py が失敗しました: {proc.stderr[-400:] or missing}")
        log(f"  アップロード済みの新しい blob (次回の反映で消す): {list(blobs.values())}")
        save_state({**state, "stale_blobs": sorted(set(state.get("stale_blobs", [])) | set(blobs.values()))})
        return 1

    # 3) datasets の更新と古い blob の削除 (Claude)
    log("3/3 datasets を更新し、古い blob を消す")
    repl_ap = {
        "__URL__": state["url"],
        "__DOC_CANDIDATES__": os.path.join(ROOT, DOCS["candidates"]),
        "__DOC_PLANS__": os.path.join(ROOT, DOCS["plans"]),
        "__DOC_CONDITIONS__": os.path.join(ROOT, DOCS["conditions"]),
        "__OLD_BLOBS__": ", ".join(old_blobs(state)) or "(なし)",
        "__NEW_BLOBS__": ", ".join(blobs.values()),
    }
    ap_res = run_claude(fill(APPLY_PROMPT, repl_ap), APPLY_TOOLS, APPLY_SCHEMA)
    errs = check_apply(ap_res)
    if errs:
        log("反映は完了していません。状態ファイルは変更していません (古い blob は使い続けます):")
        for e in errs:
            log(f"  - {e}")
        log(f"  アップロード済みの新しい blob: {list(blobs.values())}")
        save_state({**state, "stale_blobs": sorted(set(state.get("stale_blobs", [])) | set(blobs.values()))})
        return 1

    nxt = new_state(state, hashes, blobs, ap_res["versions"], set(ap_res.get("deleted") or []))
    save_state(nxt)
    log(f"完了: blob {nxt['blobs']}、version {nxt['dataset_versions']}")
    if nxt["stale_blobs"]:
        log(f"  消せなかった古い blob (次回削除): {nxt['stale_blobs']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
