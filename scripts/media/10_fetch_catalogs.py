"""Fetch fal catalogs for image + audio generation categories.

Writes all_image_models.json / all_audio_models.json in the current dir.

Endpoints the atlas carried before (../../data/<name>_rows.json) that the index
no longer returns are re-checked against their model page, the same way
../09_unlisted.py does for video: if the page still carries the model record,
the endpoint is kept with `_unlisted: true` and its fal status (`unlisted`, or
`deprecated: true`); if the record is gone or marked removed, it is dropped and
listed in media_removed.json.
"""
import importlib.util
import json
import os
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
_spec = importlib.util.spec_from_file_location('unl', os.path.join(HERE, '..', '09_unlisted.py'))
unl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(unl)


def fetch(url):
    return json.load(urllib.request.urlopen(
        urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60))


CATS = [('image', ['text-to-image', 'image-to-image']),
        ('audio', ['text-to-audio', 'text-to-speech', 'audio-to-audio', 'speech-to-speech'])]

unl.PAGE_DIR = 'pages_recheck'
os.makedirs(unl.PAGE_DIR, exist_ok=True)
removed = {}
for name, cats in CATS:
    items = {}
    for cat in cats:
        page = 1
        while True:
            d = fetch(f'https://fal.ai/api/models?categories={cat}&page_size=40&page={page}')
            for it in d['items']:
                if it['id'] in items:
                    items[it['id']]['_cats'].append(cat)
                else:
                    it['_cats'] = [cat]
                    items[it['id']] = it
            if page >= d['pages']:
                break
            page += 1
            time.sleep(0.2)
    listed = len(items)

    prev_path = os.path.join(ROOT, 'data', f'{name}_rows.json')
    prev = {r['id']: r for r in json.load(open(prev_path))} if os.path.exists(prev_path) else {}
    removed[name] = []
    for eid in sorted(set(prev) - set(items)):
        page = unl.get_page(eid)
        rec = unl.page_record(eid, page) if page else None
        if not rec or rec.get('removed'):
            removed[name].append(eid)
            continue
        rec['_cats'] = prev[eid].get('cats') or [rec.get('category')]
        rec['_unlisted'] = True
        rec['_page_status'] = rec.get('status') or ''
        items[eid] = rec
    json.dump(items, open(f'all_{name}_models.json', 'w'), indent=1)
    print(name, listed, 'listed +', len(items) - listed, 'unlisted/deprecated kept,',
          len(removed[name]), 'removed')
json.dump(removed, open('media_removed.json', 'w'), indent=1)
