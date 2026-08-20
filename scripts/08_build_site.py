"""Step 8 — emit the static site.

Reads final.json, writes a compact payload (family verdicts are stored once and
referenced by key, which keeps the page ~170 KB rather than ~400 KB), then
inlines head.html + body.html + app.js into a single self-contained index.html.

Writes: ../index.html, ../data/payload.json, ../data/models.json,
        ../data/fal_video_models.csv
"""
import csv
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

CSV_COLUMNS = [
    ('id', 'Endpoint'), ('family_key', 'Family'), ('lab', 'Lab'), ('category', 'Type'),
    ('usd_per_min_720p', 'USD/min @720p'), ('price_basis', 'Price basis'),
    ('f_maxframes', 'Max frames'), ('f_duration', 'Duration options'),
    ('f_quality', 'Quality options'), ('f_aspect', 'Aspect ratios'), ('f_audio', 'Audio?'),
    ('f_start', 'Start frame?'), ('f_end', 'End frame?'), ('f_multicut', 'Multi-cut?'),
    ('f_task', 'Task'), ('f_lipsync', 'Lipsync?'),
    ('f_strong', 'Strongest side'), ('f_weak', 'Weakest side'),
    ('f_use_strong', 'Strongest use-cases'), ('f_use_weak', 'Weakest use-cases'),
]


# --------------------------------------------------------------------------
# Filter tokens. The page filters by discrete checkbox values, so each row
# carries explicit token arrays: duration in whole seconds ('5s'), quality
# tiers ('720p'), normalised aspect ratios ('16:9'), plus one bucket per
# yes/no-ish column. Durations above 30 s collapse into '>30s' so the
# checkbox list stays scannable.
# --------------------------------------------------------------------------

