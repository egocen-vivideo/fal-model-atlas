"""Fetch fal catalogs for image + audio generation categories.
Writes all_image_models.json / all_audio_models.json in the current dir."""
import json, urllib.request

def fetch(url):
    return json.load(urllib.request.urlopen(
        urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60))

for name, cats in [('image', ['text-to-image', 'image-to-image']),
                   ('audio', ['text-to-audio', 'text-to-speech', 'audio-to-audio', 'speech-to-speech'])]:
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
    json.dump(items, open(f'all_{name}_models.json', 'w'), indent=1)
    print(name, len(items), 'unique endpoints')
