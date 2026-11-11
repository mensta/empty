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
})();
