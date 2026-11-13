# eagler-lab — driving and analysing a local Eaglercraft 1.8.8 build

Scripts only. **Nothing here contains game assets or a downloaded build** (they include Mojang's
material): keep the build, patched copy, extracted pack, screenshots and footage outside git.
Findings are in `FINDINGS.md`; history/takedown notes in `HISTORY.md`.

## Setup (all paths outside the repo)
```bash
# 1. get the official offline zip from the project's download page into an EMPTY directory and unzip it
# 2. make a patched COPY that exposes window.__eagMC (the original is never modified)
node patch-hook.js /path/to/eaglercraft1-8.html /path/to/work/eagler-hooked.html
# 3. (optional) split the build and catalogue the pack; add --shaders to also write only the shader sources
python3 -I extract-build.py /path/to/eaglercraft1-8.html /path/to/work/build --shaders
# 4. run any script
EAGLER_HTML=/path/to/work/eagler-hooked.html EAGLER_SHOTS=/path/to/work/shots node capture-demo.js
```
Needs Node + Playwright with the preinstalled Chromium (software GL / SwiftShader).
Env: `EAGLER_HTML` (patched copy), `EAGLER_SHOTS` (output dir), `EAGLER_LOG` (full console log file).

## API (`lib.js`, `launch()` returns these)
| function | what it does |
|---|---|
| `enterWorld(seed)` / `skipFirstRun()` | first-run screens -> create a cheat-enabled fixed-seed world (click coordinates are 1280x720 only; call `setResolution` afterwards) |
| `chat(cmd)` | type a chat command (~2 s each) |
| `freezeWorld({time, weather})` | spectator, no daylight cycle, no mob spawning, fixed time, clear weather, kill non-player entities |
| `getState()` / `setCamera(x,y,z,yaw,pitch)` | read/write player pose through the hooked singleton (build-specific field names) |
| `moveSafe(pose)` / `teleport(...)` | server-accepted moves (steps <= 2 blocks, >=2 client ticks between); `/tp` for big jumps |
| `render(on)` / `glStats()` | gate WebGL2 draw/clear/blit calls on or off (`gl-gate.js`) |
| `warmPath(pathFn, stops)` | visit the route once with drawing off so chunks stream in (see below) |
| `waitChunks()` | heuristic: no buffer uploads for a while. **Not sufficient alone** |
| `captureFrame(file, opts)` | open the gate, draw frames, shoot until two consecutive stills match, close the gate |
| `captureSequence(pathFn, n, dir, opts)` | stills along a camera path; resumable; writes `manifest.json` |
| `hideHud()` / `dismissHints()` / `setResolution(w,h)` | F1, remove the "Press E" toast, resize the viewport (1920x1080 tested) |
| `rawLogs` + `EAGLER_LOG` | every console line, never filtered, with ISO ms timestamp and ms since page start |
| `paths.orbit(...)`, `paths.line(a,b)` | camera-path helpers |

## Things that will bite you
- **Speed is not game speed.** Frames are drawn one at a time on software GL (~15 fps plain, ~1 fps with the
  PBR pack, a PBR screenshot can take 100+ s). Footage assembled from stills must not be presented as the
  real game's speed. Simulation still ticks at 20 TPS in real time.
- **Chunks stream in around the player only**, and JS world generation is slow. A still can look "stable"
  while distant terrain is missing. Always `warmPath` the route first, then capture.
- **PBR frames never become static** (clouds, temporal effects): compare terrain only, or accept drift.
- Position writes: small steps are accepted by the integrated server; 40+ block jumps are reverted.
- Field names (`D/J/E`, `bN/cR`, `dz`, ...) and the hook only fit the build with sha256
  `8d7b926f5488baba...` (EaglercraftX 1.8-u53 JS). `patch-hook.js` finds the singleton itself, but the
  field names must be re-derived for another build (see FINDINGS.md section 7).
- The headless page logs one harmless `NotAllowedError: A user gesture is required to request Pointer Lock`.
- Nothing here uploads anywhere. Where footage is stored is a decision for the project owner.
