"""Extract fields + pricing for fal image & audio endpoints."""
import json, os, re, html, math

def schema_input(d):
    sch = (d.get('components') or {}).get('schemas') or {}
    cands = []
    for k, v in sch.items():
        if k in ('QueueStatus', 'File', 'ValidationError', 'HTTPValidationError'): continue
        if k.endswith('Output') or k.endswith('Response'): continue
        if 'properties' in v: cands.append((k, v))
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

def page_pricing(eid):
    p = os.path.join('pages2', eid.replace('/', '__') + '.html')
    if not os.path.exists(p): return ''
    t = open(p, encoding='utf-8', errors='ignore').read()
    t = re.sub(r'<script[\s\S]*?</script>', '', t)
    for m in re.finditer(r'<p>((?:(?!</p>).){0,900})</p>', t, re.S):
        s = re.sub(r'<[^>]+>', ' ', re.sub(r'<!--.*?-->', '', m.group(1)))
        s = html.unescape(re.sub(r'\s+', ' ', s)).strip()
        if '$' in s and re.search(r'will cost|per |charged|costs', s, re.I) and len(s) > 15:
            return s
    return ''

def F(s):
    s = str(s).rstrip('.').replace(',', '')
    return float(s) if s else 0.0

# ---------------- image pricing -> $/image at 1MP ----------------
def price_image(t, has_input):
    t = t.replace('**', '').replace(' ', ' ')
    tl = t.lower()
    if 'per compute second' in tl:
        return None, 'billed per GPU compute-second', 'compute'
    m = re.search(r'\$([0-9.]+)\s*(?:per|/)\s*megapixel in TURBO[^.]*?\$([0-9.]+)\s*(?:per|/)\s*megapixel in BALANCED', t, re.I)
    if m: return F(m.group(2)), f"${m.group(2)}/MP (BALANCED) x 1MP", 'exact'
    m = re.search(r'\$([0-9.]+)\s*with TURBO,?\s*\$([0-9.]+)\s*with BALANCED', t, re.I)
    if m: return F(m.group(2)), f"${m.group(2)} BALANCED mode (TURBO ${m.group(1)})", 'exact'
    m = re.search(r'\$([0-9.]+)\s*with Express,?\s*\$([0-9.]+)\s*with Standard', t, re.I)
    if m: return F(m.group(2)), f"${m.group(2)} Standard tier", 'exact'
    m = re.search(r'\$([0-9.]+)\s*with Low Quality,?\s*\$([0-9.]+)\s*with Medium', t, re.I)
    if m: return F(m.group(2)), f"${m.group(2)} Medium quality", 'exact'
    m = re.search(r'\$([0-9.]+)\s*for the first megapixel of output,?\s*plus\s*\$([0-9.]+)\s*per extra megapixel', t, re.I)
    if m:
        v = F(m.group(1)) + (F(m.group(2)) if has_input else 0)
        return v, f"${m.group(1)} first MP out" + (f" + ${m.group(2)} 1MP input" if has_input else ''), 'exact'
    m = re.search(r'\$([0-9.]+)\s*per megapixel of input and output', t, re.I)
    if m:
        v = F(m.group(1)) * (2 if has_input else 1)
        return v, f"${m.group(1)}/MP x {'2MP (1 in + 1 out)' if has_input else '1MP'}", 'exact'
    m = re.search(r'\$([0-9.]+)\s*per megapixel', t, re.I)
    if m: return F(m.group(1)), f"${m.group(1)}/MP x 1MP", 'exact'
    m = re.search(r'\$([0-9.]+)\s*\(low\)\s*or\s*\$([0-9.]+)\s*\(medium\)\s*per image for 1K', t, re.I)
    if m: return F(m.group(2)), f"${m.group(2)} medium 1K", 'exact'
    m = re.search(r'\$([0-9.]+)\s*per (?:1K|generated) image(?: at 1K)?', t, re.I)
    if m: return F(m.group(1)), f"${m.group(1)} per 1K image", 'exact'
    m = re.search(r'\$([0-9.]+)\s*per image for 480p or \$([0-9.]+)\s*per image for 720p', t, re.I)
    if m: return F(m.group(2)), f"${m.group(2)} per 720p image", 'exact'
    m = re.search(r'charged\s*\$([0-9.]+)\s*\(text-to-image\)', t, re.I)
    if m: return F(m.group(1)), f"${m.group(1)} t2i base", 'exact'
    for pat, basis in [(r'\$([0-9.]+)\s*per image', '${} per image'),
                       (r'Each image costs\s*\$([0-9.]+)', '${} per image'),
                       (r'\$([0-9.]+)\s*per request', '${} per request'),
                       (r'\$([0-9.]+)\s*per (?:generation|edit)', '${} per generation')]:
        m = re.search(pat, t, re.I)
        if m: return F(m.group(1)), basis.format(m.group(1)), 'exact'
    # token-based with example
    m = re.search(r'1024\s*[x×]\s*1024[^.$]{0,80}\$([0-9.]+)', t, re.I)
    if m: return F(m.group(1)), f"${m.group(1)} per 1024x1024 (from example)", 'est'
    if 'token' in tl:
        return None, 'token-based (varies with size/quality)', 'token'
    m = re.search(r'\$([0-9.]+[0-9])', t)
    if m and len(t) < 200 and F(m.group(1)) > 0:
        return F(m.group(1)), f"${m.group(1)} (parsed loosely)", 'est'
    return None, '', 'none'

