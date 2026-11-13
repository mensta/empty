# Eaglercraft 1.8.8 (u53, JS build) — analysis findings

Subject: the official offline single-file build `eaglercraft1-8-62da5f39.zip` (JS, not WASM-GC),
downloaded from the project's own download page. Neither the build nor any game asset is in this repo.
Everything marked **[verified]** was observed by running or reading the build in this environment;
**[research]** came from the pre-research notes and was NOT independently checked.

## 1. What the file is  [verified]
- One 34.9 MB HTML file, three parts: a tiny `eaglercraftXOpts` launch-options script,
  one ~22.6 MB TeaVM-generated JS program, and the asset pack (EPK) embedded as base64
  (12.27 M chars -> 9.2 MB -> gunzip -> 19.2 MB).
- The only symbol exported from the JS program is `main` (`$rt_exports.main`).
- On-screen: `Minecraft 1.8.8`, `EaglercraftX 1.8-u53 ultimate [JS]`, `Resources Copyright Mojang AB`.

## 2. Boot sequence (from the console log)  [verified]
EagRuntimeX starts -> creates the canvas -> WebGL **2.0** context (via ANGLE) and the extensions it
unlocks -> embedded EPK is "downloaded" (it is a data: URI) and decompressed -> **4872 resources**
loaded -> filesystem init (worlds live in IndexedDB, name `worlds`) -> sound engine -> MediaRecorder
probe -> Minecraft client thread starts -> resource manager reload (includes OptiFine-style
connected-textures code) -> title screen.
First run also shows content-warning, profile and default-username screens.

## 3. EPK container  [verified, fully parsed, 0 CRC mismatches]
Outer: `EAGPKG$$` + `ver2.0` header, then one gzip stream. Inner: `HEAD`, then repeated
`>FILE <len1><name> <len4> [crc32 | data | ':']`, ended by `>END$`. 4872 files:

| folder | files | size |
|---|---|---|
| minecraft/lang | 75 | 7.64 MB |
| minecraft/sounds (ogg effects) | 537 | 4.24 MB |
| minecraft/textures | 1059 | 3.27 MB |
| eagler/glsl (shaders) | 291 files in folder* | 0.82 MB |
| minecraft/models | 1595 | 0.75 MB |

*folder also holds non-shader files; 79 are `.vsh/.fsh/.glsl`.
No music tracks are present (the game logs "File ... does not exist" for each) — consistent with
[research] "music removed to shrink the file". Sound *effects* are kept.

## 4. GPU layer  [verified by reading the shaders; Java-side GL wrapper not read]
- Rendering is **WebGL 2.0**, not WebGPU. A WebGL 1.0 (GLES 2.00) fallback path also exists
  (`gles2_compat.glsl` maps `EAGLER_IN/OUT/TEXTURE_2D...` macros to either GLSL ES 3.00 or 1.00).
- `core.vsh`/`core.fsh` re-implement the fixed-function OpenGL pipeline as ONE uber-shader whose
  features are switched with `COMPILE_*` defines: texture matrix, vertex colour, normals,
  lightmap, texgen planes, alpha test, fog, additive blend, and Minecraft's 2-light diffuse lighting.
  Shader variants are therefore generated per GL state combination.
- Beyond emulation there is a full **deferred PBR pipeline** (`glsl/deferred/*`, 50+ shaders):
  G-buffer, sun shadows (LOD cascades), SSAO, screen-space reflections, subsurface scattering,
  realistic water, volumetric clouds, light shafts, bloom, tonemap, lens effects, FXAA.
  Title screen advertises "PBR Shaders".
- **Java-side variant selection (R4)  [verified by reading `main.js` + runtime recording]**
  One function (minified `C3n(b,c,d)`) takes a **12-bit bitmask** `b`, builds the `#define COMPILE_*`
  header (`b&1` TEXTURE_ATTRIB, `&2` COLOR_ATTRIB, `&4` NORMAL_ATTRIB, `&8` LIGHTMAP_ATTRIB,
  `&16` ENABLE_TEXTURE2D, `&32` ENABLE_LIGHTMAP, `&64` ENABLE_ALPHA_TEST, `&128` ENABLE_MC_LIGHTING,
  `&256` ENABLE_TEX_GEN, `&512` ENABLE_ANISOTROPIC_FIX, `&1024` ENABLE_FOG, `&2048` BLEND_ADD),
  loads `core.vsh`/`core.fsh` once, compiles and links the pair. So at most 4096 variants exist.
  Recorded in a ~63 s session (title screen -> world -> spectator camera): 57 `shaderSource` calls,
  **29 programs, 21 of them core variants**, each compiled once (cache works), created in bursts when a
  GL state combination first appears (menus, world load). Only 9 of the 12 flags were hit
  (no TEX_GEN, ANISOTROPIC_FIX, BLEND_ADD in this short session).
  **No deferred/PBR flag is compiled with default settings** — the pack's PBR pipeline is OFF by default.
  (Turning it on is covered in "R9" below.) The game's own log confirms the bit reading: the deferred
  pipeline logs lines like `Compiling program for core state: 1 4 16 64, ext state: 8`
  (= TEXTURE_ATTRIB, NORMAL_ATTRIB, ENABLE_TEXTURE2D, ENABLE_ALPHA_TEST).
  Not read: the state-tracking code that decides which bits to set (the GL-call side before `C3n`).
