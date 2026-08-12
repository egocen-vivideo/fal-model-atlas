"""Step 8 — emit the static site.

Reads final.json, writes a compact payload (family verdicts are stored once and
referenced by key, which keeps the page ~170 KB rather than ~400 KB), then
inlines head.html + body.html + app.js into a single self-contained index.html.

Writes: ../index.html, ../data/payload.json, ../data/models.json,
        ../data/fal_video_models.csv
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

CSV_COLUMNS = [
    ('id', 'Endpoint'), ('family_key', 'Family'), ('lab', 'Lab'), ('category', 'Type'),
    ('usd_per_min_720p', 'USD/min @720p'), ('price_basis', 'Price basis'),
    ('f_maxframes', 'Max frames'), ('f_duration', 'Duration options'),
    ('f_quality', 'Quality options'), ('f_aspect', 'Aspect ratios'), ('f_audio', 'Audio?'),
    ('f_start', 'Start frame?'), ('f_end', 'End frame?'), ('f_multicut', 'Multi-cut?'),
    ('f_lipsync', 'Lipsync?'), ('f_strong', 'Strongest side'), ('f_weak', 'Weakest side'),
]


def build_payload(rows):
    fams = {}
    for r in rows:
        fams.setdefault(r['family_key'], [r['f_strong'], r['f_weak']])
    compact = [{
        'i': r['id'], 'f': r['family_key'], 'l': r['lab'] or '—',
        'c': 'ref' if r['is_ref'] else ('t2v' if r['category'] == 'text-to-video' else 'i2v'),
        'p': r['usd_per_min_720p'], 'pb': r['price_basis'],
        'mf': r['f_maxframes'], 'd': r['f_duration'], 'q': r['f_quality'], 'a': r['f_aspect'],
        'au': r['f_audio'], 's': r['f_start'], 'e': r['f_end'], 'm': r['f_multicut'],
        'ls': r['f_lipsync'], 'ds': r['desc'][:200],
    } for r in rows]
    return {'rows': compact, 'fams': fams}


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
    # default to ./final.json (pipeline output in the scratch dir), else the
    # committed copy, else an explicit path argument
    src = sys.argv[1] if len(sys.argv) > 1 else (
        'final.json' if os.path.exists('final.json')
        else os.path.join(ROOT, 'data', 'models.json'))
    print('reading', src)
    rows = json.load(open(src))
    payload = build_payload(rows)

    with open(os.path.join(ROOT, 'data', 'payload.json'), 'w') as f:
        json.dump(payload, f, separators=(',', ':'))
    with open(os.path.join(ROOT, 'data', 'models.json'), 'w') as f:
        json.dump(rows, f, indent=1)

    with open(os.path.join(ROOT, 'data', 'fal_video_models.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow([c[1] for c in CSV_COLUMNS])
        for r in sorted(rows, key=lambda x: (x['family_key'], x['id'])):
            w.writerow([r.get(c[0]) for c in CSV_COLUMNS])

    js = open(os.path.join(HERE, 'app.js')).read().replace(
        '__PAYLOAD__', json.dumps(payload, separators=(',', ':')))
    doc = HTML_SHELL.format(
        head=open(os.path.join(HERE, 'head.html')).read(),
        body=open(os.path.join(HERE, 'body.html')).read(),
        js=js,
    )
    out = os.path.join(ROOT, 'index.html')
    with open(out, 'w') as f:
        f.write(doc)
    print('wrote index.html — %d KB, %d endpoints' % (os.path.getsize(out) // 1024, len(rows)))


if __name__ == '__main__':
    main()
