// ローカル表示用の dash (Claude のアーティファクト実行環境の代わり)。
// ページ (artifact/index.html) が使う API だけを実装する: data / calc / draw / onData / colors。
// データは ../data/*.json を読む。読み込み後に、登録された描画関数をすべて実行する。
(function () {
  const DATA_DIR = "../data/";
  const FILES = { candidates: "candidates.json", plans: "plans.json", conditions: "conditions.json" };
  const store = {};    // 名前 -> データ (読み込み後)
  const status = {};   // 名前 -> "loading" | "ok" | "error"
  const drawers = {};  // 描画名 -> 関数 (data-draw="描画名" の要素に対して実行)
  const calcs = {};    // 名前 -> { inputs, fn } (読み込み後に計算)
  const listeners = [];
  let ready = false;

  const dash = {
    colors: ["#2f6f9f", "#b8692a"], // 0: 鉄筋コン, 1: 鉄骨・ALC
    data(name) {
      return { status: status[name] || "loading", data: store[name] || [] };
    },
    calc(name, spec) { calcs[name] = spec; },
    draw(name, fn) {
      if (fn) drawers[name] = fn;   // 登録のみ。読み込み前は描かない
      if (!ready || !drawers[name]) return;
      document.querySelectorAll(`[data-draw="${name}"]`).forEach((el) => drawers[name](el));
    },
    onData(cb) { listeners.push(cb); if (ready) cb(); },
  };
  window.dash = dash;

  function paintAll() {
    Object.keys(drawers).forEach((name) => dash.draw(name));
    listeners.forEach((cb) => cb());
  }

  function showError(message) {
    const card = document.getElementById("list") || document.body;
    const p = document.createElement("p");
    p.className = "lx-note";
    p.style.color = "var(--color-warn)";
    p.textContent = message;
    card.prepend(p);
  }

  async function load() {
    const failed = [];
    for (const [name, file] of Object.entries(FILES)) {
      try {
        if (window.RENTAL_DATA && name in window.RENTAL_DATA) {  // standalone build (scripts/publish_s3.py)
          store[name] = window.RENTAL_DATA[name];
          status[name] = "ok";
          continue;
        }
        const r = await fetch(DATA_DIR + file, { cache: "no-store" });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        store[name] = await r.json();
        status[name] = "ok";
      } catch (e) {
        console.error(name, e);
        status[name] = "error";
        store[name] = [];
        failed.push(file);
      }
    }
    for (const [name, c] of Object.entries(calcs)) {
      store[name] = c.fn(...c.inputs.map((i) => store[i] || []));
      status[name] = "ok";
    }
    ready = true;
    paintAll();
    if (failed.length) showError(`データを読めませんでした: ${failed.join(", ")} (data/ を確かめ、python -m http.server をリポジトリ直下で起動してください)`);
  }

  let resizeTimer = null;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => { if (ready) dash.draw("scatter"); }, 150);
  });
  window.addEventListener("load", load);
})();