- Shader sources carry `Copyright (c) 2022-2024 lax1dude` — they are the project's own code,
  not Mojang's. [verified]

## 5. Compiled-code shape (TeaVM)  [verified]
- **Build identity (R2)  [verified]**: the JS carries TeaVM's runtime helper set — 134 distinct `$rt_*`
  names, ~3,740 uses (`$rt_mainStarter`, `$rt_startThread`, `$rt_nativeThread`, `$rt_wrapFunction0..4`,
  `$rt_createArray`, `$rt_cls`, `$rt_str`, `$rt_eraseClinit`, `$rt_decodeStack` ...). Compared with the
  open-source TeaVM `master` runtime (Apache-2.0, `core/src/main/resources/org/teavm/backend/javascript/*.js`):
  **114 of 134 (85%) are defined there**. The other 20 are older-style cache variables
  (`$rt_intclsCache`...), wrapper scope variables (`$rt_exports`, `$rt_globals`) and
  customisations (`$rt_putStdoutCustom`, `$rt_putStderrCustom`). Conclusion: TeaVM-family output,
  older or locally modified relative to current master; **the exact TeaVM version was not found** in the file.
  Java origin is consistent (Java exception model `$rt_javaException`, class/`instanceof` model, log class
  names), but package names are stripped from the string pool (only `net.lax1dude.eaglercraft.v1_8.client` remains).
- Identifiers are minified (e.g. `HRd`); 11,733 strings live in one shared pool (`$rt_stringPool`).
- Blocking Java code is rewritten into **state machines** (`switch($p){case 0:... $p=1; case 1:...}`)
  so Java threads can suspend/resume on the single JS thread.
- `deobfClassName` / `deobfFunctionFullName` exist, but the string pool has **no field names**
  (`thePlayer`, `posX`, ... occur 0 times) and the runtime says "Loading deobfuscation data", so the
  full map is not in the offline file. Names had to be found empirically.
- The `Minecraft` constructor was located via the log string "Setting user: " (pool index 565);
  its static singleton is `HRd`.

## 6. Client + integrated server  [verified]
Log threads are `Client thread` and `IntegratedServer`; client logs `NetHandlerSingleplayerLogin`
(protocol 5) — singleplayer is a real client/server pair talking packets, as in vanilla 1.8.
The server logs `Can't keep up! ... skipping N tick(s)` when the CPU is starved by software GL.

## 7. Experiments  [verified]
- **Render gate (R1, repeated)**: `gl-gate.js` wraps WebGL2 draw/clear/blit entry points and skips them
  while a flag is off. Setup: software GL (SwiftShader), 1280x720, spectator camera, scene loaded, F3 on;
  4 rounds each of ON and OFF, 12 s windows, alternating order (`measure-r1-r4.js`).
  * **Render loop**: GL `clear` calls/s (a frame proxy): ON 105 +/- 6 -> OFF 314 +/- 5, ratio **2.98**
    (2.68-3.27 across runs). The game's own F3 counter read **14-17 fps ON** and **50-60 fps OFF**
    (9 single reads right after switching back; OFF looks capped at 60 by the on-screen `vsync`), i.e.
    roughly 3-4x. Treat "about 3x" as the supported claim; the OFF figure is vsync-capped.
  * **Game logic did NOT speed up**: server game time advanced **20.01 ticks/s ON and 20.01 OFF**
    (`/time query gametime` vs log timestamps); the client tick counter moved the same in both modes.
    So the 3x is *frames drawn per second*, not simulation speed. (An earlier note here said the
    "game loop" ran 3.2x faster — corrected.)
  * GL commands attempted/s: ON ~2.5k, OFF ~5.8k (the game also issues more draws per second when frames
    are faster). The earlier "792 commands/s -> 0" figure was a single sample in a different scene.
  * Not measured: other resolutions, a real GPU, WASM-GC build; clears-per-frame was assumed constant.
