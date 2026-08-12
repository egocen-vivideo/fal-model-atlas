"""Step 1 — pull every video endpoint from fal's model index.

fal's /api/models endpoint caps page_size at 40, so every category is paginated
to exhaustion. The three video categories overlap (a reference-to-video model is
filed under image-to-video), so results are de-duplicated by endpoint id.

Writes: all_video_models.json  { endpoint_id: model_record }
"""
import json
import urllib.request

CATEGORIES = ['text-to-video', 'image-to-video', 'video-to-video']
UA = {'User-Agent': 'Mozilla/5.0'}


def fetch(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))


def main():
    all_items = {}
    for cat in CATEGORIES:
        page = 1
        while True:
            d = fetch(f'https://fal.ai/api/models?categories={cat}&page_size=40&page={page}')
            for it in d['items']:
                all_items.setdefault(it['id'], it)
            print(f'{cat} page {page}/{d["pages"]} (total {d["total"]})')
            if page >= d['pages']:
                break
            page += 1

    with open('all_video_models.json', 'w') as f:
        json.dump(all_items, f, indent=1)
    print('unique endpoints:', len(all_items))


if __name__ == '__main__':
    main()