def _add_sec(toks, v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return
    if v <= 0:
        return
    if v > 30:
        toks.add('>30s')
    else:
        toks.add(f'{max(1, int(round(v)))}s')


def _range_secs(toks, lo, hi):
    a = max(1, int(math.ceil(lo)))
    b = int(math.floor(hi))
    for v in range(a, min(b, 30) + 1):
        toks.add(f'{v}s')
    if hi > 30:
        toks.add('>30s')


def dur_tokens(r):
    toks = set()
    for x in r.get('duration_enum') or []:
        s = str(x).strip().lower()
        if s == 'auto':
            toks.add('auto')
            continue
        m = re.fullmatch(r'([\d.]+)\s*s?', s)
        if m:
            _add_sec(toks, m.group(1))
    if toks:
        return sorted(toks)
    lo, hi = r.get('duration_min'), r.get('duration_max')
    if lo is not None and hi is not None:
        _range_secs(toks, float(lo), float(hi))
    if not toks:
        nlo, nhi = r.get('num_frames_min'), r.get('num_frames_max')
        fps = r.get('fps_default') or 24
        if nhi:
            _range_secs(toks, (nlo or 1) / fps, nhi / fps)
    if not toks:
        fd = re.sub(r'\([^)]*\)', ' ', (r.get('f_duration') or '')).lower()
        if re.search(r'follows|driven|derived|matches input', fd):
            toks.add('input-driven')
        else:
            m = re.search(r'up to\s*([\d.]+)', fd)
            if m:
                _range_secs(toks, 1, float(m.group(1)))
            else:
                for n in re.findall(r'[\d.]+', fd):
                    _add_sec(toks, n)
    if not toks and r.get('f_maxframes') and r.get('fps_default'):
        _add_sec(toks, r['f_maxframes'] / r['fps_default'])
    if not toks:
        toks.add('unspecified')
    return sorted(toks)


def qual_tokens(r):
    toks = set()
    for x in r.get('res_enum') or []:
        s = str(x).lower()
        if re.fullmatch(r'\d+x\d+', s):
            toks.add('other')
        elif re.fullmatch(r'(square|square_hd|portrait_\w+|landscape_\w+)', s):
            toks.add('preset')     # size presets, not quality tiers
        else:
            toks.add(s)
    if not toks:
        fq = (r.get('f_quality') or '').lower()
        if 'from docs' in fq:
            toks.update(re.findall(r'\b(?:\d{3,4}p|2k|4k)\b', fq))
        elif 'free width/height' in fq:
            toks.add('custom')
        elif 'preset' in fq:
            toks.add('preset')
        else:
            toks.add('fixed')
    return sorted(toks)


AR_MAP = {
    'square': '1:1', 'square_hd': '1:1',
    'portrait_4_3': '3:4', 'portrait_16_9': '9:16',
    'landscape_4_3': '4:3', 'landscape_16_9': '16:9',
    'horizontal': '16:9', 'vertical': '9:16',
}


def ar_tokens(r):
    toks = set()
    for x in r.get('ar_enum') or []:
        s = str(x).lower()
        toks.add(AR_MAP.get(s, s))
    if not toks:
        fa = (r.get('f_aspect') or '').lower()
        if 'free' in fa:
            toks.add('free')
        elif 'inherits' in fa:
            toks.add('inherits input')
        else:
            toks.add('fixed')
    return sorted(toks)


def dur_display(r):
    """Full duration option list — no truncation, no parentheses."""
    e = r.get('duration_enum')
    if e:
        vals = [str(x) for x in e]
        norm = [v[:-1] if re.fullmatch(r'[\d.]+s', v) else v for v in vals]
        if all(re.fullmatch(r'[\d.]+', v) or v == 'auto' for v in norm):
            return ', '.join(norm) + ' s'
        return ', '.join(vals)
    lo, hi = r.get('duration_min'), r.get('duration_max')
    if lo is not None or hi is not None:
        return f"{lo}–{hi} s continuous"
    nlo, nhi = r.get('num_frames_min'), r.get('num_frames_max')
    fps = r.get('fps_default') or 24
    if nhi:
        return f"{(nlo or 1) / fps:.1f}–{nhi / fps:.1f} s via num_frames"
    fd = (r.get('f_duration') or 'not exposed').replace('(', ' ').replace(')', ' ')
    return re.sub(r'\s+', ' ', fd).strip()


def _bucket(v, table):
    for prefix, tok in table:
        if (v or '').startswith(prefix):
            return tok
    return table[-1][1]


def build_payload(rows):
    fams = {}
    for r in rows:
        fams.setdefault(r['family_key'], [
            r['f_strong'], r['f_weak'],
            r.get('f_use_strong', ''), r.get('f_use_weak', '')])
    compact = [{
        'i': r['id'], 'f': r['family_key'], 'l': r['lab'] or '—',
        'c': ('v2v' if r['category'] == 'video-to-video'
              else 'ref' if r['is_ref']
              else 't2v' if r['category'] == 'text-to-video' else 'i2v'),
        'tk': r.get('f_task', 'generate'),
        'p': r['usd_per_min_720p'], 'pb': r['price_basis'],
        'mf': r['f_maxframes'],
        'd': dur_display(r),
        'q': ', '.join(str(x) for x in r['res_enum']) if r.get('res_enum') else r['f_quality'],
        'a': ', '.join(str(x) for x in r['ar_enum']) if r.get('ar_enum') else r['f_aspect'],
        'au': r['f_audio'], 's': r['f_start'], 'e': r['f_end'], 'm': r['f_multicut'],
        'ls': r['f_lipsync'], 'ds': r['desc'][:200],
        'dt': dur_tokens(r), 'qt': qual_tokens(r), 'at': ar_tokens(r),
        'auB': _bucket(r['f_audio'], [('Yes', 'yes'), ('Input', 'input'), ('', 'no')]),
        'sB': _bucket(r['f_start'], [('Yes', 'y'), ('', 'n')]),
        'eB': _bucket(r['f_end'], [('Yes', 'y'), ('', 'n')]),
        'mB': _bucket(r['f_multicut'], [('Yes', 'native'), ('Partial', 'keyframe'), ('', 'no')]),
        'lsB': _bucket(r['f_lipsync'], [('Yes', 'yes'), ('Partial', 'partial'), ('', 'no')]),
    } for r in rows]
    return {'rows': compact, 'fams': fams}



TABS = """<nav class="tabs" aria-label="Atlas sections">
<a href="./"{v}>Video <span class="n">332</span></a>
<a href="repurpose.html"{r}>Video repurpose <span class="n">199</span></a>
<a href="image.html"{i}>Image <span class="n">587</span></a>
<a href="audio.html"{a}>Audio <span class="n">126</span></a>
</nav>"""


def tabs(cur):
    m = {'v': '', 'r': '', 'i': '', 'a': ''}
    m[cur] = ' aria-current="page"'
    return TABS.format(**m)


PAGES = {
 'generate': {
   'file': 'index.html',
   'title': 'fal.ai Video Model Atlas',
   'h1': 'Every video generation model on fal.ai',
   'col2th': '<th data-sort="col2">Type</th>',
   'dek': ('All <b>332 endpoints</b> across text-to-video, image-to-video and reference-to-video '
           '&mdash; pulled from fal\'s live model index and each endpoint\'s published OpenAPI schema, '
           'with pricing normalised to <b>USD per minute of 720p output</b>. '
           'Editing, upscaling and lipsync tools live on the '
           '<a href="repurpose.html">Video repurpose</a> tab. '
           'Click any row for its strongest/weakest side and use-cases.'),
   'footer': """<p><b>Method.</b> Endpoint list from fal's model index (categories text-to-video + image-to-video, all pages). Duration, resolution, aspect-ratio, frame-count, audio and start/end-frame fields read from each endpoint's published <code>openapi.json</code>. Pricing from fal's own per-model pricing copy, normalised to a 60-second 720p render.</p>
  <p><b>Read $/min as a rate, not a shopping cart.</b> Most of these models cap out at 5&ndash;15 seconds, so a full minute is not a single generation &mdash; the column exists to make wildly different billing units (per second, per video, per megapixel, per 1000 tokens) comparable. Where a model bills per megapixel or per token, 720p at the endpoint's native frame rate is assumed. Audio-on tiers cost more; the figure shown is audio-off where the two differ.</p>
  <p><b>12 endpoints</b> are billed per GPU compute-second rather than per output, so no fixed rate exists &mdash; these are the legacy open models (SVD, AnimateDiff, SadTalker, MuseTalk, LivePortrait, T2V-Turbo and friends). <b>Max frames</b> is blank where output length simply follows the driving audio or video.</p>""",
 },
 'repurpose': {
   'file': 'repurpose.html',
   'title': 'fal.ai Video Repurpose Atlas',
   'h1': 'Every video repurposing model on fal.ai',
   'col2th': '<th data-sort="col2">Task</th>',
   'dek': ('All <b>199 video-to-video endpoints</b> &mdash; everything that takes finished footage '
           'and changes it: extend, edit and restyle, inpaint and erase, lipsync, upscale and restore, '
           'interpolate, generate matching audio, or analyse. Models that create video from scratch '
           'are on the <a href="./">Video</a> tab. Pricing is normalised to '
           '<b>USD per minute of footage processed at 720p</b>.'),
   'footer': """<p><b>Method.</b> Endpoint list from fal's model index (category video-to-video, all pages). Fields read from each endpoint's published <code>openapi.json</code>; pricing from fal's own copy, scraped from the model page where the metadata carries none.</p>
  <p><b>Read $/min as a processing rate.</b> Unlike the generation tab, this is the cost to run a minute of footage through the model, not the cost to create a minute. Per-frame billing (background removal, SAM) is converted at a 30&nbsp;fps reference. Upscalers whose lowest tier is 1080p are priced at that tier and flagged in the expanded row.</p>
  <p><b>16 endpoints</b> are billed per GPU compute-second and show as compute-billed. Many columns here describe the model's <em>output</em> envelope &mdash; for pure analysis and utility endpoints (SAM, depth, ffmpeg) several are simply not applicable.</p>""",
 },
}

HTML_SHELL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow, noarchive">
<meta name="description" content="Internal reference: every fal.ai video generation endpoint with normalised pricing and capability matrix.">
<meta name="theme-color" content="#FAFAFB" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0D0F13" media="(prefers-color-scheme: dark)">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Ctext y='13' font-size='13'%3E%F0%9F%8E%AC%3C/text%3E%3C/svg%3E">
{head}</head>
<body>
{body}
<script>
{js}
</script>
</body>
</html>
"""


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else (
        'final.json' if os.path.exists('final.json')
        else os.path.join(ROOT, 'data', 'models.json'))
    print('reading', src)
    all_rows = json.load(open(src))

    # one CSV for everything, Task column included
    with open(os.path.join(ROOT, 'data', 'fal_video_models.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow([c[1] for c in CSV_COLUMNS])
        for r in sorted(all_rows, key=lambda x: (x.get('f_task', 'generate'), x['family_key'], x['id'])):
            w.writerow([r.get(c[0]) for c in CSV_COLUMNS])
    with open(os.path.join(ROOT, 'data', 'models.json'), 'w') as f:
        json.dump(all_rows, f, indent=1)

    head_src = open(os.path.join(HERE, 'head.html')).read()
    body_src = open(os.path.join(HERE, 'body.html')).read()
    app_src = open(os.path.join(HERE, 'app.js')).read()

    for mode, tab_key in (('generate', 'v'), ('repurpose', 'r')):
        cfg = PAGES[mode]
        rows = [r for r in all_rows
                if (r.get('f_task', 'generate') == 'generate') == (mode == 'generate')]
        payload = build_payload(rows)
        if mode == 'generate':
            with open(os.path.join(ROOT, 'data', 'payload.json'), 'w') as f:
                json.dump(payload, f, separators=(',', ':'))

        head = head_src.replace('<title>fal.ai Video Model Atlas</title>',
                                f"<title>{cfg['title']}</title>")
        body = (body_src
                .replace('__EYEBROW__', 'fal.ai catalogue survey &middot; 20 Aug 2026')
                .replace('__H1__', cfg['h1'])
                .replace('__DEK__', cfg['dek'])
                .replace('__TABS__', tabs(tab_key))
                .replace('__COL2TH__', cfg['col2th'])
                .replace('__FOOTER__', '<footer><div class="wrap">' + cfg['footer'] + '</div></footer>'))
        js = (app_src
              .replace('__PAYLOAD__', json.dumps(payload, separators=(',', ':')))
              .replace('__MODE__', json.dumps(mode)))
        doc = HTML_SHELL.format(head=head, body=body, js=js)
        out = os.path.join(ROOT, cfg['file'])
        with open(out, 'w') as f:
            f.write(doc)
        print(f"wrote {cfg['file']} — {os.path.getsize(out)//1024} KB, {len(rows)} endpoints")


if __name__ == '__main__':
    main()
