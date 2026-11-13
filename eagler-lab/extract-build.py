#!/usr/bin/env python3 -I
"""G5/G6: split an Eaglercraft single-file HTML into its three parts and catalogue the asset pack.

    python3 -I extract-build.py <build.html> <out-dir> [--shaders]

Outputs (all under <out-dir>, which MUST be outside the git repo - the pack holds Mojang assets):
  opts.js          the launch-options script (first <script>)
  main.js          the TeaVM-generated program (largest <script>)
  assets.epk       the EPK exactly as embedded (base64-decoded, still gzip inside)
  catalog.json     every entry: name, bytes, crc32 (verified), top folder
  catalog.txt      full per-folder totals that add up to the entry count and byte total
  parts.json       byte offsets/sizes of the three parts inside the HTML (for the "where is what" figure)
  shaders/         ONLY with --shaders: the .vsh/.fsh/.glsl sources (the project's own code; check licence first)

Deliberately NOT written: textures, sounds, models or any decompressed copy of the pack.
Treat the HTML as untrusted data: nothing from it is executed; Python is run with -I.
"""
import base64, collections, gzip, json, os, re, struct, sys, zlib


def die(msg):
    print('extract-build: ' + msg, file=sys.stderr)
    sys.exit(1)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    want_shaders = '--shaders' in sys.argv
    if len(args) != 2:
        die('usage: extract-build.py <build.html> <out-dir> [--shaders]')
    src, out = args
    out = os.path.abspath(out)
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.abspath(os.path.join(here, '..'))
    if out == repo or out.startswith(repo + os.sep):
        die('out-dir is inside the repo; choose a directory outside it (Mojang assets)')
    os.makedirs(out, exist_ok=True)

    raw = open(src, 'rb').read()
    html = raw.decode('latin-1')              # byte-preserving; offsets == byte offsets

    # --- three parts -------------------------------------------------------------------
    scripts = []
    for m in re.finditer(r'<script type="text/javascript">', html):
        end = html.find('</script>', m.end())
        scripts.append((m.end(), end))
    if len(scripts) < 3:
        die('expected >=3 <script> blocks, found %d' % len(scripts))
    scripts_by_size = sorted(scripts, key=lambda s: s[1] - s[0], reverse=True)
    main_js = scripts_by_size[0]
    opts = scripts[0]
    epk_block = [s for s in scripts if 'assetsURI' in html[s[0]:s[0] + 400]]
    if not epk_block:
        die('no script block assigns assetsURI (the embedded EPK)')
    epk_block = epk_block[0]
    open(os.path.join(out, 'opts.js'), 'w', encoding='utf-8').write(html[opts[0]:opts[1]])
    open(os.path.join(out, 'main.js'), 'w', encoding='utf-8').write(html[main_js[0]:main_js[1]])

    m = re.search(r'assetsURI = "data:application/octet-stream;base64,([A-Za-z0-9+/=]+)"', html[epk_block[0]:epk_block[1]])
    if not m:
        die('could not read the base64 EPK data URI')
    b64_start = epk_block[0] + m.start(1)
    b64_len = len(m.group(1))
    epk = base64.b64decode(m.group(1))
    open(os.path.join(out, 'assets.epk'), 'wb').write(epk)
    json.dump({
        'html_bytes': len(raw),
        'opts_script': {'start': opts[0], 'bytes': opts[1] - opts[0]},
        'main_js': {'start': main_js[0], 'bytes': main_js[1] - main_js[0]},
        'epk_base64': {'start': b64_start, 'chars': b64_len},
        'epk_decoded_bytes': len(epk),
    }, open(os.path.join(out, 'parts.json'), 'w'), indent=1)

    # --- EPK v2: 'EAGPKG$$' + ver string + filename + comment, then one gzip stream ------
    if not epk.startswith(b'EAGPKG$$'):
        die('not an EPK (bad magic)')
    gz = epk.find(b'\x1f\x8b\x08')
    if gz < 0:
        die('no gzip stream in EPK')
    d = zlib.decompressobj(31)
    blob = d.decompress(epk[gz:])               # kept in memory only
    if blob[:4] != b'HEAD':
        die('inner pack does not start with HEAD')
    p = 4
    p += 1 + blob[p]                            # header key
    p += 4 + struct.unpack('>I', blob[p:p + 4])[0]   # header value
    entries, bad = [], 0
    while p < len(blob) and blob[p:p + 5] == b'>FILE':
        p += 5
        nl = blob[p]
        name = blob[p + 1:p + 1 + nl].decode('utf-8', 'replace')
        q = p + 1 + nl
        ln = struct.unpack('>I', blob[q:q + 4])[0]
        crc = struct.unpack('>I', blob[q + 4:q + 8])[0]
        data = blob[q + 8:q + 4 + ln - 1]       # length = crc(4) + data + ':' terminator
        ok = (zlib.crc32(data) & 0xffffffff) == crc and blob[q + 4 + ln - 1:q + 4 + ln] == b':'
        bad += 0 if ok else 1
        entries.append({'name': name, 'bytes': len(data), 'crc32': '%08x' % crc,
                        'crc_ok': ok, 'off': q + 8})
        if want_shaders and name.endswith(('.vsh', '.fsh', '.glsl')):
            dst = os.path.join(out, 'shaders', name.replace('assets/eagler/glsl/', '', 1))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            open(dst, 'wb').write(data)
        p = q + 4 + ln
    if blob[p:p + 5] != b'>END$':
        die('pack did not end with >END$ at %d (got %r)' % (p, blob[p:p + 8]))

    # --- catalogue: full folder totals, no entry left out ----------------------------------
    def folder(n):
        parts = n.split('/')
        return '/'.join(parts[:3]) if n.startswith('assets/') and len(parts) > 3 else (parts[0] if len(parts) == 1 else '/'.join(parts[:-1]) or '.')
    tot = collections.defaultdict(lambda: [0, 0])
    for e in entries:
        e['folder'] = folder(e['name'])
        tot[e['folder']][0] += 1
        tot[e['folder']][1] += e['bytes']
    json.dump([{k: v for k, v in e.items() if k != 'off'} for e in entries], open(os.path.join(out, 'catalog.json'), 'w'))
    n_all = sum(v[0] for v in tot.values()); b_all = sum(v[1] for v in tot.values())
    assert n_all == len(entries)
    ext = collections.Counter(e['name'].rsplit('.', 1)[-1] if '.' in e['name'] else '(none)' for e in entries)
    with open(os.path.join(out, 'catalog.txt'), 'w') as f:
        f.write('entries: %d   data bytes: %d   crc mismatches: %d   decompressed pack: %d\n' % (len(entries), b_all, bad, len(blob)))
        f.write('\n%-44s %7s %12s\n' % ('folder', 'files', 'bytes'))
        for k, (n, b) in sorted(tot.items(), key=lambda x: -x[1][1]):
            f.write('%-44s %7d %12d\n' % (k, n, b))
        f.write('%-44s %7d %12d\n' % ('TOTAL', n_all, b_all))
        f.write('\nby extension: %s\n' % dict(ext.most_common()))
    print(open(os.path.join(out, 'catalog.txt')).read())
    print('wrote', out)
    if bad:
        die('%d entries failed CRC' % bad)


main()