- **PBR shader pack (R9)  [verified, one run]**: Options -> `Shaders...` shows the built-in pack
  "High Performance PBR", author lax1dude, version 1.4.2, with sub-options (Waving Grass, Dynamic Lights,
  Global SSAO ... all ON). `Enable Shaders: No -> Yes`, then `Done` triggers "Refreshing Resources...
  Please Wait." (about 10 s; clicks sent meanwhile are swallowed).
  * **It really runs**: after entering a world, shader programs went **24 -> 84** and shader sources
    47 -> 138; new flags appeared: SSAO reprojection, SSR (screen-space reflections), env-map
    reflections, sun shadows (LOD2, smooth), subsurface scattering, atmospheric + linear fog, clouds,
    paraboloid sky/env map, dynamic lights, waving blocks, G-buffer vs forward vertex paths. The log tag is
    `DeferredGBufferPipelineCompiler`. Largest shader sources are ~27 KB of GLSL each.
  * **WebGL extensions the game requests** (all granted here): `EXT_color_buffer_float`,
    `OES_texture_float_linear`, `EXT_texture_filter_anisotropic`, `WEBGL_debug_renderer_info`.
    (Recorded `getExtension` calls only — "requested", not proven "required".) Needs WebGL 2.0 for the
    GLES 3.00 path.
  * **Cost under software GL (SwiftShader, 1280x720)**: F3 showed **1 fps** (single read, integer display),
    `TPS: 20/20`. Steady state over 11 probes: ~10.5 `clear` calls/s and ~560 GL commands/s reaching the
    GPU (vs ~105 clears/s and ~2.5k cmds/s with PBR off) — frames are an order of magnitude slower while
    the simulation keeps 20 TPS. One screenshot could take more than 60 s; the default 30 s timeout failed.
    "Time per frame" is therefore on the order of a second here; it says nothing about a real GPU.
  * Caveat: in this run the inventory screen was open (at ~1 fps the typed `/tp`/`/gamemode` did not get
    through and a letter opened the inventory), so there is no clean before/after still at an identical
    pose yet. The screenshot does show PBR-lit terrain (soft shadows, dim lighting), but not as a fair comparison.
- **Player state** (this build only): `mc = window.__eagMC()` (needs a one-line hook patch on a COPY),
  `mc.bR` = player; `D/J/E` = x/y/z, `bN/cR` = yaw/pitch, bounding box `mc.bR.dz`
  (`cG/b4/cF` min, `cL/cI/cM` max).
- **Server authority**: yaw/pitch writes stick immediately. Position writes of +5 blocks, and a
  20-block path in 0.25-block steps, were accepted — the server-held position (read via
  `/tp @p ~ ~ ~`) matched. 40+ block jumps, and fast writes while rendering was slow, were reverted.
  Working explanation (not measured): per-packet displacement limit (~10 blocks in vanilla).

## 8. Not done / unverified
- Java-side state tracking that chooses the `C3n` bitmask (the GL-call side) not read; the bitmask -> compile step is read.
- [research] "LWJGL rewritten for WebGL" — not checked in code.
- Multiplayer path: the launch options list a shared-world relay (`wss://relay.eaglercraft.net/`);
  the WebSocket proxy path described in research was not exercised.
- WASM-GC build not compared. PBR: no clean before/after still at the same pose; no real-GPU frame time. Textures/lang contents not inspected.

## 9. Legal/sensitivity note for the video
The build bundles Mojang's assets and the project's own site carries a DMCA page. Explaining the
structure is one thing; showing assets at length or pointing to a download is the riskier part.

## Reproduce
`EAGLER_HTML=<path to html> node eagler-lab/<script>.js` (needs Playwright + Chromium).
`python3 -I eagler-lab/parse-epk.py <decompressed-epk> <out.json>` lists the pack.

## 10. Capture toolkit findings  [verified]
- **Full pack catalogue (R7 closed)**: `extract-build.py` reads all **4872** entries, **18,853,633** data
  bytes, **0 CRC mismatches**; folder totals add up exactly. Largest: lang 75 files / 7.6 MB, sounds 537 /
  4.2 MB, textures 1059 / 3.3 MB, `eagler/glsl` 291 / 0.82 MB, models 1595 / 0.75 MB, `eagler/mesh` 26 /
  0.61 MB, blockstates 340 / 0.25 MB, `eagler/icudt` 4 / 0.25 MB, `relay_download.zip` 0.24 MB. By
  extension: json 1948, png 1917, ogg 537, ebp 192, lang 75, fsh 53, vsh 22, glsl 4, properties 37.
- **Where the HTML's bytes go** (`parts.json`): 34.9 MB file = launch-options script + 22.6 MB TeaVM
  program + 12.27 M base64 chars (-> 9.2 MB EPK -> 19.2 MB after gunzip).
- **Console log**: attaching the listener before `goto` and writing every line gives ~240-260 lines for
  start + world creation, first line at ~1.4 s after navigation; the 41 "File ... does not exist" (no music)
  and 39 OptiFine lines are kept.
- **Hook discovery** (`patch-hook.js`): found entry `HjT`, constructor `BC3`, singleton `HRd` from the
  "Setting user: " pool string alone; output is byte-identical to the hand-patched copy.
