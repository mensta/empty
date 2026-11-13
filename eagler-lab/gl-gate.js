// Injected into the page BEFORE any game script runs (page.addInitScript).
// Wraps WebGL2 command entry points so the GPU never receives draw work while
// window.__gl.on === false. Game logic / chunk meshing / networking keep running.
(() => {
  const gl2 = window.WebGL2RenderingContext;
  if (!gl2) return;
  const proto = gl2.prototype;
  const st = (window.__gl = {
    on: true,
    passed: 0,
    skipped: 0,
    frames: 0, // proxy: number of full clears attempted (~= frames the game tried to render)
    gated: [],
  });
  const DRAW = [
    'drawArrays', 'drawElements', 'drawArraysInstanced', 'drawElementsInstanced',
    'drawRangeElements', 'blitFramebuffer', 'clear', 'clearBufferfv', 'clearBufferfi',
    'clearBufferiv', 'clearBufferuiv',
  ];
  for (const name of DRAW) {
    const orig = proto[name];
    if (typeof orig !== 'function') continue;
    st.gated.push(name);
    proto[name] = function (...args) {
      if (name === 'clear') st.frames++;
      if (!st.on) { st.skipped++; return; }
      st.passed++;
      return orig.apply(this, args);
    };
  }
  st.reset = () => { st.passed = st.skipped = st.frames = 0; };

  // Shader-variant recording (R4): which #define sets the game compiles, and when.
  st.shaders = []; st.createdPrograms = 0; st.links = [];
  const oSrc = proto.shaderSource;
  proto.shaderSource = function (sh, src) {
    try {
      const flags = (String(src).match(/#define (?:COMPILE|STATE)_\w+/g) || []).map((s) => s.slice(8));
      st.shaders.push({ t: Math.round(performance.now()), n: String(src).length, flags,
        vertex: /EAGLER_IS_VERTEX_SHADER/.test(src), core: /u_modelviewProjMat4f|u_modelviewMat4f/.test(src) });
    } catch (e) { /* never break the game */ }
    return oSrc.apply(this, arguments);
  };
  const oCreate = proto.createProgram;
  proto.createProgram = function () { st.createdPrograms++; return oCreate.apply(this, arguments); };
  const oLink = proto.linkProgram;
  proto.linkProgram = function () { st.links.push(Math.round(performance.now())); return oLink.apply(this, arguments); };
})();