# ---------------- audio pricing -> $/min output ----------------
def price_audio(t):
    t = t.replace('**', '').replace(' ', ' ')
    tl = t.lower()
    if 'per compute second' in tl:
        return None, 'billed per GPU compute-second', 'compute'
    m = re.search(r'\$([0-9.]+)\s*per minute', t, re.I)
    if m: return F(m.group(1)), f"${m.group(1)}/min", 'exact'
    m = re.search(r'\$([0-9.]+)\s*per\s*(\d+)\s*second\b', t, re.I)
    if m: return F(m.group(1)) * 60 / F(m.group(2)), f"${m.group(1)}/{m.group(2)}s -> x60", 'exact'
    m = re.search(r'\$([0-9.]+)\s*per audio\b', t, re.I)
    if m: return ('PER_CLIP', F(m.group(1))), '', 'clip'
    m = re.search(r'\$?([0-9.]+)\s*\$?\s*per 1,?000 characters?', t, re.I)
    if m: return F(m.group(1)) * 0.75, f"${m.group(1)}/1k chars x ~750 chars/min speech", 'est'
    m = re.search(r'\$([0-9.]+)\s*per\s*(?:generated|output)(?:\s*audio)?\s*minute', t, re.I)
    if m: return F(m.group(1)), f"${m.group(1)}/min", 'exact'
    m = re.search(r'\$([0-9.]+)\s*per output minute', t, re.I)
    if m: return F(m.group(1)), f"${m.group(1)}/min", 'exact'
    m = re.search(r'\$([0-9.]+)\s*per\s*(\d+)\s*s(?:econds?)?\s*of (?:output|generated)', t, re.I)
    if m: return F(m.group(1)) * 60 / F(m.group(2)), f"${m.group(1)}/{m.group(2)}s -> x60", 'exact'
    m = re.search(r'\$([0-9.]+)\s*per\s*(\d+)\s*second of generated audio', t, re.I)
    if m: return F(m.group(1)) * 60 / F(m.group(2)), f"${m.group(1)}/{m.group(2)}s -> x60", 'exact'
    m = re.search(r'\$?([0-9.]+)\s*per\s*(?:generated\s*)?(?:audio\s*)?seconds?\b', t, re.I)
    if m: return F(m.group(1)) * 60, f"${m.group(1)}/s x 60", 'exact'
    m = re.search(r'\$([0-9.]+)\s*per second of (?:generated |output )?audio', t, re.I)
    if m: return F(m.group(1)) * 60, f"${m.group(1)}/s x 60", 'exact'
    m = re.search(r'voice clone request will cost\s*\$([0-9.]+)', t, re.I)
    if m: return None, f"${m.group(1)} flat per clone", 'flat'
    m = re.search(r'\$([0-9.]+)\s*per created voice', t, re.I)
    if m: return None, f"${m.group(1)} flat per voice design", 'flat'
    if 'token' in tl: return None, 'token-based', 'token'
    m = re.search(r'\$([0-9.]+)\s*per (?:generation|request|video)', t, re.I)
    if m: return None, f"${m.group(1)} per request", 'flat'
    return None, '', 'none'

