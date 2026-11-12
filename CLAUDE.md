@AGENTS.md

# Claude Code で作業するときの補足

- 作業の前提は上の `AGENTS.md` を読んでいる。ここには Claude Code 固有の注意だけを書く。
- アーティファクトの反映は `scripts/sync_artifact.py` を使う。`Artifact` / `ArtifactData` を直接呼ぶのは、スクリプトが使えないときの手動の修理だけ。その場合も `data/artifact_state.json` を更新する。
