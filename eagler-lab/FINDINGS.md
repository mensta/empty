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
  The bits are decided in two places (read from the code, section 12): attribute bits from the vertex
  format being drawn, state bits computed on demand from current GL state.
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
- Remaining in the GL layer: exactly where bit 512 (anisotropic fix) is set (not by the state function; never seen in our runs), and the immediate-mode path.
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

## 12. Inside the GL emulation layer and the platform layer  [verified by reading `main.js`; names minified]
**How a draw call becomes a shader variant (R4, closed except bit 512).**
- A draw (minified `FEW(listId)`, a `glCallList`-style call) builds `key = formatBits | Grn()`:
  * **bits 1/2/4/8 = vertex attributes present in the recorded vertex format**: texcoord, colour, normal,
    lightmap (`format.rE & 1 -> attribute 1`, `& 2 -> 2`, `& 4`, `& 8`).
  * **`Grn()` = state bits, computed on every call from current GL state**: 16 = texture unit 0 enabled,
    32 = texture unit 1 (lightmap) enabled, 64 = alpha test, 128 = lighting enabled and the MC light state,
    256 = texture unit 0 enabled and texgen, 1024 = fog enabled and density > 0, 2048 = additive colour blend.
- `key` indexes a **flat array cache of 4096 entries**; a miss calls the compiler `C3n(key, ...)` (section 4) and stores the
  program. With the deferred (PBR) pipeline a second function (`Gv$`) keeps a cache keyed by
  `key & (15 | extensionStateMask)` plus the extension state, so bits that cannot matter for a given
  extension state do not create duplicate variants. The game logs this as
  `Compiling program for core state: <bits> , ext state: <bits>` (`DeferredGBufferPipelineCompiler`).
- Bit 512 (`ENABLE_ANISOTROPIC_FIX`) is **not** produced by `Grn()` and was never seen in any run; the shader comment
  says it works around Direct3D 11 + nearest filtering + anisotropy. Hypothesis (unverified): it is only set on a D3D backend.

