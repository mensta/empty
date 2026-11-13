#!/usr/bin/env node
// G4: make a PATCHED COPY of an Eaglercraft single-file HTML that exposes `window.__eagMC()`
// (the Minecraft singleton). The original is never modified; the copy must live outside the repo
// (it contains Mojang assets).
//
//   node patch-hook.js <original.html> <output-copy.html>
//
// How the singleton is found (no hard-coded minified names):
//   1. TeaVM entry:  `$rt_exports.main=$rt_mainStarter(<entry>);`   -> insertion point
//   2. string pool alias:  `var <C>=$rt_s;`  and the pool array `$rt_stringPool([...])`
//   3. index of the log string "Setting user: " (logged by the Minecraft constructor)
//   4. the function that uses `<C>(<index>)` is the constructor; inside it, `<X>=a;` (a = this) is the
//      static assignment `theMinecraft = this`.
// Fails loudly (exit 1) if any step is ambiguous, instead of guessing.
'use strict';
const fs = require('fs');
const crypto = require('crypto');

const [src, dst] = process.argv.slice(2);
if (!src || !dst) { console.error('usage: node patch-hook.js <original.html> <output-copy.html>'); process.exit(2); }
if (fs.realpathSync(src) === (fs.existsSync(dst) ? fs.realpathSync(dst) : '')) { console.error('refusing to overwrite the original'); process.exit(2); }

const html = fs.readFileSync(src, 'latin1');         // byte-preserving round trip
const sha = crypto.createHash('sha256').update(fs.readFileSync(src)).digest('hex');
const fail = (m) => { console.error('patch-hook: ' + m); process.exit(1); };

// 1. insertion point
const entryRe = /\$rt_exports\.main=\$rt_mainStarter\((\w+)\);/g;
const entries = [...html.matchAll(entryRe)];
if (entries.length !== 1) fail(`expected exactly one "$rt_exports.main=$rt_mainStarter(...)" , found ${entries.length}`);
const entry = entries[0];

// 2. string pool alias + array
const alias = /var (\w+)=\$rt_s;/.exec(html);
if (!alias) fail('could not find the "var X=$rt_s;" string-pool alias');
const poolAt = html.indexOf('$rt_stringPool([', entry.index - 3000000 > 0 ? 0 : 0);
let starts = []; for (let i = html.indexOf('$rt_stringPool(['); i >= 0; i = html.indexOf('$rt_stringPool([', i + 1)) starts.push(i);
if (!starts.length) fail('could not find the $rt_stringPool([...]) call');
const s0 = starts[starts.length - 1] + '$rt_stringPool('.length;   // the real call is the last textual occurrence
let depth = 0, i = s0, inStr = false, q = '';
for (; i < html.length; i++) {
  const c = html[i];
  if (inStr) { if (c === '\\') i++; else if (c === q) inStr = false; continue; }
  if (c === '"' || c === "'") { inStr = true; q = c; continue; }
  if (c === '[') depth++; else if (c === ']') { depth--; if (depth === 0) { i++; break; } }
}
let pool;
try { pool = (0, eval)(html.slice(s0, i)); } catch (e) { fail('pool array did not evaluate: ' + e.message); }
if (!Array.isArray(pool)) fail('pool is not an array');

// 3. index of the constructor's log string
const idx = pool.indexOf('Setting user: ');
if (idx < 0) fail('log string "Setting user: " not in pool');
if (pool.indexOf('Setting user: ', idx + 1) >= 0) fail('"Setting user: " appears twice in pool');

// 4. constructor function and its static `X=a;`
const useRe = new RegExp(`\\b${alias[1]}\\(${idx}\\)`, 'g');
const uses = [...html.matchAll(useRe)];
if (uses.length !== 1) fail(`expected exactly one use of ${alias[1]}(${idx}), found ${uses.length}`);
const fnStart = html.lastIndexOf('function ', uses[0].index);
const fnEnd = html.indexOf('\nfunction ', uses[0].index);
const body = html.slice(fnStart, fnEnd);
const params = /^function \w+\((\w+)/.exec(body);
if (!params) fail('could not read constructor parameters');
const self = params[1];
const assigns = [...body.matchAll(new RegExp(`(?<![\\w.$])([A-Za-z_$][\\w$]*)=${self};`, 'g'))].map((m) => m[1]);
const uniq = [...new Set(assigns)];
if (uniq.length !== 1) fail(`expected one static "X=${self};" in the constructor, found [${uniq.join(',')}]`);
const staticName = uniq[0];

const hook = `$rt_globals.__eagMC=function(){return ${staticName};};`;
const out = html.slice(0, entry.index) + hook + html.slice(entry.index);
fs.writeFileSync(dst, out, 'latin1');
console.log(JSON.stringify({ ok: true, sha256_original: sha, entry: entry[1], poolStrings: pool.length, poolIndex: idx,
  constructorFn: body.slice(9, body.indexOf('(')), staticSingleton: staticName, inserted: hook, bytes_added: hook.length }));