# ---------------- families ----------------
IMG_FAMS = [
 (r'flux-pro/kontext|flux-kontext', 'FLUX Kontext'), (r'flux-2|flux\.2', 'FLUX.2'),
 (r'flux-pro/v1\.1', 'FLUX 1.1 Pro'), (r'flux-pro', 'FLUX Pro'),
 (r'flux-krea|krea-flux|flux/krea', 'FLUX Krea'),
 (r'juggernaut-flux', 'Juggernaut FLUX'),
 (r'flux-lora|flux-general|flux/dev/lora', 'FLUX LoRA'),
 (r'flux-control|flux.*controlnet', 'FLUX ControlNet'),
 (r'fal-ai/flux', 'FLUX.1'),
 (r'ideogram', 'Ideogram'), (r'qwen-image-edit', 'Qwen Image Edit'), (r'qwen-image', 'Qwen Image'),
 (r'image-editing', 'fal Editing presets'), (r'image-apps', 'fal Image Apps'),
 (r'post-processing', 'Post-processing'), (r'image-preprocessors', 'Preprocessors'),
 (r'z-image', 'Z-Image'), (r'fibo', 'Bria FIBO'), (r'bria', 'Bria'),
 (r'recraft', 'Recraft'), (r'nano-banana-pro|nano-banana.*pro', 'Nano Banana Pro'),
 (r'nano-banana', 'Nano Banana'), (r'gemini', 'Gemini Image'), (r'gpt-image', 'GPT Image'),
 (r'seedream', 'Seedream'), (r'seededit', 'SeedEdit'),
 (r'kling-image|kolors.*virtual|kling.*try', 'Kling Image'), (r'kolors', 'Kolors'),
 (r'grok-imagine-image', 'Grok Imagine Image'), (r'luma-photon|luma/agent', 'Luma Photon'),
 (r'sana', 'Sana'), (r'hidream', 'HiDream'), (r'hunyuan-image', 'Hunyuan Image'),
 (r'ernie-image', 'Ernie Image'), (r'mai-image', 'Microsoft MAI'),
 (r'imagineart', 'ImagineArt'), (r'fooocus', 'Fooocus'),
 (r'/sam[-/2]|/sam$', 'SAM segmentation'), (r'florence', 'Florence vision'),
 (r'topaz|upscale|esrgan|clarity|supir|aura-sr|recraft.*upscale|seedvr', 'Upscalers'),
 (r'playground', 'Playground'), (r'krea/v2|krea/1', 'Krea'), (r'reve', 'Reve'),
 (r'patina', 'Patina'), (r'phota', 'Phota'),
 (r'sdxl-controlnet|fast-sdxl-controlnet|controlnet', 'SDXL ControlNet'),
 (r'finegrain|object-removal|eraser|erase', 'Object removal'),
 (r'vidu', 'Vidu Image'), (r'minimax', 'MiniMax Image'), (r'glm-image', 'GLM Image'),
 (r'boogu', 'Boogu'), (r'longcat-image', 'LongCat Image'), (r'kandinsky', 'Kandinsky Image'),
 (r'stable-diffusion|sdxl|lightning-sdxl|lcm|stable-cascade|fast-turbo|fast-sdxl', 'SD/SDXL legacy'),
 (r'wan/|wan-|wan22', 'Wan Image'), (r'bytedance', 'ByteDance Image misc'),
 (r'birefnet|rembg|background', 'Background removal'),
 (r'face|photomaker|pulid|instantid|swap', 'Face/identity'),
 (r'ben/|imageutils|workflow', 'Image utilities'),
 (r'omnigen', 'OmniGen'), (r'janus', 'Janus'), (r'lumina', 'Lumina'), (r'switti', 'Switti'),
 (r'infinity|emu', 'Autoregressive misc'), (r'retoucher|codeformer|restore', 'Restoration'),
 (r'moondream|llava|vision', 'Vision/captioning'),
 (r'joyai|hy-wu|firered|stepx-edit|dreamomni|chrono-edit|flowedit|/uso|/uno|omni-zero|bagel|seededit|inpaint$', 'Edit specialists misc'),
 (r'cat-vton|leffa|fashn|try-?on', 'Virtual try-on'),
 (r'iclight|control-light', 'Relighting'),
 (r'nafnet|docres|ddcolor|pasd|ccsr|drct|codeformer|retoucher', 'Restoration'),
 (r'ghiblify|cartoonify|image2pixel|telestyle', 'Stylize minis'),
 (r'pony|dreamshaper|illusion-diffusion', 'SD community minis'),
 (r'pixart|cogview4|aura-flow|omnigen|switti|bitdance|infinity|emu|janus|lumina', 'Open T2I minis'),
 (r'sensenova|nucleus-image|ovis|boogu', 'Labs T2I misc'),
 (r'instant-character|photomaker|pulid|live-portrait', 'Face/identity'),
 (r'hunyuan_world|hi3d|image3d', '3D/world minis'),
 (r'smart-resize|image2svg|invisible-watermark|ffmpeg|vecglypher|/rife|/film', 'Image utilities'),
 (r'product-photo|pixelcut', 'E-commerce tools'),
 (r'rundiffusion', 'Juggernaut FLUX'),
 (r'bernini', 'ByteDance Image misc'),
 (r'cosmos-3', 'NVIDIA Cosmos Image'),
 (r'fal-ai/lora$|fal-ai/lora/', 'SD/SDXL legacy'),
 (r'krea', 'Krea'),
 (r'evf-sam', 'SAM segmentation'), (r'feynobg', 'Background removal'), (r'dwpose', 'Preprocessors'),
]
AUD_FAMS = [
 (r'stable-audio', 'Stable Audio'), (r'minimax-music|minimax/music', 'MiniMax Music'),
 (r'minimax', 'MiniMax Speech'), (r'kokoro', 'Kokoro'),
 (r'elevenlabs.*sound|elevenlabs.*sfx', 'ElevenLabs SFX'), (r'elevenlabs', 'ElevenLabs'),
 (r'ace-step', 'ACE-Step'), (r'qwen.*tts|qwen-audio', 'Qwen TTS'), (r'fal-ai/qwen', 'Qwen TTS'),
 (r'mirelo', 'Mirelo SFX'), (r'chatterbox', 'Chatterbox'), (r'vibevoice', 'VibeVoice'),
 (r'maya', 'Maya TTS'), (r'lyria', 'Google Lyria'), (r'sonilo', 'Sonilo'),
 (r'fal-ai/ltx', 'LTX Audio'), (r'kling-video', 'Kling Audio'), (r'dia-tts', 'Dia TTS'),
 (r'sam-audio', 'SAM Audio'), (r'personaplex', 'PersonaPlex'), (r'tada', 'Tada TTS'),
 (r'workflow-utilities|ffmpeg', 'Audio utilities'), (r'cassetteai/music', 'CassetteAI Music'),
 (r'cassetteai/sound', 'CassetteAI SFX'), (r'seed-audio|bytedance', 'ByteDance Audio'),
 (r'gemini-tts|fal-ai/gemini', 'Gemini TTS'), (r'f5-tts', 'F5-TTS'), (r'mmaudio', 'MMAudio'),
 (r'diffrhythm', 'DiffRhythm'), (r'csm', 'Sesame CSM'), (r'zonos', 'Zonos'),
 (r'inworld', 'Inworld TTS'), (r'xai/tts', 'xAI TTS'), (r'index-tts', 'IndexTTS'),
 (r'orpheus', 'Orpheus TTS'), (r'async/tts', 'Async TTS'), (r'demucs', 'Demucs'),
 (r'audio-understanding', 'Audio understanding'), (r'deepfilternet', 'DeepFilterNet'),
 (r'american-audio|elevenlabs', 'ElevenLabs'),
]