**It re-implements legacy OpenGL semantics in Java over WebGL (R5, graphics part).**
- Display lists: `glNewList` accepts only `GL_COMPILE` (4864), one list at a time ("A display list is already being
  compiled you eagler!"), one vertex format and one draw mode per list, no re-rendering of the same vertices while
  recording; calling or flushing an unknown list is an error. Immediate mode exists as an `IMMEDIATE` draw path.
- Only a subset of GL is honoured, with explicit complaints otherwise: `glGetInteger` only for `GL_VIEWPORT`, `glFog`
  only `GL_FOG_COLOR`. "Skipping draw call with emulated VAO because no known VAO is bound!" - vertex array objects
  have three paths: WebGL2 `bindVertexArray`, the `OES_vertex_array_object` extension, or a fully emulated VAO.
- WebGL1 (GLES 2.00) and WebGL2 (GLES 3.00) share shader source through the `EAGLER_*` macros (`gles2_compat.glsl`).

**Platform layer (R5, non-graphics part): DOM APIs used directly; no LWJGL classes in this build.**
Counts are references in the generated JS:
| area | APIs referenced |
|---|---|
| input | keydown 7, keyup 5, mousedown/up 2, mousemove 2, wheel 2, pointer lock (`requestPointerLock` 5, `pointerlockchange`), touch (5), Gamepad (`getGamepads` 5), fullscreen, clipboard, plus a keyboard-layout query ("Loading keyboard layout data", "KeyboardLayoutMap remapped N keys") and a focus guard ("Detected mouse input while the window was not focused...") |
| audio | Web Audio: `AudioContext` 3, `createBufferSource` 3, `createPanner` 2, `createGain` 8, `decodeAudioData` 2; microphone `getUserMedia` 5 (voice) |
| storage | IndexedDB (`indexedDB` 11, `createObjectStore` 3, `openCursor` 2) and `localStorage` 19 |
| network | `WebSocket` 4, `RTCPeerConnection` 6 + `createDataChannel` 2 (peer-to-peer), `fetch` 12, `XMLHttpRequest` 5 |
| time / yield | `performance.now` **2 call sites**, `requestAnimationFrame` 2, `MessageChannel` 11, `postMessage` 25, `setTimeout` 63 |
| media | `MediaRecorder` 5 / `captureStream` 3 (screen recording), `createObjectURL` 7 |
- The strings `LWJGL` and `LWJGL3` are only (a) a crash-report "System Details" label and (b) a platform-enum value next to
  `DESKTOP`/`CHROME`/`EDGE`/`IE`: the code base has a desktop LWJGL3 backend as well as the browser one, selected through a
  platform abstraction. The research claim "LWJGL was rewritten for WebGL" is therefore **not what this build shows**: the
  browser build replaces LWJGL with its own platform classes + the GL emulation above. Whether those classes mimic
  LWJGL's API shapes cannot be told here (class names are stripped, no `org.lwjgl` string).
- **Threads**: the integrated server runs in a Web Worker started from a Blob URL (`WorkerMain: eaglercraftx worker thread
  is starting...`, CSP string `worker-src data: blob:`). TeaVM "yield" (section 5) is implemented with
  `MessageChannel` posts ("fast immediate continue") to dodge the browser's minimum `setTimeout` delay, with fallbacks to
  `window.postMessage` and `setTimeout` (log strings name each fallback). This is why a single JS thread can run
  Java-style blocking code.
- The two `performance.now` call sites match the virtual-clock result in section 11 (only that clock matters).

## 13. Startup, memory, browser storage, multiplayer plumbing, and what the project says about itself  [verified unless marked]
**Startup timeline (R8)** - one run, software GL, from the game's own timestamps (`raw-console.log`); first console line comes
~1.4 s after navigation (parsing/compiling the 35 MB page).
| step | time since first game log line |
|---|---|
| runtime init -> canvas -> WebGL context | +0.20 s -> +0.21 s -> +0.25 s |
| embedded EPK taken out of the data URI | +0.42 s; the next log line (decompress) at +1.60 s, i.e. **~1.2 s** for the base64 -> bytes step |
| pack unpacked, **4872 resources** loaded | +2.03 s |
| filesystem, sound engine, platform ready | +2.09 s, +2.09 s, +2.18 s |
| client thread started, user set | +2.35 s |
| resource-manager reload -> texture atlas created | +4.03 s -> +8.30 s (the 4.3 s includes software-GL texture work) |
(The integrated-server boot line comes ~35 s later in that log only because the script was clicking through menus.)
**JS heap** (Chromium `Performance.getMetrics`): **363 MB** right after load, **113 MB** at the title screen (the 35 MB page
string and the decoded pack are freed), **149 MB** in a freshly created world. DOM nodes 1622 -> 203.

**Where saves live (R10).** Two IndexedDB databases named `_net_lax1dude_eaglercraft_v1_8_internal_PlatformFilesystem_1_8_8_worlds`
and `..._resourcePacks`; each has ONE object store `filesystem` with key path `path`. A virtual file system: after creating one
world the `worlds` store held **90 entries, ~339 KB**; `resourcePacks` was empty. `localStorage` holds three keys
(`_eaglercraftX.g`, `_eaglercraftX.relays`, `_eaglercraftX.p`; by name: settings, relay list, profile - contents not read).
Browser quota reported 4.3 GB, usage 0.5 MB. The launch option `worldsDB` names the database; `ramdiskMode` (see below) would keep it in memory.

**Launch options (the page may set `window.eaglercraftXOpts`)** - ~45 keys are read, among them `container`, `worldsDB`,
`relays`, `joinServer`, `joinWorld`, `joinWorldRelay`, `demoMode`, `lang`, `allowVoiceClient`, `singleThreadMode` (no worker),
`ramdiskMode`, `eaglerNoDelay`, `forceWebGL1`, `forceWebGL2`, `allowExperimentalWebGL1`, `useWebGLExt`, `useJOrbisAudioDecoder`,
`useXHRFetch`, `deobfStackTraces`, `checkGLErrors`, `checkShaderGLErrors`, `showBootMenuOnLaunch`, `allowBootMenu`,
`enableEPKVersionCheck`, `localStorageNamespace`. This build sets only `container`, `worldsDB` and one relay.

**Multiplayer plumbing (R6, static only - no third-party server was contacted).** The launch options list one shared-world relay
(`wss://relay.eaglercraft.net/`, "Eaglercraft Shared World Relay"; `Default Relay #`, `checkRelaysForUpdates`). Strings show the
peer-to-peer LAN-world path (`eagler-p2p-lan:`, `/lan/join`, `lanServer.relayDisconnected`, "This is an EaglercraftX 1.8 LAN
world!") on top of `RTCPeerConnection`/`createDataChannel`; direct servers use `ws://`/`wss://` plus a server-side proxy plugin
(names present: `EaglercraftXBungee`, `EaglercraftXVelocity`, "upgrade to EaglercraftXServer"). Not exercised: the actual
handshake, the relay protocol, or voice.

**Audio (R12, partly).** 537 `.ogg` effects in the pack (no music), Web Audio nodes (BufferSource, Panner, Gain,
`decodeAudioData`), and a Java Ogg decoder (JOrbis) selected by `useJOrbisAudioDecoder` / used "in browsers that don't
support OGG" (per the project's credits).

**What the project says about itself (primary: `assets/eagler/CREDITS.txt` inside the build, 979 lines)** - quoted from its
own text; these are the authors' statements, not independently checked.
- *lax1dude*: "Creator of Eaglercraft; Ported the Minecraft 1.8 src to TeaVM; Optimized the Minecraft 1.8 src; **Made the platform
  abstraction layer; Made HW accelerated OpenGL 1.3 emulator**; Made the default shader pack; Made the integrated PBR resource
  pack; Added touch and mobile device support; Made the multiplayer backends; Made the shared world relay server; Made the patch
  and build system". *ayunami2000*: bug fixes, WebRTC shared worlds, WebRTC voice chat, touch support, velocity plugin, resource
  packs, screen recording, seamless fullscreen, "Created the replit". *cire3*: Gradle plugin, Kotlin DSL.
- **LWJGL 3 is listed as "OpenGL, OpenAL, and GLFW bindings in desktop debug runtime"** (and ANGLE as "OpenGL ES 3.0 emulation in
  desktop debug runtime"): it is a desktop development aid, not what the browser build runs on. This settles R5: the browser build
  uses the project's own platform abstraction layer + its OpenGL 1.3 emulator; the research claim "LWJGL was rewritten for
  WebGL" is not what the project itself says.
- **34 third-party projects are listed**, e.g. TeaVM ("Compiling Java to JS, JRE implementation"), JOML (renderer maths),
  NVIDIA FXAA, Alfheim (lighting engine), Netty (`ByteBuf` classes for the 1.8 networking), Bouncy Castle (MD5/SHA/AES), JZlib
  (deflate/gzip), a debloated ICU4J (Arabic/Hebrew reordering), JOrbis, fix-webm-duration (screen recordings), Emscripten and XZ
  (the WASM runtime's loader/decompression), Google Guava and Apache Commons (Minecraft 1.8 dependencies).
- **OptiFine (1.8.9_HD_U_M6): "A few, limited portions we 'borrowed' without the author's permission"** - the project's own wording.
- The credits text never uses the word "Mojang" (0 occurrences; "Minecraft" 5). It contains no licence or permission
  statement from Mojang/Microsoft.
- `EPKVersionIdentifier.txt` in the pack contains `u53`, i.e. the "u53" in "EaglercraftX 1.8-u53" is the pack's update number.

## 14. The WASM-GC build compared with the JS build (R11)  [verified for structure; performance inconclusive]
Official offline zips from the same page: `eaglercraft1-8-62da5f39.zip` (JS) and `eaglercraft1-8-wasm-62da5f39.zip` (WASM-GC).
**Structure**
| | JS build | WASM-GC build |
|---|---|---|
| zip | 13.55 MB | 12.66 MB |
| HTML | 34.9 MB (JS program 22.6 MB as text + 12.27 M base64 chars of EPK) | **16.8 MB** (one 16.75 M-char base64 blob + a 7.9 KB loader script) |
| game code | TeaVM-generated JavaScript, minified names | **14.46 MB WebAssembly (WasmGC) module**, stored XZ-compressed as 2.26 MB |
| assets | EPK 9,202,347 B, 4872 entries | **EPK 9,202,347 B, same size** |
| debug info | string pool without field names; no symbol map in the file | **5.34 MB TeaVM debug-info blob (`tdbg`, `classes.wasm.teadbg`)** with class and method names (`Minecraft`, `getMinecraft`, `MinecraftServer`, `launchIntegratedServer`, `EntityPlayerSP`, `GlStateManager`...); **no field names** (`thePlayer`, `posX`: 0 hits); package names stored as separate parts |
- The WASM-GC page carries an **"EPW" bundle** (magic `EAG$WASM`, 12,565,525 B): an uncompressed Emscripten-built loader WASM
  (~47 KB), then XZ sections: an HTML page (327 KB), JS glue `eagruntime.js` (110 KB), the game WASM (14.5 MB), the TeaVM debug blob
  (5.3 MB), a 37 KB helper WASM, and the EPK. The loader logs each step: "Checking primary CRC32 checksum", "Copying non-compressed segments",
  "Decompressing eagruntime.js / classes.wasm / classes.wasm.teadbg / deobfuscator / assets EPK", "Loading EaglercraftX WASM GC binary...",
  "WebAssembly direct memory resized to 32.56 MiB". (Matches the credits: Emscripten for the loader, XZ for the runtime.)
- So the two builds share the same assets and the same Java game code; they differ in the TeaVM target (JS vs WasmGC) and the packaging.

**Startup (software GL, one run each, ms since navigation)** - JS: first log line 1480, WebGL context 1820, assets loaded 3879,
user set 4195, resource reload 5944, texture atlas 9845. WASM-GC: first log line **498**, WebGL context 1591, assets loaded **2183**, user set 2317,
resource reload 3109, texture atlas **5867**. WASM-GC reaches the texture atlas about **4 s sooner** (page parse is lighter: 16.8 MB vs 34.9 MB).

**Not conclusive (do not state as fact)**
- *In-game speed*: the game's own F3 counter read **18 / 21 / 19 fps** (JS, three reads) and **8 / 36 / 44 fps** (WASM-GC, rising over ~1.5 min);
  `clear` calls per second were 47-49 (JS, stable) vs 75 -> 63 -> 51 (WASM-GC, falling). The two signals disagree for WASM-GC, there is one run per
  build, and a screenshot of the WASM-GC page took 28-34 s (a JS plain still takes ~2 s). Software GL dominates both. No claim that one is faster.
- *Memory*: JS heap 376 -> 114 -> 135 MB (load / title / world) vs 84 -> 83 -> 94 MB for WASM-GC; **not comparable**: WebAssembly linear
  memory (32.56 MiB+) is outside the JS heap metric.
- The hook, `setCamera` and the virtual clock were built for the JS build; the WASM-GC build has no JS-visible minified singleton to hook, so
  none of the capture tooling that needs `__eagMC` works on it (screenshots, `render()` and chat do).
- Both builds requested the same four WebGL extensions and compiled a similar number of shader programs (JS 28, WASM-GC 25 in this scene).

## 15. The integrated server really is a separate Web Worker (R16)  [verified in code and at run time]
Earlier sections (11, 12) stated this from log tags and strings (`IntegratedServer` thread name, "WorkerMain: ...", CSP `worker-src data: blob:`) and,
for the virtual clock, assumed the server would keep real time. Both are now checked directly:
- **Code**: the server-start function (minified `FDy`) contains `e = new $rt_globals.Worker($rt_ustr(url))`, stores it in a static, registers an
  `"error"` listener and an `onMessage` handler for the `"message"` event; the worker source is a Blob URL (`createObjectURL`). Messages travel through
  `postMessage` (25 references) / `message` listeners (15). The `FDy` branch for `singleThreadMode` skips the Worker (the launch option exists).
- **Run time** (Playwright, listeners attached before navigation, one run): **0 Workers before** creating a world, **1 after**, created at world creation,
  URL scheme `blob:`, global scope **`DedicatedWorkerGlobalScope`**, `typeof window === 'undefined'`, `importScripts` is a function: a real dedicated Web Worker
  with its own global scope, started from a Blob.
- **Clock independence**: with the page's `performance.now` held (section 11) for 20 s of wall time, the page clock moved **0 ms** and the Worker's
  `performance.now` moved **20,056 ms**; the server's game time (`/time query gametime`) went 1150 -> 1668, **+518 ticks in 25.9 s = 20.03 ticks/s
  across the pause**. So the server keeps real time and is not slowed by the virtual clock; the virtual clock only controls the client.
- **No network traffic in this scenario**: from page load through creating and playing a singleplayer world (including the paused-clock test) Playwright saw
  **0 HTTP requests** (excluding `file:`/`data:`/`blob:`) and **0 WebSockets**. The configured shared-world relay was not contacted (no shared world was
  opened). Limit: requests made by the Worker itself might not be listed by the page-level listener.
- **A second, dormant Worker exists in the code ("zeus cloud")**: a block near the end of `main.js` can start a Worker from an embedded script, but only if
  `window.eaglercraftXOpts.zeusCloud.endpoint` is a non-empty string; otherwise it sets `{"status":"disabled"}` and returns. This build's options do not set it:
  `window.__zeusCloud.state` was `{"status":"disabled"}` and no second Worker appeared. What the script would do with an endpoint (its messages are `init`,
  `token`, `cmd`, `state`, `result`) was not run or analysed.

## 16. Three checks against a secondary source: TeaVM version, multiplayer transport, world storage  [static, no third-party server contacted]
**1. TeaVM version - not stated anywhere in either build.**
- Searched both builds (JS `main.js`; every decompressed section of the WASM-GC bundle: page HTML, `eagruntime.js`, `classes.wasm`, TeaVM debug blob,
  helper WASM, loader WASM) for `EAGLER`, `0.9.x`-`0.19.x` style versions and "teavm version" text. **No version string exists.**
  `EAGLER` appears only in GLSL macros (`EAGLER_IS_GLES_300`, ...: 64 in the JS text, 20 in `classes.wasm`); "TeaVM" appears as class/method names
  (`TeaVMWebSocketClient`, `immediateContinueTeaVM0`, ...). The credits name TeaVM (Apache-2.0, "Copyright 2014 Alexey Andreev") with no version.
  The claim "JS 0.9.2-EAGLER / WASM 0.12.1-EAGLER" is therefore **not confirmable from the files**.
- The only hint is indirect, for the JS build: its runtime uses **13 helper names that exist in TeaVM 0.9.2's `runtime.js` but not in current master**
  (`$rt_intclsCache`, `$rt_createcls`, `$rt_assertNotNaN`, `$rt_createNumericArray`, `$rt_createArrayFromData`, ...). That fits an older generation (0.9.x-like).
  The raw match rates (0.9.2: 104/134 = 78%, master: 114/134 = 85%) are not comparable, because 0.9.2 emits the thread/string/exception helpers
  from the compiler instead of that file. Nothing comparable exists for the WASM-GC build (no JS helper layer to match).
**2. Multiplayer transport - what static reading supports.**
- **Direct servers = WebSocket.** `TeaVMWebSocketClient` calls `new WebSocket(url)`, sets `binaryType = "arraybuffer"`, listens for `open`/`close`/`message`/`error`
  and sends binary frames (`send(frame.data.buffer)`); `WebSocketNetworkManager` carries Minecraft packets over it. Vanilla 1.8 login classes are present
  (`C00Handshake`, `C00PacketLoginStart`, `S02PacketLoginSuccess`, `S03PacketEnableCompression`, `EnumConnectionState`; encryption classes
  `S01/C01` exist too, whether they are used was not checked). Connection log strings in order: "Connecting to: {}", "Could not open WebSocket to \"...\"",
  "Handshake timed out", "Logging in: {}", `connect.authorizing`, "Handshake Failure: Too Many Requests!". A status ping goes through `ServerQueryImpl`
  (`WebSocketQuery`, results `COMPATIBLE` / `CLIENT_OUTDATED`, with a rate limiter).
- **Eagler-specific packets (57 class names ending `EAG`)** for skins/capes (`CPacketGetOtherSkinV5EAG`, `SPacketOtherSkinCustomV5EAG`, ...), voice signalling
  (`CPacketVoiceSignalICEEAG`, `...DescEAG`, `...ConnectEAG`, `SPacketVoiceSignal*`), WebView, notification badges, server cookies
  (`SPacketSetServerCookieV4EAG`), redirects (`SPacketRedirectClientV4EAG`: "Recieved ..., reconnecting to: {}") and update certificates. Server-side proxy
  plugins are named in strings (`EaglercraftXBungee`, `EaglercraftXVelocity`, "upgrade to EaglercraftXServer").
- **Relay = a WebRTC signalling service.** Relay packet classes: `RelayPacket00Handshake`, `01ICEServers` (with `RelayServer`/`RelayType`), `02NewClient`,
  `03ICECandidate`, `04Description`, `05ClientSuccess`, `06ClientFailure`, `07LocalWorlds`, `69Pong`, `70SpecialUpdate`, `FEDisconnectClient`, `FFErrorCode`, plus
  `RelayManager`, `RelayServerSocket`, `RelayQuery` (with a rate limiter and a version-mismatch result). ICE candidates and session descriptions are what WebRTC
  peers exchange; the game data then travels on WebRTC data channels (`PlatformWebRTC$LANPeer`, `LANPeerEvent$LANPeerDataChannelEvent`/`DescriptionEvent`/
  `ICECandidateEvent`, `LANClientNetworkManager`). That the relay only introduces the peers is an inference from these names; the traffic was not observed. Voice uses
  the same signalling idea (`VoiceClientController`, microphone via `getUserMedia`). Two relay addresses are in the build: `wss://relay.eaglercraft.net/` (launch
  options) and `wss://relay.deev.is/` (a string in the program).
- **"Browsers have no raw TCP, so WebSocket"**: the build agrees in the sense that its only socket-like transports are WebSocket and WebRTC data channels (plus
  `fetch`/XHR); the statement about browsers having no raw TCP is a platform fact the build cannot show. **Not determinable by reading strings**: the bytes of the
  first handshake frame (they are numeric constants in code). Nothing was sent to any server.
**3. World storage - the secondary source is half right.**
- Worlds are stored in **IndexedDB** (`IndexedDBFilesystem`, `EaglerSaveFormat`, `EaglerSaveHandler`; section 13). **EPK is the export/import file format**, not
  the storage. Menus (from `en_US.lang` and the code): select-world **Backup** -> "World Backup Menu" with **Export EPK File** ("Download this world as a compressed
  .epk file"), **Convert to Vanilla** ("Download this world as a vanilla 1.8 world"), Duplicate World, Re-Create World (same seed), Delete Player Data; creating a world
  offers **Load EPK File** ("Load an Eaglercraft .epk world file") and **Import Vanilla World** ("Load a vanilla minecraft 1.8 world", reads `region/*.mca`, `DIM1/region/`).
- The same container carries a type tag: world EPKs are `epk/world188` and `epk/world152`, the asset/resource pack is `epk/resources`; the parser rejects other
  types ("EPK is not of file-type 'epk/resources'!") and checks an end-of-file code (`:::YEE:>`), the `END$` object and the version identifier (`u53`). Code:
  `EPKCompiler`, `EPKDecompiler`, `EPKLoader`, `GuiScreenBackupWorldSelection`, `GuiScreenNameWorldImport`, `IPCPacket07ImportWorld`.
- Profile and settings can also be exported/imported (as EPK: "Could not compile EPK"); resource packs import from ZIP.
- **Also present, not exercised: cloud saves.** Class names `CloudSaves` with flows `OpenFlow`, `LinkFlow`, `DownloadFlow`, `HistoryFlow`, `TrashFlow`, `DeleteFlow`,
  `MenuFlow` and a `Transport`. It has no endpoint in this build (the dormant `zeus cloud` worker, section 15, is the likely transport - an inference from
  the names, not tested).
