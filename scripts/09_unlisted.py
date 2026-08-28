"""Step 9 — add fal endpoints that are live but absent from fal's model index.

fal's /api/models index (step 01) does not return every deployed endpoint.
Some ship with a model page and a queue OpenAPI schema but never appear in the
index — H3-Max, Wan 3.0, Gemini Omni Flash v1.1 among them. A few have a schema
and no page at all.

Discovery vector is fal's own sitemap (https://fal.ai/sitemap-0.xml), which
lists every model page including unlisted ones; each candidate is then
confirmed live by fetching its queue OpenAPI schema.

NOTE ON RATE LIMITING: fal throttles the OpenAPI endpoint. Probing 8k+
candidates at 24 threads produced ~100% false 404s. Keep concurrency <= 4 with
backoff, or every result is a lie.

Reads:  <work>/oas_unlisted/*.json, <work>/unlisted_pricing.json
Writes: merges rows into ../data/models.json
Usage:  python3 09_unlisted.py <work_dir>
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MP720 = 1280 * 720 / 1e6

# Endpoints whose page 404s (schema-only). Pricing inherited from the sibling
# the endpoint is built on, flagged 'est' in price_conf.
INHERITED = {
    'blackforestlabs/flux-3/edit-video': (10.20, '$0.17/s @720p x 60s (FLUX.3 video tier; endpoint has no public page)'),
    'minimax/h3-max/text-to-video/lora': (3.00, '$0.04/s @768p x 1.25 LoRA uplift x 60s (mirrors H3 base->lora ratio)'),
    'minimax/h3-max/image-to-video/lora': (3.00, '$0.04/s @768p x 1.25 LoRA uplift x 60s (mirrors H3 base->lora ratio)'),
    'openrouter/router/video': (None, 'per-token, varies by routed model'),
    'openrouter/router/video/enterprise': (None, 'per-token, varies by routed model'),
}

FAMILIES = [
    (r'wan-3\.0-prime', 'Wan 3.0 Prime'), (r'wan-3\.0', 'Wan 3.0'),
    (r'h3-max', 'MiniMax H3-Max'), (r'minimax/h3', 'MiniMax H3'),
    (r'gemini-omni-flash', 'Gemini Omni Flash'),
    (r'ltx-2\.5', 'LTX-2.5'), (r'ltx-2\.3', 'LTX-2.3'), (r'ltx-2-19b', 'LTX-2 19B'),
    (r'flux-3', 'FLUX.3 Video'),
    (r'longcat-single-avatar', 'LongCat Avatar'),
    (r'flashtalk|latentsync', 'Talking-head (legacy)'),
    (r'argil', 'Argil'), (r'veed', 'VEED'),
    (r'kling-video', 'Kling Audio'),
    (r'mirelo', 'Mirelo SFX'), (r'sonilo', 'Sonilo'),
    (r'bria/video', 'Video background/erase'),
    (r'sa2va|video-understanding|nemotron|openrouter', 'Video understanding'),
    (r'omnilottie', 'OmniLottie'),
    (r'workflow-utilities|ffmpeg', 'Video utilities'),
]

# family -> (strong side, weak side, strong use-cases, weak use-cases)
NEW_VERDICTS = {
 'Wan 3.0': ("Alibaba's third generation: t2v, i2v with optional last frame, and a reference mode that accepts images, video, audio, a document or a web page as conditioning — the widest input surface of any open-lineage family.",
             "480p/720p/1080p only (no 4K); brand-new, so community tooling and LoRAs still target 2.2.",
             "General-purpose scene generation where one family must cover text, image, keyframe and reference modes; document- or page-driven explainer video.",
             "4K masters, workflows that depend on the mature Wan 2.2 LoRA ecosystem."),
 'Wan 3.0 Prime': ("The quality tier of Wan 3.0 — same four input modes at a ~40% premium, tuned for fidelity.",
                   "$8.40/min at 720p puts it above Kling O3 Pro with less independent evaluation behind it.",
                   "Hero shots inside a Wan-3.0 pipeline where the base tier's fidelity falls short.",
                   "Volume work — the base tier is a third cheaper for the same feature set."),
 'MiniMax H3-Max': ("Post-trained H3 at half the price of base H3 ($2.40/min vs $4.80 at 768p): 5–15s continuous duration, six aspect ratios, prompt_expansion_mode, LoRA variants, and end_image_url on i2v so it does keyframes too.",
                    "Caps at 768P — the 2K/4K tiers of base H3 are gone, and it has no reference-to-video endpoint of its own (use minimax/h3/reference-to-video/lora).",
                    "The value pick for high-volume generation with keyframe control; batch work needing consistent style via LoRA.",
                    "2K/4K delivery, reference-driven scenes without falling back to the H3 base family."),
 'LongCat Avatar': ("Audio-driven talking avatars with and without a reference image — the no-image mode invents a consistent presenter from the prompt alone.",
                    "$18/min at 720p is steep for avatar work; young model with little independent evaluation.",
                    "Presenter video when no avatar asset exists yet; quick talking-head drafts from a voice track.",
                    "Volume avatar production (VEED and Kling Avatar are far cheaper)."),
 'Video understanding': ("Video-in, text-out analysis (SA2VA 4B/8B, fal's video-understanding, Nemotron omni, OpenRouter's video router) — captioning, QA and description over a clip.",
                         "Produces text, not video; per-second or per-token billing makes long clips costly.",
                         "Auto-tagging generated footage, QC checks, building prompts from reference video, accessibility descriptions.",
                         "Any generation or editing task."),
 'Kling Audio': ("Extracts or generates the audio track for a Kling clip at a flat $0.035 per video.",
                 "Extraction only — it does not compose new music or design sound.",
                 "Pulling the native audio out of a Kling generation for separate editing.",
                 "Sound design or scoring (use a dedicated video-to-audio model)."),
 'OmniLottie': ("Converts video into a Lottie JSON animation — vector output that scales and stays tiny.",
                "Only suits graphic, flat-motion source; photoreal footage will not vectorise usefully.",
                "Turning generated motion-graphics into lightweight web/app animations.",
                "Photoreal video, anything needing pixel fidelity."),
}


def schema_input(d):
    sch = (d.get('components') or {}).get('schemas') or {}
    cands = [(k, v) for k, v in sch.items()
             if k not in ('QueueStatus', 'File', 'ValidationError', 'HTTPValidationError')
             and not k.endswith(('Output', 'Response')) and 'properties' in v]
    if not cands:
        return {}
    for k, v in cands:
        if 'Input' in k:
            return v
    return cands[0][1]


def enum_of(p):
    if not isinstance(p, dict):
        return None
    if p.get('enum'):
        return p['enum']
    for key in ('anyOf', 'oneOf', 'allOf'):
        for sub in p.get(key) or []:
            if isinstance(sub, dict) and sub.get('enum'):
                return sub['enum']
    return None


def numrange(p):
    if not isinstance(p, dict):
        return (None, None)
    lo, hi = p.get('minimum'), p.get('maximum')
    for key in ('anyOf', 'oneOf'):
        for sub in p.get(key) or []:
            if isinstance(sub, dict):
                lo = lo if lo is not None else sub.get('minimum')
                hi = hi if hi is not None else sub.get('maximum')
    return (lo, hi)


def price(eid, txt):
    """-> (usd_per_min_720p, basis, conf)"""
    if eid in INHERITED:
        v, b = INHERITED[eid]
        return v, b, 'est' if v else 'token'
    t = (txt or '').replace('**', '')
    if not t:
        return None, '', 'none'
    if 'per compute second' in t.lower():
        return None, 'billed per GPU compute-second', 'compute'
    # per-megapixel of generated data (LTX)
    m = re.search(r'\$([0-9.]+)\s*per megapixel', t, re.I)
    if m:
        mp = float(m.group(1))
        return mp * MP720 * 25 * 60, f"${mp}/MP x 0.9216 MP/frame x 25fps x 60s", 'calc'
    # explicit 720p per-second, several phrasings
    for pat in (r'for 720p,?\s*\$([0-9.]+)\s*per second',
                r'\$([0-9.]+)\s+720p\b',
                r'\$([0-9.]+)\s*(?:at|for)\s*720p',
                r'\$([0-9.]+)\s*per second at 720p',
                r'\$([0-9.]+)\s*per video second for 720p'):
        m = re.search(pat, t, re.I)
        if m:
            v = float(m.group(1))
            return v * 60, f"${v}/s @720p x 60s", 'exact'
    # 768p tier (H3 family tops out there)
    m = re.search(r'\$([0-9.]+)\s*per second at 768p', t, re.I)
    if m:
        v = float(m.group(1))
        return v * 60, f"${v}/s @768p x 60s (768P is the top tier)", 'exact'
    # generic per-second / per-minute / per-N-seconds
    m = re.search(r'\$([0-9.]+)\s*per (?:input |output )?second', t, re.I)
    if m:
        v = float(m.group(1))
        return v * 60, f"${v}/s x 60s", 'exact'
    m = re.search(r'\$([0-9.]+)\s*per minute', t, re.I)
    if m:
        return float(m.group(1)), f"${m.group(1)}/min", 'exact'
    m = re.search(r'\$([0-9.]+)\s*per\s*(\d+)\s*second', t, re.I)
    if m:
        v, n = float(m.group(1)), float(m.group(2))
        return v * 60 / n, f"${v} per {n:g}s -> x60", 'exact'
    m = re.search(r'\$([0-9.]+)\s*per second of output and per sample', t, re.I)
    if m:
        return float(m.group(1)) * 60, f"${m.group(1)}/s/sample x 60s", 'exact'
    m = re.search(r'\$([0-9.]+)\s*per video', t, re.I)
    if m:
        return float(m.group(1)) * 12, f"${m.group(1)} per video -> x60 assuming 5s clips", 'est'
    if 'token' in t.lower():
        return None, 'token-based', 'token'
    return None, '', 'none'


def classify(eid, cat, props):
    """-> (category, is_ref, f_task)"""
    if re.search(r'audio-to-video', eid):
        return 'image-to-video', False, 'generate'
    if re.search(r'video-to-audio|video-to-sound|/sfx', eid):
        return 'video-to-video', False, 'video→audio'
    if re.search(r'sa2va|video-understanding|nemotron|openrouter', eid):
        return 'video-to-video', False, 'analysis/masking'
    if re.search(r'video-to-lottie|interleave-video', eid):
        return 'video-to-video', False, 'utility'
    if re.search(r'despill|background-removal', eid):
        return 'video-to-video', False, 'inpaint/erase'
    if re.search(r'edit-video', eid):
        return 'video-to-video', False, 'edit/restyle'
    if 'reference-to-video' in eid:
        return 'image-to-video', True, 'generate'
    if cat == 'text-to-video':
        return 'text-to-video', False, 'generate'
    return 'image-to-video', False, 'generate'


def build(work):
    oas = os.path.join(work, 'oas_unlisted')
    pricing = json.load(open(os.path.join(work, 'unlisted_pricing.json')))
    ids = json.load(open(os.path.join(work, 'unlisted_video.json')))
    ids = sorted(set(ids) | set(INHERITED))
    rows = []
    for eid in ids:
        p = os.path.join(oas, eid.replace('/', '__') + '.json')
        if not os.path.exists(p):
            continue
        d = json.load(open(p))
        meta = (d.get('info') or {}).get('x-fal-metadata') or {}
        props = schema_input(d).get('properties', {}) or {}
        about = (meta.get('about') or '').strip()
        cat, is_ref, task = classify(eid, meta.get('category') or '', props)
        usd, basis, conf = price(eid, pricing.get(eid, ''))

        dur = props.get('duration') or {}
        de = enum_of(dur)
        dlo, dhi = numrange(dur)
        nlo, nhi = numrange(props.get('num_frames') or {})
        fps = (props.get('fps') or {}).get('default') or 24
        res_e = enum_of(props.get('resolution') or {})
        ar_e = enum_of(props.get('aspect_ratio') or {})
        start = [k for k in ('image_url', 'start_image_url', 'first_image_url', 'image_urls',
                             'reference_image_urls', 'input_image_urls') if k in props]
        end = [k for k in ('end_image_url', 'last_frame_url', 'tail_image_url') if k in props]
        aud = [k for k in ('generate_audio', 'audio_url', 'audio_urls', 'reference_audio_urls',
                           'voice', 'voice_id') if k in props]

        if de:
            f_dur = ', '.join(str(x) for x in de) + ' s'
            mx = max((float(re.sub(r'[^0-9.]', '', str(x)) or 0) for x in de), default=None)
        elif dlo is not None or dhi is not None:
            f_dur = f"{dlo}–{dhi} s continuous"
            mx = dhi
        elif nhi:
            f_dur = f"{(nlo or 1)/fps:.1f}–{nhi/fps:.1f} s via num_frames"
            mx = nhi / fps
        else:
            f_dur = 'follows input length' if task != 'generate' else 'not exposed'
            mx = None
        maxf = int(round(mx * fps)) if mx else (int(nhi) if nhi else None)

        fam = next((n for pat, n in FAMILIES if re.search(pat, eid)), 'Unlisted misc')
        is_audio_driven = 'audio-to-video' in eid
        rows.append({
            'id': eid, 'title': meta.get('title') or '', 'lab': meta.get('modelLab') or '',
            'category': cat, 'is_ref': is_ref, 'tags': [], 'desc': about[:200],
            'about': about[:1500], 'pricing_raw': '', 'price': {}, 'machineType': None,
            'price_text': pricing.get(eid, ''), 'price_basis': basis, 'price_conf': conf,
            'price_src': 'model page (unlisted)' if pricing.get(eid) else 'sibling endpoint',
            'usd_per_min_720p': round(usd, 2) if usd else None,
            'duration_enum': de, 'duration_min': dlo, 'duration_max': dhi,
            'duration_default': dur.get('default'),
            'res_enum': res_e, 'res_default': (props.get('resolution') or {}).get('default'),
            'ar_enum': ar_e,
            'num_frames_min': nlo, 'num_frames_max': nhi, 'num_frames_default': None,
            'fps_enum': None, 'fps_min': None, 'fps_max': None, 'fps_default': fps,
            'has_audio_field': aud, 'start_keys': start, 'end_keys': end,
            'multi_keys': [k for k in ('multi_prompt', 'shot_type', 'keyframes', 'elements') if k in props],
            'lip_keys': [k for k in ('audio_url', 'voice', 'text') if k in props],
            'lipsync_tag': bool(re.search(r'avatar|talk|lipsync|flashtalk', eid)),
            'all_props': sorted(props.keys()), 'has_schema': True,
            'family': fam, 'family_key': fam, 'f_task': task,
            'f_duration': f_dur, 'f_maxframes': maxf,
            'f_maxframes_basis': 'from schema' if maxf else 'driven by input length',
            'f_quality': ', '.join(str(x) for x in res_e) if res_e else 'fixed',
            'f_aspect': ', '.join(str(x) for x in ar_e) if ar_e else (
                'inherits input' if cat != 'text-to-video' else 'fixed'),
            'f_audio': ('Yes — native generation' if 'generate_audio' in props else
                        'Input only (drives lipsync)' if aud else 'No'),
            'f_start': ('Yes (multi-image / reference)' if is_ref else
                        'Yes' if start else
                        'No (text-only)' if cat == 'text-to-video' else 'No'),
            'f_end': 'Yes' if end else 'No',
            'f_multicut': 'No — single shot',
            'f_lipsync': ('Yes — dedicated lipsync/avatar model'
                          if re.search(r'avatar|talk|lipsync', eid)
                          else 'Partial — audio input, no explicit lipsync claim'
                          if is_audio_driven else 'No'),
        })
    return rows


def main():
    work = sys.argv[1]
    new = build(work)
    path = os.path.join(ROOT, 'data', 'models.json')
    rows = json.load(open(path))
    have = {r['id'] for r in rows}
    add = [r for r in new if r['id'] not in have]

    # verdicts: new families defined here, existing families inherit
    inherit = {}
    for r in rows:
        inherit.setdefault(r['family_key'], (r['f_strong'], r['f_weak'],
                                             r.get('f_use_strong', ''), r.get('f_use_weak', '')))
    for r in add:
        v = NEW_VERDICTS.get(r['family_key']) or inherit.get(r['family_key']) or ('', '', '', '')
        r['f_strong'], r['f_weak'], r['f_use_strong'], r['f_use_weak'] = v

    merged = rows + add
    json.dump(merged, open(path, 'w'), indent=1)
    print(f'added {len(add)} unlisted endpoints -> {len(merged)} total')
    import collections
    print('by task:', dict(collections.Counter(r['f_task'] for r in add)))
    missing = [r['id'] for r in add if not r['f_strong']]
    if missing:
        print('WARNING no verdict:', missing)


if __name__ == '__main__':
    main()
