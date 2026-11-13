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
