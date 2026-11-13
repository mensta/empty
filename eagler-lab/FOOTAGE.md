# Footage log (files live in private storage, never in git)

This repo is public: this note lists file names, hashes and capture conditions only. The storage location is
shared privately with the video session. Frames are software-GL stills (SwiftShader); playback speed is set by
the chosen fps, not by the real game. All stills: seed `eagler`, build EaglercraftX 1.8-u53 JS
(sha256 of the original HTML starts `8d7b926f5488baba`), 1280x720 unless noted, noon (`/time set 6000`),
clear weather, HUD hidden, spectator, route warmed first (`warmPath`).

| name (under `cand/`) | sha256 | what |
|---|---|---|
| `orbit-plain-3s-30fps.mp4` | `c626694ceb14765eab49ad77d51694a97d56dfda579a4d314432a4acb043a2b3` | PBR off, 90 frames at 30 fps = 3.000 s, quarter orbit (~39 blocks) around a point 25 blocks ahead of [100.5, 100, 200.5]; virtual clock +1/30 s per frame; libx264 crf 16 yuv420p; made with `make-video.sh` |
| `orbit-plain-90frames-png.tar` | `9d4c9e5f59661e171d0cf2dc588b293f4f80544a77af988e50998d6e30d63c77` | the 90 source PNGs (`v-00000.png` ...) + `manifest.json` (requested vs got pose per frame, timing) for the clip above |
| `ab-plain-0.png` | `b80ad3385fe51136b37fcc285f04f84b9f06809417b19527e37368146dec6ca0` | PBR off, pose [100.5, 100, 200.5], yaw 45, pitch 10 |
| `ab-pbr-0.png` | `03a6e2d80b4aa0d8050918f56e128571c11c0074f3222deda9067ec97f53a323` | same pose, "High Performance PBR" 1.4.2 enabled |
| `ab-pbr-1.png` | `de01623d7279ce3e8eb98868c8e168515dfa7a5bf9f1392c79d7f2ac7a986f99` | same as `ab-pbr-0`, taken ~90 s later (differs in 0.23% of pixels) |
| `ab-side-by-side.png` | `235eb52cb33a954f089ee8992798d4e5afefbea6a7cf9db01e4ddf24bc0b279d` | plain (left) / PBR (right), downscaled; labelled |
| `still-1080p-plain.png` | `504640e5b71d394166070e0cd6fc30c4fe9e496afbb9e8236494114543e8ade1` | 1920x1080, PBR off, pose [100.5, 100, 200.5, 45, 10] |

Uploaded 2026-11-13 after the user's go-ahead; `orbit-plain-3s-30fps.mp4`, the tar and `ab-pbr-0.png` were
downloaded again and their sha256 matched. Not uploaded: the 4-frame PBR timing clip, intermediate/earlier stills
(the first A/B pair is superseded; it was taken with an under-loaded world).

## Group 2 (video lead request, 2026-11-13)

Same conditions as above unless noted (PBR off, build u53 JS). `SHA256SUMS.txt` is also in storage. 4 files were downloaded again and matched.

| name (under `cand/`) | sha256 | what |
|---|---|---|
| `boot-real-0-23s-720p.mp4` | `acee4d26550d164ca80f9c305f77a22a8f59a9e1a9edc161c4d32944ac8d8d89` | REAL boot recorded with Playwright (not frame-stepped), 1280x720, 30 fps resampled from 25, 0-23 s: offline-wrapper countdown (skipped at 2.4 s) -> splash -> Mojang logo -> Edit Profile / Default Username (first-run screens of a fresh profile) -> title at ~21 s; software GL; made with `boot-capture.js` (MODE=rec) |
| `title-4s-1080p-30fps.mp4` | `848a67c4afc31c7de52954ab7934df221baac43ab6724f52b812c9b0b56c278e` | title screen, 120 frames at 30 fps on the virtual clock, 1920x1080, PBR off; `boot-capture.js` (MODE=frames) |
| `title-4s-120frames-png.tar` | `ae95d3a3f04b33ddab2f56856066110d001e22f75cdd01391c71cd0a9e315a71` | the 120 source PNGs `t-00000..t-00119.png` |
| `menu-1-title-1080p.png` | `0aba96f0144cdde332180d43c83cd538834e929b8acbee74ee69bfc2e08e5ad3` | 1920x1080 still, PBR off; `menus-capture.js` |
| `menu-2-singleplayer-worldlist-1080p.png` | `530f7e2035504c4a61d9d3c2c5067ef636da7094fb90d33678be374f44018668` | Select World (empty list) |
| `menu-3a-new-world-choice-1080p.png` | `b2d1d0eb96bd274e24a1b741420c4512ffc9e45144c46a97693fc5fbc2d614af` | "What do you wanna do?" dialog (Create New World / Load EPK / Import Vanilla) |
| `menu-3b-create-new-world-1080p.png` | `0dd8b1cbb23234a28ad75f70030e6525b5ff74b327ab96effa86bcbfc26a6f03` | Create New World screen |
| `menu-4-options-1080p.png` | `4c135209bba1992d76be07d9a35f89840605ab0805bfc972d7066c5d826a118e` | Options |
| `menu-5-options-shaders-1080p.png` | `f185693476dc57926eafc421aedf8429ae99bdeb6001c142281599468f88fe29` | Options > Shaders ("Enable Shaders: No"; pack High Performance PBR 1.4.2) |
| `boot-log.txt` | `c80de52a2be18e1ec8ab7668a2ebe4e2e8cc0274da8003130168731fbfa3c7e7` | raw unfiltered console log of the recording run, 119 lines, ms since the recorder attached, cut at 23000 ms |
| `code-snippets.json` | `ac227948adccbade9bd98c85d6c02c924b90b64b2e45f70b9732fe9e54889c8b` | 3 excerpts of the original HTML with byte offsets (a: lines 4517-4528, b: lines 4507-4509 DL0, c: COMPILE_* names) |
| `credits-lines.json` | `573ce2b1409f2512d881dda925ceacf38acacd3b78d9faafcd759171660abfd6` | lines 8/10/11/69 of assets/eagler/CREDITS.txt, verbatim |
