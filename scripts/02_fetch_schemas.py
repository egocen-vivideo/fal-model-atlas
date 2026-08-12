"""Step 2 — download each endpoint's published OpenAPI schema and model page.

The queue OpenAPI schema is the source of truth for duration / resolution /
aspect-ratio / frame-count / audio / start-end-frame parameters. A handful of
endpoints have no published schema (404) — those fall back to the model page.

Only text-to-video and image-to-video are kept; video-to-video was fetched in
step 1 purely to catch reference-to-video models filed under it.

Writes: oas/<escaped_id>.json  and  pages/<escaped_id>.html
        page_pricing.json  { endpoint_id: [pricing paragraphs] }
"""
import concurrent.futures as cf
import html
import json
import os
import re
import urllib.parse
import urllib.request

UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
OAS_DIR, PAGE_DIR = 'oas', 'pages'


def esc(eid):
    return eid.replace('/', '__')


def get_schema(eid):
    path = os.path.join(OAS_DIR, esc(eid) + '.json')
    if os.path.exists(path) and os.path.getsize(path) > 200:
        return eid, 'cached'
    url = 'https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=' + urllib.parse.quote(eid, safe='')
    try:
        raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
        json.loads(raw)
        with open(path, 'wb') as f:
            f.write(raw)
        return eid, 'ok'
    except Exception as e:
        return eid, 'ERR ' + str(e)[:60]


def get_page(eid):
    path = os.path.join(PAGE_DIR, esc(eid) + '.html')
    if os.path.exists(path) and os.path.getsize(path) > 50_000:
        return eid, 'cached'
    try:
        raw = urllib.request.urlopen(
            urllib.request.Request('https://fal.ai/models/' + eid, headers=UA), timeout=90).read()
        with open(path, 'wb') as f:
            f.write(raw)
        return eid, 'ok'
    except Exception as e:
        return eid, 'ERR ' + str(e)[:50]


def strip_html(s):
    s = re.sub(r'<!--.*?-->', '', s)
    s = re.sub(r'<[^>]+>', '', s)
    return html.unescape(re.sub(r'\s+', ' ', s)).strip()


def scrape_page_pricing():
    """fal renders pricing into the page even when the model metadata omits it."""
    out = {}
    for fn in os.listdir(PAGE_DIR):
        if not fn.endswith('.html'):
            continue
        eid = fn[:-5].replace('__', '/')
        text = open(os.path.join(PAGE_DIR, fn), encoding='utf-8', errors='ignore').read()
        seen, found = set(), []
        for m in re.finditer(r'<p>((?:(?!</p>).){0,900})</p>', text, re.S):
            s = strip_html(m.group(1))
            if '$' in s and re.search(r'(will cost|per second|charged|costs)', s, re.I):
                if s not in seen and len(s) > 12:
                    seen.add(s)
                    found.append(s)
        out[eid] = found[:4]
    with open('page_pricing.json', 'w') as f:
        json.dump(out, f, indent=1)
    return out


def main():
    os.makedirs(OAS_DIR, exist_ok=True)
    os.makedirs(PAGE_DIR, exist_ok=True)
    catalog = json.load(open('all_video_models.json'))
    ids = [k for k, v in catalog.items()
           if v['category'] in ('text-to-video', 'image-to-video')]
    print(f'{len(ids)} generation endpoints')

    with cf.ThreadPoolExecutor(12) as ex:
        for eid, status in ex.map(get_schema, ids):
            if status.startswith('ERR'):
                print(' schema miss:', eid, status)

    # model pages are only needed where fal's metadata carries no pricing copy
    need = [k for k in ids if not (catalog[k].get('pricingInfoOverride') or '').strip()]
    print(f'{len(need)} endpoints need page-scraped pricing')
    with cf.ThreadPoolExecutor(8) as ex:
        for eid, status in ex.map(get_page, need):
            if status.startswith('ERR'):
                print(' page miss:', eid, status)

    got = scrape_page_pricing()
    print('pages with pricing text:', sum(1 for v in got.values() if v))


if __name__ == '__main__':
    main()
