"""Derive the remaining spec fields for every endpoint."""
import json, re

rows = json.load(open('priced2.json'))


def fmt_list(v, maxn=9):
    if not v: return None
    v = [str(x) for x in v]
    if len(v) > maxn: return ', '.join(v[:maxn]) + f' (+{len(v)-maxn})'
    return ', '.join(v)


def duration_opts(r):
    e = r.get('duration_enum')
    if e:
        vals = [str(x) for x in e]
        return fmt_list(vals, 12) + ' s' if all(re.fullmatch(r'[\d.]+', x) for x in vals) else fmt_list(vals, 12)
    lo, hi = r.get('duration_min'), r.get('duration_max')
    if lo is not None or hi is not None:
        return f"{lo or '?'}–{hi or '?'} s (continuous)"
    nlo, nhi = r.get('num_frames_min'), r.get('num_frames_max')
    fps = r.get('fps_default') or 24
    if nhi:
        try: return f"{(nlo or 1)/fps:.1f}–{nhi/fps:.1f} s (via num_frames)"
        except Exception: pass
    d = r.get('duration_default')
    if d: return f"fixed {d}"
    return 'fixed / not exposed'


def max_frames(r):
    nhi = r.get('num_frames_max')
    fps = r.get('fps_default') or r.get('fps_min')
    if nhi: return int(nhi), f"num_frames max {int(nhi)}"
    # from duration
    dmax = None
    e = r.get('duration_enum')
    if e:
        nums = []
        for x in e:
            m = re.fullmatch(r'([\d.]+)s?', str(x))
            if m: nums.append(float(m.group(1)))
        if nums: dmax = max(nums)
    if dmax is None and r.get('duration_max'): dmax = float(r['duration_max'])
    if dmax is None:
        dd = r.get('duration_default')
        if dd:
            m = re.search(r'[\d.]+', str(dd))
            if m: dmax = float(m.group(0))
    if dmax:
        f = fps or 24
        return int(round(dmax * f)), f"{dmax:g}s x {f:g}fps"
    return None, ''


AUDIO_GEN = {'generate_audio', 'generate_audio_switch', 'audio_cfg_scale', 'audio_modality_scale', 'bgm'}
AUDIO_IN = {'audio_url', 'audio_urls', 'audio', 'voice', 'voice_id'}


def audio(r):
    keys = set(r.get('has_audio_field') or [])
    txt = (r['desc'] + ' ' + r['about']).lower()
    gen = bool(keys & AUDIO_GEN) or 'native audio' in txt or 'synchronized audio' in txt
    inp = bool(keys & AUDIO_IN)
    if gen and inp: return 'Yes — native gen + audio input'
    if gen: return 'Yes — native generation'
    if inp: return 'Input only (drives lipsync)'
    return 'No'


def start_frame(r):
    k = set(r.get('start_keys') or [])
    if r['category'] == 'text-to-video' and not k: return 'No (text-only)'
    if k & {'image_url', 'start_image_url', 'first_image_url', 'first_frame_url'}: return 'Yes'
    if k & {'image_urls', 'input_image_urls', 'keyframes', 'elements', 'frontal_image_url'}: return 'Yes (multi-image / reference)'
    return 'No'


def end_frame(r):
    k = set(r.get('end_keys') or [])
    if k: return 'Yes'
    if 'keyframes' in (r.get('all_props') or []): return 'Yes (via keyframes)'
    eid = r['id']
    if 'flf2v' in eid or 'first-last-frame' in eid or 'start-end' in eid or 'pikaframes' in eid or 'transition' in eid:
        return 'Yes'
    return 'No'


def multicut(r):
    props = set(r.get('all_props') or [])
    txt = (r['desc'] + ' ' + r['about']).lower()
    if 'multi_prompt' in props or 'multi_shots' in props or 'generate_multi_clip_switch' in props:
        return 'Yes — native multi-shot'
    if 'keyframes' in props or 'elements' in props:
        return 'Partial — keyframe/element chaining'
    if re.search(r'multi-?shot|multiple shots|multi-?clip|shot transitions|cuts between', txt):
        return 'Yes — native multi-shot'
    if 'single-shot' in txt or 'single shot' in txt:
        return 'No — single continuous shot'
    return 'No — single shot'


def lipsync(r):
    eid, txt = r['id'], (r['desc'] + ' ' + r['about']).lower()
    props = set(r.get('all_props') or [])
    tags = r.get('tags') or []
    hard = any(s in eid for s in ('lipsync', 'avatar', 'omnihuman', 'infinitalk', 'sadtalker',
                                  'musetalk', 'live-portrait', 'talking', 'magihuman', 'flashhead',
                                  'ai-avatar', 'digital-twin', 'video-agent', 'lynx', 'fabric'))
    if hard: return 'Yes — dedicated lipsync/avatar model'
    if 'audio_url' in props and re.search(r'lip.?sync|talking|speech|speaking', txt):
        return 'Yes — audio-driven lipsync'
    if re.search(r'lip.?sync', txt): return 'Yes — dialogue/lipsync supported'
    if 'lipsync' in tags:
        return 'Yes — dialogue via prompt (native audio)'
    if 'audio_url' in props: return 'Partial — audio input, no explicit lipsync claim'
    return 'No'


def quality_opts(r):
    e = r.get('res_enum')
    if e: return fmt_list(e, 8)
    props = r.get('all_props') or []
    if 'video_quality' in props: return 'video_quality preset'
    if 'width' in props and 'height' in props: return 'free width/height'
    if 'video_size' in props: return 'video_size presets'
    txt = (r['desc'] + ' ' + r['about'] + ' ' + (r.get('price_text') or '')).lower()
    found = sorted(set(re.findall(r'\b(360p|480p|540p|580p|720p|768p|1080p|1440p|2k|4k)\b', txt)))
    if found: return ', '.join(found) + ' (from docs)'
    return 'fixed'


def aspect_opts(r):
    e = r.get('ar_enum')
    if e: return fmt_list(e, 10)
    props = r.get('all_props') or []
    if 'width' in props and 'height' in props: return 'free (width/height)'
    if r['category'] == 'image-to-video': return 'inherits input image'
    return 'fixed'


for r in rows:
    mf, mfb = max_frames(r)
    r['f_maxframes'] = mf
    r['f_maxframes_basis'] = mfb
    r['f_duration'] = duration_opts(r)
    r['f_quality'] = quality_opts(r)
    r['f_aspect'] = aspect_opts(r)
    r['f_audio'] = audio(r)
    r['f_start'] = start_frame(r)
    r['f_end'] = end_frame(r)
    r['f_multicut'] = multicut(r)
    r['f_lipsync'] = lipsync(r)

json.dump(rows, open('final.json', 'w'), indent=1)
print('done', len(rows))
import collections
for k in ('f_audio', 'f_start', 'f_end', 'f_multicut', 'f_lipsync'):
    print('\n', k, dict(collections.Counter(r[k] for r in rows)))
print('\nmaxframes unknown:', sum(1 for r in rows if not r['f_maxframes']))
