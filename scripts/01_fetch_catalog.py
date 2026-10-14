"""Step 1 — pull every video endpoint from fal's model index.

fal's /api/models endpoint caps page_size at 40, so every category is paginated
to exhaustion. Results are de-duplicated by endpoint id.

Besides the three core video categories, fal files some video endpoints under
categories of their own (audio-to-video avatars and LTX audio-to-video,
video-to-audio foley, video-to-text understanding). Those are fetched too and
mapped onto the atlas's three categories so the rest of the pipeline treats
them uniformly; the original category is kept in `category_src`:

    audio-to-video            -> image-to-video  (generation tab)
    video-to-audio            -> video-to-video  (repurpose tab, task video->audio)
    video-to-text, vision*    -> video-to-video  (repurpose tab, task analysis)
    * vision only for endpoints whose id names video

Writes: all_video_models.json  { endpoint_id: model_record }
"""
import json
import re
import time
import urllib.request

CORE = ['text-to-video', 'image-to-video', 'video-to-video']
EXTRA = {'audio-to-video': 'image-to-video', 'video-to-audio': 'video-to-video',
         'video-to-text': 'video-to-video', 'vision': 'video-to-video'}
UA = {'User-Agent': 'Mozilla/5.0'}


def fetch(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60))


def main():
    all_items = {}
    for cat in CORE + list(EXTRA):
        page = 1
        while True:
            d = fetch(f'https://fal.ai/api/models?categories={cat}&page_size=40&page={page}')
            for it in d['items']:
                if cat == 'vision' and not re.search(r'video', it['id']):
                    continue
                if it['id'] in all_items:
                    continue
                it['category_src'] = it['category']
                it['category'] = EXTRA.get(it['category'], it['category'])
                all_items[it['id']] = it
            print(f'{cat} page {page}/{d["pages"]} (total {d["total"]})')
            if page >= d['pages']:
                break
            page += 1
            time.sleep(0.2)

    with open('all_video_models.json', 'w') as f:
        json.dump(all_items, f, indent=1)
    print('unique endpoints:', len(all_items))


if __name__ == '__main__':
    main()