- **Chunk streaming vs. screenshots**: at a pose reached by `/tp`, a stable-looking still showed only the
  nearest hill; the same pose after flying the route showed far hills, trees and fog. The terrain-only
  difference between a frame and a later frame at the same pose is **0.000%** once the route has been warmed;
  the remaining ~2.7% of the whole image is cloud drift. `waitChunks` (no `bufferData` for 3 s) returned
  "quiet" too early, so it is only a hint.
- **Earlier PBR on/off stills** were taken before this was understood and show a partially loaded world; they
  also made PBR look temporally unstable (24.5% of pixels differing between two shots). That conclusion was
  wrong. Superseded by the re-shot set below.
- **Same-pose PBR on/off stills (re-shot, warmed route, 1280x720, seed `eagler`, noon, clear, HUD hidden)**:
  pose `[100.5, 100, 200.5, yaw 45, pitch 10]` reached on both runs. Plain vs PBR: 63% of all pixels and
  **69.8% of the terrain region differ** (PBR: tone-mapped muted colours, hazy atmospheric sky and fog,
  soft cloud, different shading; geometry identical). Two PBR shots ~90 s apart: **0.23%** whole image /
  0.42% terrain differ, so PBR does settle given enough frames (>= 60 clears). Plain stills keep ~1% drift from
  clouds (5 attempts ended at 1.02%). Under PBR `waitChunks` never reports quiet (buffer uploads continue), so
  that heuristic is meaningless there; the warm pass with drawing off is what loads the terrain.
- **Capture cost**: a plain still takes ~2-15 s per attempt, usually 2-5 attempts; a 5-frame orbit with a
  warm pass took ~6 min; a 1920x1080 still ~40 s. PBR stills take 100+ s each.
- **Server-accepted camera moves**: a 5-frame orbit (18 sub-steps of <= 2 blocks per leg, 120 ms apart)
  was accepted at every frame; the server's own position (`/tp @p ~ ~ ~`) matched the client's.

## 11. Frame-by-frame video capture (virtual game time)  [verified, one machine]
- **The game reads `performance.now()`** for its timer (about 280 reads/s); `Date.now()` was read **0** times in
  3 s. Replacing `performance.now` with a clock the capture script controls (`gl-gate.js`, `__vt`) is enough.
- **Client time follows the virtual clock exactly**: real clock 3 s -> +60 client ticks (20 TPS); virtual clock
  held 3 s of wall time -> **+0** ticks; advancing 1.000 virtual second in **15, 30 or 60 steps -> +20 ticks each
  time**. So client-side animation (clouds, water/lava textures, particles, client ticks) advances per virtual
  second regardless of how many frames are drawn. In a 3-virtual-second check the sky (clouds) changed 1.44%
  and the terrain 0.00%. Holding the clock for 20 s of wall time caused no disconnect/timeout line; releasing it
  gave +55 ticks in 3 s (back to ~20 TPS).
- **Limits**: the integrated server runs in a Worker with its own real clock and is NOT virtualised. Mobs,
  world time and weather are server-driven, so freeze them (`freezeWorld`) - and run it again after `warmPath`:
  chunks generated later bring new animals (sheep appeared on far hills in the test clip). The game timer caps
  catch-up at 10 ticks per frame, so advance the clock in small steps (one `vtStep` per video frame) rather than jumping.
- **Server acceptance of camera moves** is judged per client packet and client ticks only run when the clock
  advances, so `captureVideoFrames` refuses paths that move more than 4 blocks per frame.
- **Test clip (plain, no PBR)**: seed `eagler`, 1280x720, noon, clear, HUD hidden, quarter orbit (about 39 blocks,
  ~13 blocks/s) around a point 25 blocks ahead of [100.5, 100, 200.5], **90 frames at 30 fps = 3.000 s**
  (ffmpeg libx264 crf 16, yuv420p; 4.76 MB). Capture took **326 s = 3.6 s/frame** (median 3.4 s, max 6.2 s),
  0 pose mismatches, 0 disconnect lines. Consecutive frames differ in 15.9% of pixels on average (min 14.6, max 16.9;
  terrain-only 28.6%) with **no outlier frame**, i.e. no flicker or terrain popping; that difference is the
  camera turning about 1 degree per frame.
- **PBR estimate (4 frames only)**: 208 s for 4 frames = **52 s/frame mean** (median 65 s, max 70 s); pose mismatches
  0; consecutive-frame difference 13.7% (terrain 24.9%), no outlier. Extrapolation: 30 frames (1 s) ~ 26-32 min,
  90 frames (3 s) ~ 1.5-1.8 h. Small sample; the warm-up pass under PBR took 90 s and never reported quiet.
- Everything here is software GL (SwiftShader). Playback speed is set by the chosen fps, not by the real game.