def fam_of(eid, fams, fallback_lab):
    for pat, name in fams:
        if re.search(pat, eid, re.I): return name
    parts = eid.split('/')
    return (fallback_lab or parts[0]) + ' / ' + re.sub(r'[-_]?(v\d.*)$', '', parts[1] if len(parts) > 1 else parts[0])

MP = {'1k': 1.05, '2k': 4.2, '4k': 16.8}

def build(name):
    cat = json.load(open(f'all_{name}_models.json'))
    rows = []
    for eid, meta in cat.items():
        p = os.path.join('oas2', eid.replace('/', '__') + '.json')
        props, about = {}, ''
        if os.path.exists(p):
            try:
                d = json.load(open(p))
                if isinstance(d, dict):
                    props = schema_input(d).get('properties', {}) or {}
                    about = (((d.get('info') or {}).get('x-fal-metadata') or {}).get('about') or '')[:1200]
            except Exception: pass
        ptext = (meta.get('pricingInfoOverride') or '').strip() or page_pricing(eid)
        cats = meta.get('_cats') or []
        r = {'id': eid, 'title': meta.get('title'), 'lab': meta.get('modelLab'),
             'cats': cats, 'desc': (meta.get('shortDescription') or '').strip(),
             'about': about, 'price_text': ptext, 'props': sorted(props.keys())}
        if name == 'image':
            has_in = any(k in props for k in ('image_url', 'image_urls'))
            r['type'] = ('both' if ('text-to-image' in cats and 'image-to-image' in cats)
                         else 't2i' if 'text-to-image' in cats else 'i2i')
            v, basis, conf = price_image(ptext, has_in)
            r['usd'] = round(v, 4) if v is not None else None
            r['basis'], r['conf'] = basis, conf
            # max megapixels
            mp = None
            wlo, whi = numrange(props.get('width') or {}); hlo, hhi = numrange(props.get('height') or {})
            if whi and hhi: mp = whi * hhi / 1e6
            res_e = enum_of(props.get('resolution') or {})
            if res_e:
                got = [MP[str(x).lower()] for x in res_e if str(x).lower() in MP]
                if got: mp = max(max(got), mp or 0)
            sz = enum_of(props.get('image_size') or {})
            if mp is None and sz: mp = 1.05
            if mp is None and re.search(r'\b4k\b', (r['desc'] + about).lower()): mp = 16.8
            r['max_mp'] = round(mp, 1) if mp else None
            r['size_opts'] = (', '.join(str(x) for x in sz) if sz else
                              (f'custom up to {int(whi)}x{int(hhi)}' if whi and hhi else
                               (', '.join(str(x) for x in res_e) if res_e else 'fixed')))
            ar = enum_of(props.get('aspect_ratio') or {}) or enum_of(props.get('ratio') or {})
            r['aspect'] = ', '.join(str(x) for x in ar) if ar else ('via image_size' if sz else ('free' if whi else 'fixed'))
            r['img_input'] = 'Yes' if has_in else 'No'
            r['mask'] = 'Yes' if any(k in props for k in ('mask_url', 'mask_image_url')) else 'No'
            r['lora'] = 'Yes' if any(k in props for k in ('loras', 'embeddings')) else 'No'
            r['ref'] = 'Yes' if any(k in props for k in ('reference_image_urls', 'style', 'control_image_url', 'style_id', 'image_style_reference')) else 'No'
            blo, bhi = numrange(props.get('num_images') or {})
            r['batch'] = int(bhi) if bhi else 1
        else:
            txt = (eid + ' ' + r['desc']).lower()
            if 'text-to-speech' in cats or re.search(r'tts|speech', eid):
                ty = 'tts'
            elif 'speech-to-speech' in cats: ty = 's2s'
            elif 'audio-to-audio' in cats and 'text-to-audio' not in cats:
                ty = 'a2a'
            else:
                ty = 'music' if re.search(r'music|song|lyric|melody|beat|rhythm|compos', txt) else 'sfx'
            r['type'] = ty
            v, basis, conf = price_audio(ptext)
            if conf == 'clip':
                per_clip = v[1]
                dur = props.get('duration') or {}
                dd = dur.get('default')
                _, dmax = numrange(dur)
                secs = None
                try: secs = float(dd) if dd else (float(dmax) if dmax else None)
                except Exception: secs = None
                if not secs:
                    KNOWN_CLIP = {'stable-audio-25': 190, 'minimax-music': 240, 'lyria3': 30, 'lyria2': 30}
                    for kk, vv in KNOWN_CLIP.items():
                        if kk in eid: secs = vv; break
                if secs and secs > 0:
                    v = per_clip / (secs / 60)
                    basis = f"${per_clip} per clip / {secs:g}s default -> $/min"
                    conf = 'est'
                else:
                    v = None
                    basis = f"${per_clip} flat per clip (length not exposed)"
                    conf = 'flat'
            r['usd'] = round(v, 4) if v is not None else None
            r['basis'], r['conf'] = basis, conf
            dlo, dhi = numrange(props.get('duration') or {})
            de = enum_of(props.get('duration') or {})
            if de:
                nums = [float(re.sub(r'[^0-9.]', '', str(x)) or 0) for x in de]
                dhi = max([n for n in nums if n] or [None])
            m = re.search(r'up to (\d+)\s*(minutes|seconds|s\b|min)', (r['desc'] + about).lower())
            if dhi is None and m:
                dhi = float(m.group(1)) * (60 if 'min' in m.group(2) else 1)
            r['max_dur'] = dhi
            r['dur_opts'] = (', '.join(str(x) for x in de) + ' s' if de else
                             (f'{dlo:g}–{dhi:g} s' if dlo is not None and dhi else
                              ('follows text length' if ty in ('tts', 's2s') else
                               ('follows input audio' if ty == 'a2a' else 'model default'))))
            ve = enum_of(props.get('voice') or {}) or enum_of(props.get('voice_id') or {})
            r['voices'] = f'{len(ve)} preset voices' if ve else ('voice prop' if 'voice' in props or 'voice_id' in props else '—')
            le = enum_of(props.get('language') or {}) or enum_of(props.get('language_code') or {}) or enum_of(props.get('language_boost') or {})
            r['langs'] = f'{len(le)} languages' if le else '—'
            r['clone'] = 'Yes' if re.search(r'clone|voice.*(clon|design)', txt) or 'reference_audio_url' in props or ('audio_url' in props and ty == 'tts') else 'No'
            r['lyrics'] = 'Yes' if 'lyrics' in props or 'lyric' in txt else 'No'
            r['audio_in'] = 'Yes' if any(k in props for k in ('audio_url', 'audio_urls', 'reference_audio_url')) else 'No'
            fe = enum_of(props.get('output_format') or {}) or enum_of(props.get('format') or {})
            r['formats'] = ', '.join(str(x) for x in fe) if fe else 'default'
        r['family'] = fam_of(eid, IMG_FAMS if name == 'image' else AUD_FAMS, meta.get('modelLab'))
        rows.append(r)
    json.dump(rows, open(f'{name}_rows.json', 'w'), indent=1)
    priced = sum(1 for r in rows if r['usd'] is not None)
    import collections
    fams = collections.Counter(r['family'] for r in rows)
    print(f"== {name}: {len(rows)} rows, priced {priced}, conf:", collections.Counter(r['conf'] for r in rows))
    print(f"   families: {len(fams)}")
    for f, c in fams.most_common(): print(f'   {c:3} {f}')

build('image')
build('audio')
