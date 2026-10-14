"""Step 9 — find fal video endpoints that are live but absent from the model index.

Runs right after 01 (it appends to all_video_models.json, so every later step
treats unlisted endpoints exactly like listed ones — same schema extraction,
same price engine, same fields, families and verdicts).

fal's /api/models index (step 01) does not return every deployed endpoint:
- endpoints fal marks `status: unlisted` (e.g. the whole Veo 3.1 family since
  Sep 2026) are callable and have a model page, but never appear in the index;
- endpoints fal marks `deprecated: true` (Kling 1.x/2.0/2.1, Luma Ray 2, LTX-2
  19B...) drop out of the index while still being callable;
- a few endpoints have a queue OpenAPI schema and no public page at all.

Discovery vectors (fal's sitemap no longer lists unlisted pages — it is now a
single sitemap.xml that mirrors the index, and sitemap-0.xml is gone):
  1. every endpoint the atlas carried before (../data/models.json) that today's
     index no longer returns;
  2. sibling probes: for the families in SIBLING_FAMILIES, every listed
     endpoint's base path x the standard mode suffixes (+ /lora);
  3. model records embedded in the pages fetched here (a model page carries the
     records of its family siblings, unlisted ones included).
Each candidate is confirmed live by fetching its queue OpenAPI schema; its model
page is then read for the embedded model record (title, category, pricing copy,
status, deprecated flag). Candidates whose schema 404s are dead.

The page also carries fal's `endpoint_messages` list — scheduled deprecation
notices ("This endpoint will be deprecated on November 17, 2026") keyed by exact
id or id prefix. Those are written to endpoint_messages.json and applied as row
status by 08.

NOTE ON RATE LIMITING: fal throttles the OpenAPI endpoint. Probing 8k+
candidates at 24 threads produced ~100% false 404s (Aug 2026). Concurrency is
capped at 3 with backoff, and every 404 is re-probed once, slowly, before it
is believed.

Reads:  all_video_models.json (from 01), ../data/models.json
Writes: all_video_models.json (unlisted records appended, `_unlisted: true`),
        oas/<id>.json (schemas, reused by 02), unlisted_report.json,
        endpoint_messages.json
Usage:  python3 09_unlisted.py
"""
import concurrent.futures as cf
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
OAS_DIR = 'oas'
PAGE_DIR = 'pages_unlisted'

MODES = ['text-to-video', 'image-to-video', 'reference-to-video',
         'first-last-frame-to-video', 'start-end-to-video', 'extend-video',
         'video-to-video', 'edit-video', 'audio-to-video']
# families whose sibling paths are worth probing (recent / fast-moving lines)
SIBLING_FAMILIES = [
    r'^fal-ai/veo3', r'^google/', r'^minimax/h3', r'^bytedance/seedance-2',
    r'^fal-ai/kling-video/(v3|o3)', r'^alibaba/', r'^fal-ai/vidu/q[34]',
    r'^luma/', r'^fal-ai/pixverse/(v6|c1)', r'^xai/', r'^lightricks/',
    r'^fal-ai/kandinsky6', r'^blackforestlabs/', r'^fal-ai/ltx-2\.3',
]
# extra hand-named candidates (announced or previously seen, cheap to check)
EXTRA_CANDIDATES = [
    'fal-ai/veo3.1/lite/reference-to-video', 'fal-ai/veo3.1/lite/extend-video',
    'fal-ai/veo3', 'fal-ai/veo3/fast', 'fal-ai/veo3/image-to-video',
    'fal-ai/sora-2/text-to-video', 'fal-ai/sora-2/image-to-video',
    'fal-ai/sora-2/text-to-video/pro', 'fal-ai/sora-2/image-to-video/pro',
    'fal-ai/sora-2/video-to-video/remix',
]
EXTRA_CATS = {'audio-to-video': 'image-to-video', 'video-to-audio': 'video-to-video',
              'video-to-text': 'video-to-video', 'vision': 'video-to-video'}


def esc(eid):
    return eid.replace('/', '__')


