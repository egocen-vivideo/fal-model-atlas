import json, os, re, glob, collections

CAT = json.load(open('all_video_models.json'))

def safe(i): return i.replace('/', '__') + '.json'

def input_schema(d):
    sch = (d.get('components') or {}).get('schemas') or {}
    cands = []
    for k, v in sch.items():
        if k in ('QueueStatus', 'File', 'ValidationError', 'HTTPValidationError'): continue
        if k.endswith('Output') or k.endswith('Response'): continue
        if 'properties' not in v: continue
        cands.append((k, v))
    if not cands: return {}
    for k, v in cands:
        if 'Input' in k: return v
    return cands[0][1]

def enum_of(p):
    if not isinstance(p, dict): return None
    if p.get('enum'): return p['enum']
    for key in ('anyOf', 'oneOf', 'allOf'):
        for sub in p.get(key) or []:
            if isinstance(sub, dict) and sub.get('enum'): return sub['enum']
    return None

def numrange(p):
    if not isinstance(p, dict): return (None, None)
    lo, hi = p.get('minimum'), p.get('maximum')
    for key in ('anyOf', 'oneOf'):
        for sub in p.get(key) or []:
            if isinstance(sub, dict):
                lo = lo if lo is not None else sub.get('minimum')
                hi = hi if hi is not None else sub.get('maximum')
    return (lo, hi)

START_KEYS = ['image_url', 'start_image_url', 'first_image_url', 'first_frame_url',
              'input_image_urls', 'image_urls', 'frontal_image_url', 'keyframes', 'elements']
END_KEYS = ['end_image_url', 'tail_image_url', 'last_frame_url', 'end_image_strength']
AUDIO_KEYS = ['generate_audio', 'generate_audio_switch', 'audio_url', 'audio_urls', 'audio',
              'bgm', 'voice', 'voice_id', 'audio_cfg_scale', 'audio_modality_scale']
MULTI_KEYS = ['multi_shots', 'generate_multi_clip_switch', 'multi_prompt', 'keyframes',
              'shot_type', 'elements']
LIP_KEYS = ['audio_url', 'audio_urls', 'voice', 'voice_id', 'text', 'avatar', 'frontal_image_url']


def f(s):
    try: return float(s.rstrip('.'))
    except Exception: return None

def parse_price(txt, meta):
    """Return dict of resolution->$/sec, plus flat and per-video prices."""
    out = {'per_sec': {}, 'flat': None, 'notes': ''}
    if not txt: return out
    t = txt.replace('*', '')
    # $X per second at RES  /  for RES ... $X per second
    for m in re.finditer(r'\$([0-9.]+)\s*(?:/|per\s+)second[^.$]{0,60}?\b(\d{3,4}p|4k|2k|720|1080)\b', t, re.I):
        v=f(m.group(1));
        if v: out['per_sec'].setdefault(m.group(2).lower(), v)
    for m in re.finditer(r'\b(\d{3,4}p|4k|2k)\b[^.$]{0,80}?\$([0-9.]+)\s*(?:/|per\s+)?\s*(?:per\s+)?second', t, re.I):
        v=f(m.group(2));
        if v: out['per_sec'].setdefault(m.group(1).lower(), v)
    # "For 720p, you will be charged roughly $0.4730 per second"
    for m in re.finditer(r'(?:for|at)\s+(\d{3,4}p|4k|2k)\b[^.$]{0,60}\$([0-9.]+)', t, re.I):
        v=f(m.group(2));
        if v: out['per_sec'].setdefault(m.group(1).lower(), v)
    # generic "$X per second of video" with no resolution
    if not out['per_sec']:
        m = re.search(r'\$([0-9.]+)\s*(?:/|per\s+)second', t, re.I)
        if m and f(m.group(1)): out['per_sec']['any'] = f(m.group(1))
    m = re.search(r'\$([0-9.]+)\s*per\s+(?:generated\s+)?video', t, re.I)
    if m: out['flat'] = f(m.group(1))
    if re.search(r'megapixel|per\s+1000\s+tokens|compute', t, re.I):
        out['notes'] = 'token/compute-based component'
    return out


rows = []
for eid, meta in CAT.items():
    if meta['category'] not in ('text-to-video', 'image-to-video'): continue
    p = os.path.join('oas', safe(eid))
    props, about = {}, ''
    if os.path.exists(p):
        try:
            d = json.load(open(p))
            if isinstance(d, dict):
                props = input_schema(d).get('properties', {}) or {}
                about = (((d.get('info') or {}).get('x-fal-metadata') or {}).get('about') or '')
        except Exception:
            pass
    txt = (meta.get('shortDescription') or '') + ' ' + about
    tags = [t.lower() for t in (meta.get('tags') or [])]

    dur = props.get('duration') or {}
    dur_enum = enum_of(dur)
    dlo, dhi = numrange(dur)
    res_enum = enum_of(props.get('resolution') or {}) or enum_of(props.get('video_quality') or {})
    ar_enum = enum_of(props.get('aspect_ratio') or {}) or enum_of(props.get('video_size') or {}) or enum_of(props.get('orientation') or {})
    nf = props.get('num_frames') or {}
    nflo, nfhi = numrange(nf)
    fps_p = props.get('fps') or props.get('frames_per_second') or props.get('frame_rate') or props.get('export_fps') or {}
    fps_enum = enum_of(fps_p); fpslo, fpshi = numrange(fps_p)

    rows.append({
        'id': eid,
        'title': meta.get('title'),
        'lab': meta.get('modelLab'),
        'family': meta.get('modelFamily'),
        'category': meta['category'],
        'is_ref': 'reference' in eid or 'reference-to-video' in tags or 'subject-reference' in eid,
        'tags': tags,
        'desc': (meta.get('shortDescription') or '').strip(),
        'about': about[:1500],
        'pricing_raw': (meta.get('pricingInfoOverride') or '').strip(),
        'price': parse_price(meta.get('pricingInfoOverride'), meta),
        'machineType': meta.get('machineType'),
        'duration_enum': dur_enum, 'duration_min': dlo, 'duration_max': dhi,
        'duration_default': dur.get('default'),
        'res_enum': res_enum, 'res_default': (props.get('resolution') or {}).get('default'),
        'ar_enum': ar_enum,
        'num_frames_min': nflo, 'num_frames_max': nfhi,
        'num_frames_default': nf.get('default'),
        'fps_enum': fps_enum, 'fps_min': fpslo, 'fps_max': fpshi,
        'fps_default': fps_p.get('default'),
        'has_audio_field': [k for k in AUDIO_KEYS if k in props],
        'start_keys': [k for k in START_KEYS if k in props],
        'end_keys': [k for k in END_KEYS if k in props],
        'multi_keys': [k for k in MULTI_KEYS if k in props],
        'lip_keys': [k for k in LIP_KEYS if k in props],
        'lipsync_tag': 'lipsync' in tags or 'lip sync' in tags or 'avatar' in tags,
        'all_props': sorted(props.keys()),
        'has_schema': bool(props),
    })

json.dump(rows, open('extracted.json', 'w'), indent=1)
print('rows:', len(rows))
print('no schema:', [r['id'] for r in rows if not r['has_schema']])
print('with price parsed:', sum(1 for r in rows if r['price']['per_sec'] or r['price']['flat']))
print('reference models:', sum(1 for r in rows if r['is_ref']))
