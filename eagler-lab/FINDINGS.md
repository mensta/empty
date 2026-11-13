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
  **No deferred/PBR flag was ever compiled** with default settings: the PBR pipeline described above
  exists in the pack but did not run in this session. (Not yet tested: enabling it in options.)
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
- WASM-GC build not compared. PBR pipeline not exercised (not compiled with default options). Textures/lang contents not inspected.

## 9. Legal/sensitivity note for the video
The build bundles Mojang's assets and the project's own site carries a DMCA page. Explaining the
structure is one thing; showing assets at length or pointing to a download is the riskier part.

## Reproduce
`EAGLER_HTML=<path to html> node eagler-lab/<script>.js` (needs Playwright + Chromium).
`python3 -I eagler-lab/parse-epk.py <decompressed-epk> <out.json>` lists the pack.