def http(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b''
    except Exception:
        return 0, b''


def probe_schema(eid, slow=False):
    """-> True (live, cached), False (404), None (inconclusive)."""
    path = os.path.join(OAS_DIR, esc(eid) + '.json')
    if os.path.exists(path) and os.path.getsize(path) > 200:
        return True
    url = 'https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=' + urllib.parse.quote(eid, safe='')
    for attempt in range(4):
        time.sleep(1.5 if slow else 0.25)
        code, raw = http(url)
        if code == 200:
            try:
                d = json.loads(raw)
            except Exception:
                return None
            if not (isinstance(d, dict) and d.get('paths')):
                return False
            with open(path, 'wb') as f:
                f.write(raw)
            return True
        if code == 404:
            return False
        time.sleep(2 * (attempt + 1))       # 429 / 5xx / network: back off
    return None


def get_page(eid):
    path = os.path.join(PAGE_DIR, esc(eid) + '.html')
    if os.path.exists(path) and os.path.getsize(path) > 50_000:
        return open(path, encoding='utf-8', errors='ignore').read()
    time.sleep(0.3)
    code, raw = http('https://fal.ai/models/' + eid, timeout=90)
    if code != 200:
        return ''
    with open(path, 'wb') as f:
        f.write(raw)
    return raw.decode('utf-8', errors='ignore')


def _json_object_at(s, i):
    """Parse the JSON object starting at s[i] == '{' by brace matching."""
    depth, j, in_str, escp = 0, i, False, False
    while j < len(s):
        c = s[j]
        if in_str:
            if escp:
                escp = False
            elif c == '\\':
                escp = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return json.loads(s[i:j + 1])
        j += 1
    return None


def unescape_flight(html_text):
    """Model data sits in Next.js flight strings: JSON with escaped quotes."""
    return html_text.replace('\\\\', '\x00').replace('\\"', '"').replace('\x00', '\\')


def page_record(eid, page):
    """The page's own model record (same shape as an /api/models item)."""
    s = unescape_flight(page)
    k = s.find(f'"endpointId":"{eid}","model":{{')
    if k < 0:
        return None
    try:
        return _json_object_at(s, s.index('{', k + len(f'"endpointId":"{eid}","model":')))
    except Exception:
        return None


def embedded_ids(page):
    s = unescape_flight(page)
    return set(re.findall(r'"id":"([a-z0-9][\w.\-]*/[\w.\-/]+)","modelId"', s))


def endpoint_messages(page):
    s = unescape_flight(page)
    k = s.find('"endpoint_messages":[')
    if k < 0:
        return None
    i = s.index('[', k)
    out = []
    for m in re.finditer(r'"rule":"(exact_match|starts_with)","type":"(\w+)","value":"([^"]+)","message":"([^"]+)"',
                         s[i:i + 20000]):
        out.append({'rule': m.group(1), 'type': m.group(2), 'value': m.group(3), 'message': m.group(4)})
    return out


def sibling_candidates(catalog_ids):
    out = set()
    for eid in catalog_ids:
        if not any(re.search(p, eid) for p in SIBLING_FAMILIES):
            continue
        segs = eid.split('/')
        cut = next((i for i, s in enumerate(segs) if s in MODES), None)
        if cut is None:
            continue
        base = '/'.join(segs[:cut])
        for mode in MODES[:6]:
            out.add(f'{base}/{mode}')
            out.add(f'{base}/{mode}/lora')
    return out


def main():
    os.makedirs(OAS_DIR, exist_ok=True)
    os.makedirs(PAGE_DIR, exist_ok=True)
    catalog = json.load(open('all_video_models.json'))
    listed = set(catalog)

    prev_path = os.path.join(ROOT, 'data', 'models.json')
    prev_rows = {r['id']: r for r in json.load(open(prev_path))} if os.path.exists(prev_path) else {}
    prev = set(prev_rows)

    cands = (prev - listed) | (sibling_candidates(listed) - listed) | (set(EXTRA_CANDIDATES) - listed)
    print(f'candidates: {len(cands)} (previously carried {len(prev - listed)}, '
          f'siblings {len(sibling_candidates(listed) - listed)})')

    live, dead, unsure = set(), set(), set()

    def run_probe(ids, slow=False, threads=3):
        res = {}
        with cf.ThreadPoolExecutor(threads) as ex:
            for n, (eid, ok) in enumerate(zip(ids, ex.map(lambda e: probe_schema(e, slow), ids)), 1):
                res[eid] = ok
                if n % 50 == 0:
                    print(f'  probed {n}/{len(ids)}', flush=True)
        return res

    todo = sorted(cands)
    seen = set()
    rounds = 0
    while todo and rounds < 3:
        rounds += 1
        seen |= set(todo)
        res = run_probe(todo)
        # never trust a first 404 for an endpoint we know existed (or was named);
        # sibling guesses are mostly genuinely absent, so only retry inconclusives
        retry = [e for e, ok in res.items()
                 if ok is None or (ok is False and (e in prev or e in EXTRA_CANDIDATES))]
        if retry:
            res.update(run_probe(retry, slow=True, threads=1))
        for e, ok in res.items():
            (live if ok else dead if ok is False else unsure).add(e)
        # harvest sibling records embedded in the pages of live candidates
        more = set()
        for e in sorted(e for e, ok in res.items() if ok):
            more |= embedded_ids(get_page(e))
        todo = sorted(x for x in more - listed - seen
                      if re.search(r'video|veo|kling|seedance|h3|wan|ltx|vidu|ray|pixverse|grok|sora', x))
        print(flush=True)
        print(f'round {rounds}: live {len(live)}, dead {len(dead)}, unsure {len(unsure)}, '
              f'new from pages {len(todo)}')

    added, report = 0, {'live': [], 'dead': sorted(dead), 'unsure': sorted(unsure)}
    msgs = None
    for eid in sorted(live):
        page = get_page(eid)
        if msgs is None and page:
            msgs = endpoint_messages(page)
        rec = page_record(eid, page) if page else None
        oas = json.load(open(os.path.join(OAS_DIR, esc(eid) + '.json')))
        meta = (oas.get('info') or {}).get('x-fal-metadata') or {}
        if rec:
            if rec.get('removed'):
                report['dead'].append(eid)
                continue
            item = rec
        else:
            item = {'id': eid, 'title': meta.get('title') or eid.split('/')[-1],
                    'category': meta.get('category') or '', 'shortDescription': '',
                    'pricingInfoOverride': '', 'modelLab': meta.get('modelLab') or '',
                    'modelFamily': '', 'tags': [], 'machineType': None,
                    'status': 'schema-only', 'deprecated': False}
        cat = item.get('category') or ''
        item['category_src'] = cat
        if eid in prev_rows:                # keep the category earlier passes curated
            item['category'] = prev_rows[eid]['category']
        elif cat not in ('text-to-video', 'image-to-video', 'video-to-video'):
            item['category'] = EXTRA_CATS.get(cat) or (
                'video-to-video' if re.search(r'video-to-|edit|extend|upscale', eid)
                else 'text-to-video' if 'text-to-video' in eid else 'image-to-video')
        if (item.get('pricingInfoOverride') or '').strip() in ('$undefined', 'undefined'):
            item['pricingInfoOverride'] = ''     # page renders pricing itself; 02 scrapes it
        item['_unlisted'] = True
        item['_page_status'] = item.get('status') or ('schema-only' if not rec else '')
        catalog[eid] = item
        added += 1
        report['live'].append({'id': eid, 'status': item['_page_status'],
                               'deprecated': bool(item.get('deprecated')),
                               'category': item['category']})

    if msgs is None:                       # no unlisted page fetched: read any listed page
        for eid in sorted(listed)[:3]:
            msgs = endpoint_messages(get_page(eid))
            if msgs:
                break
    json.dump(msgs or [], open('endpoint_messages.json', 'w'), indent=1)
    json.dump(catalog, open('all_video_models.json', 'w'), indent=1)
    json.dump(report, open('unlisted_report.json', 'w'), indent=1)
    print(f'appended {added} unlisted endpoints -> {len(catalog)} in catalog')
    print(f'deprecation notices: {len(msgs or [])}')
    print('dead (schema 404):', len(report['dead']), '| inconclusive:', len(unsure))


if __name__ == '__main__':
    main()
