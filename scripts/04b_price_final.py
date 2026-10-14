"""Final price engine: merge page-scraped pricing, normalize to $/min @720p."""
import json, re

rows = json.load(open('priced.json'))
pages = json.load(open('page_pricing.json'))
MP720 = 1280 * 720 / 1e6
TOK720 = 1280 * 720 / 1024

# Known default/typical clip length (seconds) for endpoints billed per-video.
PER_VIDEO_SECONDS = {
    'fal-ai/minimax/video-01': 6, 'fal-ai/minimax/video-01-live': 6,
    'fal-ai/minimax/video-01-director': 6, 'fal-ai/minimax/video-01/image-to-video': 6,
    'fal-ai/minimax/video-01-live/image-to-video': 6,
    'fal-ai/minimax/video-01-director/image-to-video': 6,
    'fal-ai/minimax/video-01-subject-reference': 6,
    'fal-ai/hunyuan-video': 5, 'fal-ai/hunyuan-video-image-to-video': 5,
    'fal-ai/hunyuan-video-img2vid-lora': 5,
    'fal-ai/ovi': 5, 'fal-ai/ovi/image-to-video': 5,
    'fal-ai/wan/v2.2-5b/text-to-video/distill': 5,
    'fal-ai/wan/v2.2-5b/text-to-video': 5, 'fal-ai/wan/v2.2-5b/image-to-video': 5,
    'fal-ai/wan/v2.2-5b/text-to-video/fast-wan': 5,
    'fal-ai/wan-t2v': 5, 'fal-ai/wan-i2v': 5, 'fal-ai/wan-flf2v': 5,
    'fal-ai/wan-t2v-lora': 5, 'fal-ai/wan-i2v-lora': 5, 'fal-ai/wan-effects': 5,
    'fal-ai/wan/v2.2-a14b/text-to-video': 5, 'fal-ai/wan/v2.2-a14b/image-to-video': 5,
    'fal-ai/wan/v2.2-a14b/text-to-video/lora': 5, 'fal-ai/wan/v2.2-a14b/image-to-video/lora': 5,
    'fal-ai/wan/v2.2-a14b/text-to-video/turbo': 5, 'fal-ai/wan/v2.2-a14b/image-to-video/turbo': 5,
    'fal-ai/wan-pro/text-to-video': 6, 'fal-ai/wan-pro/image-to-video': 6,
    'fal-ai/ltx-video': 5, 'fal-ai/ltx-video/image-to-video': 5, 'fal-ai/ltx-video-v095': 5,
    'fal-ai/ltx-video-13b-distilled': 5, 'fal-ai/ltx-video-13b-distilled/image-to-video': 5,
    'fal-ai/ltxv-13b-098-distilled': 5, 'fal-ai/ltxv-13b-098-distilled/image-to-video': 5,
    'fal-ai/cogvideox-5b': 5, 'fal-ai/cogvideox-5b/image-to-video': 5,
    'fal-ai/infinity-star/text-to-video': 5,
    'fal-ai/cosmos-predict-2.5/text-to-video': 93 / 16,
    'fal-ai/cosmos-predict-2.5/image-to-video': 93 / 16,
    'fal-ai/cosmos-predict-2.5/distilled/text-to-video': 93 / 16,
    'fal-ai/pika/v2.1/text-to-video': 5, 'fal-ai/pika/v2.1/image-to-video': 5,
    'fal-ai/pika/v2/turbo/text-to-video': 5, 'fal-ai/pika/v2/turbo/image-to-video': 5,
    'fal-ai/pika/v2.2/text-to-video': 5, 'fal-ai/pika/v2.2/image-to-video': 5,
    'fal-ai/pika/v2.2/pikascenes': 5, 'fal-ai/pika/v2.2/pikaframes': 5,
    'fal-ai/minimax/hailuo-2.3/pro/text-to-video': 6,
    'fal-ai/minimax/hailuo-2.3/pro/image-to-video': 6,
    'fal-ai/minimax/hailuo-2.3-fast/pro/image-to-video': 6,
    'fal-ai/magi-distilled': 4, 'fal-ai/magi-distilled/image-to-video': 4,
    'fal-ai/stable-video': 4, 'fal-ai/fast-svd/text-to-video': 4,
    'fal-ai/fast-svd-lcm': 4, 'fal-ai/fast-svd-lcm/text-to-video': 4,
    'fal-ai/framepack': 5, 'fal-ai/framepack/f1': 5, 'fal-ai/framepack/flf2v': 5,
    'fal-ai/vidu/template-to-video': 4, 'fal-ai/vidu/image-to-video': 4,
    'fal-ai/kandinsky5/text-to-video': 5, 'fal-ai/kandinsky5/text-to-video/distill': 5,
    'bytedance/lynx': 5, 'fal-ai/bytedance/omnihuman': 5,
    'fal-ai/luma-dream-machine/ray-2': 5, 'fal-ai/luma-dream-machine/ray-2/image-to-video': 5,
    'fal-ai/decart/lucy-5b/image-to-video': 5,
    'fal-ai/wan-25-preview/text-to-video': 5, 'fal-ai/wan-25-preview/image-to-video': 5,
}


def clean(t):
    return (t or '').replace('**', '').replace(' ', ' ')


def dur_default_secs(r):
    for k in ('duration_default',):
        v = r.get(k)
        if v is None: continue
        try:
            n = float(re.sub(r'[^0-9.]', '', str(v)))
            if 0 < n <= 120: return n
        except Exception: pass
    nf, fpsv = r.get('num_frames_default'), r.get('fps_default') or 24
    if isinstance(nf, (int, float)) and nf > 1:
        try: return float(nf) / float(fpsv)
        except Exception: pass
    return None


def fps_of(r):
    v = r.get('fps_default')
    if isinstance(v, (int, float)) and 8 <= v <= 60: return float(v)
    t = (r['pricing_raw'] + ' ' + r['about']).lower()
    m = re.search(r'calculated at (\d+) frames per second', t)
    if m: return float(m.group(1).rstrip("."))
    v = r.get('fps_min')
    if isinstance(v, (int, float)) and 8 <= v <= 60: return float(v)
    return 24.0


def compute(r, t):
    """t = pricing text. Returns (usd_per_min_720p, basis, flag)."""
    tl = t.lower()
    fps = fps_of(r)
    eid = r['id']

    if 'per compute second' in tl:
        return None, 'billed per GPU compute-second (varies with runtime)', 'compute'

    # --- Oct 2026 phrasings ---
    if re.search(r'\$0 per compute second', t):      # placeholder copy on unlisted pages
        return None, '', 'none'
    # Seedance 2.5 draft -> complete: billed at the 1080p rate
    m = re.search(r'cost roughly \$([0-9.]+) per second of generated video', t, re.I)
    if m and 'draft' in eid:
        v = float(m.group(1).rstrip('.'))
        return v * 60, f"${v}/s x 60s (1080p render of a 480p draft; no 720p tier)", 'exact'
    # "For every second of 720p video you generated, ... $0.37/second" (Seedance US)
    m = re.search(r'second of 720p video[^.]*?\$([0-9.]+)\s*(?:/|per\s*)\s*second', t, re.I)
    if m:
        return float(m.group(1).rstrip('.')) * 60, f"${m.group(1)}/s @720p x 60s", 'exact'
    # price immediately before its tier: "$0.01 per second at 720p" (Boreal) —
    # must win over "at 720p, $0.03 per second at 1080p" read the other way round
    m = re.search(r'\$([0-9.]+)\s*(?:/|per\s*)\s*sec(?:ond)?(?:\s+of\s+[\w ]{0,25}?)?\s*(?:at|for)\s*720p\b', t, re.I)
    if m:
        return float(m.group(1).rstrip('.')) * 60, f"${m.group(1)}/s @720p x 60s", 'exact'
    # tier then price: "720p at $0.14/sec" (Grok) — before the bare-tier rule below,
    # which would otherwise grab "$0.70 at 720p" from the 5-second example
    m = re.search(r'\b720p\s*(?:at|:)\s*\$([0-9.]+)\s*(?:/|per\s*)\s*sec', t, re.I)
    if m:
        return float(m.group(1).rstrip('.')) * 60, f"${m.group(1)}/s @720p x 60s", 'exact'
    # per-second copy with a bare tier list: "$0.05 480p, $0.10 720p" / "$0.14 at 720p"
    if re.search(r'(?:every|per) second', tl):
        m = re.search(r'\$([0-9.]+)\s*(?:at|for)?\s*720p\b', t, re.I)
        if m:
            return float(m.group(1).rstrip('.')) * 60, f"${m.group(1)}/s @720p x 60s", 'exact'
    # Veo 3.1 Lite: "$0.05 for 720p with audio, $0.03 for 720p without audio"
    m = re.search(r'\$([0-9.]+)\s*for 720p without audio', t, re.I)
    if m:
        on = re.search(r'\$([0-9.]+)\s*for 720p with audio', t, re.I)
        v = float(m.group(1).rstrip('.'))
        ex = f"; audio-on ${float(on.group(1).rstrip('.'))*60:.2f}/min" if on else ''
        return v * 60, f"${v}/s @720p no-audio x 60s{ex}", 'exact'
    # Topaz: "At 30 fps, 10 seconds costs $1.20 up to 1080p" (1080p is the floor tier)
    m = re.search(r'(\d+)\s*seconds? costs \$([0-9.]+)\s*(?:up to|at) 1080p', t, re.I)
    if m:
        n, v = float(m.group(1)), float(m.group(2).rstrip('.'))
        return v / n * 60, f"${v} per {n:g}s @1080p -> x60 (no 720p tier)", 'exact'
    # Topaz interpolate: "a 10-second 30->60 fps job, Apollo or Chronos costs $0.30 at 1080p"
    m = re.search(r'(\d+)-second [^.]*?costs \$([0-9.]+)\s*at 1080p', t, re.I)
    if m:
        n, v = float(m.group(1)), float(m.group(2).rstrip('.'))
        return v / n * 60, f"${v} per {n:g}s of 60fps 1080p -> x60", 'exact'
    # Kandinsky 6: "$1.35 per 5-second 480p video" (native 480p, no 720p tier)
    m = re.search(r'\$([0-9.]+)\s*per\s*(\d+)-second\s*(\d{3,4}p)\s*video', t, re.I)
    if m:
        v, n, res = float(m.group(1).rstrip('.')), float(m.group(2)), m.group(3)
        return v / n * 60, f"${v} per {n:g}s @{res} (native; no 720p tier) -> x60", 'exact'
    # Kandinsky VSR: "$0.00036 per output megapixel per frame" -> 1080p output @24fps
    m = re.search(r'\$([0-9.]+)\s*per output megapixel per frame', t, re.I)
    if m:
        v = float(m.group(1).rstrip('.'))
        return v * 2.0736 * 24 * 60, f"${v}/MP/frame x 2.07 MP (1080p output) x 24fps x 60s", 'calc'
    # SAM Audio: "$0.05 per 30s of output audio"
    m = re.search(r'\$([0-9.]+)\s*per\s*(\d+)s of output', t, re.I)
    if m:
        v, n = float(m.group(1).rstrip('.')), float(m.group(2))
        return v / n * 60, f"${v} per {n:g}s -> x60", 'exact'

    # --- "$X per megapixel per second" (video upscalers): MP x $/MP/s x 60s,
    #     no frame-rate multiplier (rate is already per second of video) ---
    m = re.search(r'\$?([0-9.]+)\s*\$?\s*per megapixel per second', t, re.I)
    if m:
        mp = float(m.group(1).rstrip('.'))
        return mp * MP720 * 60, f"${mp}/MP/s x 0.9216 MP x 60s (<=30fps tier)", 'exact'

    # --- megapixel of generated data (LTX 2.x): per-frame area x fps ---
    m = re.search(r'\$?([0-9.]+)\s*\$?\s*per megapixel', t, re.I)
    if m:
        mp = float(m.group(1).rstrip("."))
        return mp * MP720 * fps * 60, f"${mp}/MP x 0.9216 MP/frame x {fps:g}fps x 60s", 'calc'

    # --- explicit 720p per-second ---
    m = re.search(r'(?:for|at)\s*720p[^.]{0,90}?\$([0-9.]+)\s*(?:/|per\s*)?\s*(?:of\s*)?second', t, re.I)
    if m: return float(m.group(1).rstrip(".")) * 60, f"${m.group(1)}/s @720p x 60s", 'exact'
    m = re.search(r'720p[^.]{0,50}?,?\s*every second costs\s*\$?([0-9.]+)', t, re.I)
    if m: return float(m.group(1).rstrip(".")) * 60, f"${m.group(1)}/s @720p x 60s", 'exact'
    m = re.search(r'\b720p\b\s*(?:at|:)?\s*\$([0-9.]+)\s*/?\s*(?:per\s*)?sec', t, re.I)
    if m: return float(m.group(1).rstrip(".")) * 60, f"${m.group(1)}/s @720p x 60s", 'exact'
    m = re.search(r'\$([0-9.]+)\s*(?:/|per\s*)second[^.]{0,50}?\b720p\b', t, re.I)
    if m: return float(m.group(1).rstrip(".")) * 60, f"${m.group(1)}/s @720p x 60s", 'exact'
    m = re.search(r'for 720\s*p[^.]{0,60}?([0-9.]+)\s*\$\s*(?:for )?(?:every|each)\s*video second', t, re.I)
    if m: return float(m.group(1).rstrip(".")) * 60, f"${m.group(1)}/s @720p x 60s", 'exact'

    # --- per-1000-tokens (Seedance) ---
    m = re.search(r'\$?([0-9.]+)\s*per 1000 tokens', t, re.I)
    if m:
        tk = float(m.group(1).rstrip("."))
        return tk * (TOK720 * fps * 60) / 1000, f"${tk}/1k tok, 720p@{fps:g}fps x 60s", 'calc'
    m = re.search(r'1 million video tokens[^.$]{0,30}\$?\s*([0-9.]+)', t, re.I)
    if m:
        tk = float(m.group(1).rstrip('.'))
        return tk * (TOK720 * fps * 60) / 1e6, f"${tk}/1M tok, 720p@{fps:g}fps x 60s", 'calc'

    # --- "charged $X without audio or $Y with audio for 720p or 1080p" (Veo) ---
    m = re.search(r'charged\s*\$([0-9.]+)\s*without audio(?:\s*,?\s*or\s*\$([0-9.]+)\s*with audio)?[^.]{0,40}?(?:for\s*)?720p', t, re.I)
    if m:
        v = float(m.group(1).rstrip('.'))
        ex = f"; audio-on ${float(m.group(2).rstrip('.'))*60:.2f}/min" if m.group(2) else ''
        return v * 60, f"${v}/s @720p no-audio x 60s{ex}", 'exact'
    m = re.search(r'\$([0-9.]+)\s*without audio or\s*\$([0-9.]+)\s*with audio[^.]{0,40}720p', t, re.I)
    if m:
        v = float(m.group(1).rstrip('.'))
        return v * 60, f"${v}/s @720p no-audio x 60s; audio-on ${float(m.group(2).rstrip('.'))*60:.2f}/min", 'exact'

    # --- audio off/on per second ---
    m = re.search(r'\$([0-9.]+)\s*\(audio off\)', t, re.I)
    if m:
        v = float(m.group(1).rstrip('.'))
        m2 = re.search(r'\$([0-9.]+)\s*\(audio on\)', t, re.I)
        ex = f"; audio-on ${float(m2.group(1).rstrip('.'))*60:.2f}/min" if m2 else ''
        return v * 60, f"${v}/s audio-off x 60s{ex}", 'exact'

    # --- "For 5s video ... $X" + additional second ---
    m = re.search(r'for\s*\*?\*?(\d+)\s*s(?:econd)?s?\b[^.]{0,50}?cost\s*\$?\s*([0-9.]+)', t, re.I)
    m2 = re.search(r'(?:aditional|additional)\s*seconds?[^.$]{0,40}\$?\s*([0-9.]+)', t, re.I)
    if m and m2:
        base, n, add = float(m.group(2).rstrip('.')), float(m.group(1).rstrip(".")), float(m2.group(1).rstrip('.'))
        return base + (60 - n) * add, f"${base}/{n:g}s + ${add}/extra s", 'exact'

    # --- Pixverse: "0.4$ for 720p" within a 5s statement ---
    m = re.search(r'for\s*(\d+)s video[\s\S]{0,120}?([0-9.]+)\s*\$\s*for 720p', t, re.I)
    if m:
        n, v = float(m.group(1).rstrip(".")), float(m.group(2).rstrip("."))
        return v / n * 60, f"${v} per {n:g}s @720p -> x60", 'exact'

    # --- Pixverse: "For [a] 5s video ... $0.2 for 720p"  (also "0.4$ for 720p") ---
    m = re.search(r'for\s*(?:a\s*)?(\d+)[\s-]*s(?:econd)?\s*video[\s\S]{0,140}?\$([0-9.]+)\s*for\s*720p', t, re.I)
    if not m:
        m = re.search(r'for\s*(?:a\s*)?(\d+)[\s-]*s(?:econd)?\s*video[\s\S]{0,140}?([0-9.]+)\s*\$\s*for\s*720p', t, re.I)
    if m:
        n, v = float(m.group(1)), float(m.group(2).rstrip('.'))
        return v / n * 60, f"${v} per {n:g}s @720p -> x60", 'exact'

    # --- Vidu/simple: "For 5s video your request will cost $0.40." ---
    m = re.search(r'for\s*(?:a\s*)?(\d+)[\s-]*s(?:econd)?\s*video[^.]{0,60}?cost\s*\$([0-9.]+)\s*\.?\s*$', t.strip(), re.I)
    if not m:
        m = re.search(r'for\s*(?:a\s*)?(\d+)[\s-]*s(?:econd)?\s*video[^.]{0,60}?cost\s*\$([0-9.]+)', t, re.I)
    if m:
        n, v = float(m.group(1)), float(m.group(2).rstrip('.'))
        return v / n * 60, f"${v} per {n:g}s -> x60", 'exact'

    # --- "$0.4 at 720p resolution" (wan) / "$0.10 per video for 720p" ---
    m = re.search(r'([0-9.]+)\s*\$\s*at 720p', t, re.I) or re.search(r'\$([0-9.]+)\s*at 720p', t, re.I)
    if not m:
        m = re.search(r'\$([0-9.]+)\s*per video for 720p', t, re.I)
    if m:
        v = float(m.group(1).rstrip('.'))
        n = PER_VIDEO_SECONDS.get(eid) or dur_default_secs(r) or 5
        return v / n * 60, f"${v} per {n:g}s 720p video -> x60", 'est'

    # --- "5 second video at 720p costs $0.20" (Pika) ---
    m = re.search(r'(\d+)\s*second video at 720p costs\s*\$([0-9.]+)', t, re.I)
    if m:
        return float(m.group(2).rstrip('.')) / float(m.group(1).rstrip(".")) * 60, f"${m.group(2)} per {m.group(1)}s @720p -> x60", 'exact'

    # --- "Each [1080p] N second video costs roughly $X" ---
    m = re.search(r'each\s*(\d{3,4}p)?\s*(\d+)\s*second video[^.]{0,40}?\$([0-9.]+)', t, re.I)
    if m and (m.group(1) or '').lower() in ('', '720p'):
        return float(m.group(3).rstrip('.')) / float(m.group(2).rstrip(".")) * 60, f"${m.group(3)} per {m.group(2)}s -> x60", 'exact'

    # --- "$X per N second video generation" / "$X for a N-second video" ---
    for pat in (r'\$([0-9.]+)\s*per\s*(\d+)\s*second video',
                r'\$([0-9.]+)\s*for (?:a|one)?\s*(\d+)[- ]second video',
                r'\$([0-9.]+)\s*for a (\d+)s video',
                r'\$([0-9.]+)\s*per\s*(\d+)\s*second\b'):
        m = re.search(pat, t, re.I)
        if m:
            return float(m.group(1).rstrip('.')) / float(m.group(2).rstrip(".")) * 60, f"${m.group(1)} per {m.group(2)}s -> x60", 'exact'
    m = re.search(r'\$([0-9.]+)\s*to generate one four-second video', t, re.I)
    if m:
        return float(m.group(1).rstrip(".")) / 4 * 60, f"${m.group(1)} per 4s -> x60", 'exact'

    # --- per minute ---
    m = re.search(r'\$([0-9.]+)\s*per minute', t, re.I)
    if m: return float(m.group(1).rstrip('.')), f"${m.group(1)}/min", 'exact'

    # --- plain per-second variants ---
    for pat in (r'\$([0-9.]+)\s*per\s*(?:output|generated|input)?\s*(?:video\s*)?second',
                r'\$([0-9.]+)\s*/\s*sec',
                r'charged\s*\$([0-9.]+)\s*\.?\s*(?:for every second|per second)',
                r'(?:for every second|each second|per second of)[^.$]{0,60}\$([0-9.]+)',
                r'\$([0-9.]+)\s*per second'):
        m = re.search(pat, t, re.I)
        if m: return float(m.group(1).rstrip('.')) * 60, f"${m.group(1)}/s x 60s", 'exact'

    m = re.search(r'([0-9.]+)\s*cents?\s*/\s*s', t, re.I)
    if m: return float(m.group(1).rstrip(".")) / 100 * 60, f"{m.group(1)} cents/s x 60s", 'exact'

    # --- "$0.17 $ per second ... at 720p" reversed / generic "N $ per second" ---
    m = re.search(r'([0-9.]+)\s*\$\s*per second[^.]{0,40}?720p', t, re.I)
    if m: return float(m.group(1).rstrip(".")) * 60, f"${m.group(1)}/s @720p x 60s", 'exact'

    # --- per video (flat), use known duration ---
    m = re.search(r'\$?([0-9.]+)\s*\$?\s*(?:per|for every)\s*(?:generated\s*)?video', t, re.I)
    if m:
        v = float(m.group(1).rstrip('.'))
        n = PER_VIDEO_SECONDS.get(eid) or dur_default_secs(r)
        if n: return v / n * 60, f"${v} per {n:.4g}s video -> x60", 'est'
        return None, f"${v} per video (clip length not fixed)", 'flat'

    # --- vidu style: "0.07 $ per video second for 360p and 540p, 2.2x for 720p" ---
    m = re.search(r'([0-9.]+)\s*\$?\s*per video second for 360p and 540\s*p[^.]{0,60}?([0-9.]+)x for 720p', t, re.I)
    if m:
        return float(m.group(1).rstrip(".")) * float(m.group(2).rstrip(".")) * 60, f"${m.group(1)}/s x {m.group(2)}x (720p) x 60s", 'calc'

    return None, '', 'none'


# --------------------------------------------------------------------------
# Promotional pricing (Oct 2026: MiniMax H3-Max / H3-Max Turbo until Oct 15,
# Vidu Q4 until Nov 30). Convention: the table records the REGULAR rate fal
# states will apply after the promo, and the basis names the promo price and
# its end date. A promo price is a moving target; the list price is what a
# pipeline will pay a month from now.
# --------------------------------------------------------------------------
TIER_PREF = ['720p', '768p', '1080p', '540p', '580p', '480p']


def promo_regular(t):
    """-> (usd_per_sec, res, end) for the post-promo 720p-nearest tier, or None."""
    if not re.search(r'promotional|promo rate|launch rate', t, re.I):
        return None
    m = re.search(r'(?:after which|list price being|regular price)(.*)', t, re.I | re.S)
    if not m:
        return None
    seg = m.group(1)
    tiers = {}
    for res, v in re.findall(r'\b(\d{3,4}p|2K|4K)\s*(?:is|:|at)\s*\$([0-9.]+)', seg, re.I):
        tiers.setdefault(res.lower(), float(v.rstrip('.')))
    if not tiers:
        v = re.search(r'\$([0-9.]+)\s*(?:/|per\s*)\s*second', seg, re.I)
        if v:
            tiers['any'] = float(v.group(1).rstrip('.'))
    res = next((x for x in TIER_PREF if x in tiers), None) or (next(iter(tiers)) if tiers else None)
    if not res:
        return None
    end = re.search(r'(?:ends|until|expires on)\s*([A-Z][a-z]+ \d{1,2})', t)
    pre = t[:m.start()]
    promo = None
    for v, r_ in re.findall(r'\$([0-9.]+)(?:\s*(?:/|per\s*)\s*sec(?:ond)?)?\s*(?:at|for)\s*(\d{3,4}p|2K|4K)\b', pre, re.I):
        if r_.lower() == res:
            promo = float(v.rstrip('.'))
            break
    if promo is None and res == 'any':
        pm = re.search(r'\$([0-9.]+)\s*per second', pre, re.I)
        promo = float(pm.group(1).rstrip('.')) if pm else None
    return tiers[res], res, end.group(1) if end else '', promo


def nearest_tier(t):
    """Per-second tiers with no 720p tier (MiniMax H3 is 480p/768p/2K/4K)."""
    tiers = {}
    for v, res in re.findall(r'\$([0-9.]+)(?:\s*(?:/|per\s*)\s*sec(?:ond)?(?:\s+of\s+[\w ]{0,25}?)?)?\s*(?:at|for)\s*(\d{3,4}p|2K|4K)\b', t, re.I):
        tiers.setdefault(res.lower(), float(v.rstrip('.')))
    if '720p' in tiers or not tiers:
        return None
    res = next((x for x in TIER_PREF if x in tiers), None)
    return (tiers[res], res) if res else None


VIDU_MULT = re.compile(r'cost will be ([0-9.]+)x for 720p', re.I)

for r in rows:
    if r['pricing_raw'].strip() in ('$undefined', 'undefined'):   # unlisted/deprecated records
        r['pricing_raw'] = ''
    txt = clean(r['pricing_raw'])
    src = 'model metadata'
    if not txt:
        pv = pages.get(r['id']) or []
        txt = clean(pv[0]) if pv else ''
        src = 'model page' if txt else ''
    # vidu special: base per-second for 360/540p, 2.2x for 720p
    if 'per video second for 360p' in txt.lower():
        b = re.search(r'([0-9.]+)\s*\$\s*per video second', txt, re.I)
        mm = VIDU_MULT.search(txt)
        if b and mm:
            v = float(b.group(1).rstrip(".")) * float(mm.group(1).rstrip("."))
            r['usd_per_min_720p'] = round(v * 60, 2)
            r['price_basis'] = f"${b.group(1)}/s x {mm.group(1)}x @720p x 60s"
            r['price_conf'] = 'calc'; r['price_text'] = txt; r['price_src'] = src
            continue
    v, basis, conf = compute(r, txt)
    nt = nearest_tier(txt) if re.search(r'(?:per|every) second|/\s*sec|/s\b', txt, re.I) else None
    if nt and conf in ('exact', 'none'):
        v, basis, conf = nt[0] * 60, f"${nt[0]}/s @{nt[1]} (no 720p tier; nearest) x 60s", 'exact'
    pr = promo_regular(txt)
    if pr:
        promo = f"; promo ${pr[3]:.4g}/s" if pr[3] else '; promo rate'
        v, basis, conf = (pr[0] * 60,
                          f"${pr[0]}/s @{pr[1]} regular rate x 60s{promo} until {pr[2] or 'unstated date'}",
                          'exact')
    r['usd_per_min_720p'] = round(v, 2) if v else None
    r['price_basis'] = basis
    r['price_conf'] = conf
    r['price_text'] = txt
    r['price_src'] = src

json.dump(rows, open('priced2.json', 'w'), indent=1)
ok = sum(1 for r in rows if r['usd_per_min_720p'])
print(f'priced: {ok}/{len(rows)}')
import collections
print(collections.Counter(r['price_conf'] for r in rows))
for r in rows:
    if not r['usd_per_min_720p'] and r['price_conf'] not in ('compute',):
        print(' MISS', r['id'], '||', r['price_text'][:110])

MANUAL = {
    'fal-ai/wan-pro/text-to-video':  (8.00, '$0.80 per 6s 1080p clip -> x60 (1080p-only model)', 'est'),
    'fal-ai/wan-pro/image-to-video': (8.00, '$0.80 per 6s 1080p clip -> x60 (1080p-only model)', 'est'),
    'fal-ai/kandinsky5-pro/text-to-video':  (7.20, '$0.12/s @1024p x 60s (no 720p tier)', 'est'),
    'fal-ai/kandinsky5-pro/image-to-video': (7.20, '$0.12/s @1024p x 60s (no 720p tier)', 'est'),
    'fal-ai/vidu/template-to-video': (3.00, '$0.20 standard template per 4s -> x60', 'est'),
    'fal-ai/hunyuan-video-img2vid-lora': (4.80, '$0.40 per 5s video -> x60 (same as hunyuan-video)', 'est'),
    'fal-ai/fast-svd-lcm': (None, 'billed per GPU compute-second (varies with runtime)', 'compute'),
    # fal's blurb says "0.075 cents/s"; the page body says $0.075 per second (README)
    'fal-ai/hunyuan-video-v1.5/text-to-video': (4.50, "$0.075/s x 60s (fal's '0.075 cents/s' blurb is a typo; page body says $0.075/s)", 'exact'),
    # unlisted endpoints whose page shows only "$0 per compute second": sibling rate, flagged est
    'fal-ai/veo3.1/lite/reference-to-video': (1.80, '$0.03/s @720p no-audio x 60s (no published rate; Veo 3.1 Lite i2v sibling)', 'est'),
    'fal-ai/pixverse/v6/reference-to-video': (2.70, '$0.045/s @720p no-audio x 60s (no published rate; Pixverse V6 i2v sibling)', 'est'),
}
for r in rows:
    if r['id'] in MANUAL:
        v, b, c = MANUAL[r['id']]
        r['usd_per_min_720p'] = v
        r['price_basis'] = b
        r['price_conf'] = c
json.dump(rows, open('priced2.json', 'w'), indent=1)
ok2 = sum(1 for r in rows if r['usd_per_min_720p'])
print('after manual:', ok2, '/', len(rows))
import collections as _c
print(_c.Counter(r['price_conf'] for r in rows))
print('still missing (non-compute):', [r['id'] for r in rows if not r['usd_per_min_720p'] and r['price_conf']!='compute'])


# --------------------------------------------------------------------------
# Carry-forward (Oct 2026). The Aug passes priced some video-to-video copy
# (per-N-frames background removal, SAM, 1080p-floor upscalers, per-video
# utilities) with rules that never reached this script. Where an endpoint's
# pricing copy is UNCHANGED since the committed data, the committed figure is
# the same normalisation of the same input, so it is carried forward verbatim.
# Changed copy is never carried: it is re-parsed above or left unpriced.
# --------------------------------------------------------------------------
import os as _os
_prev_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'data', 'models.json')
_norm = lambda t: re.sub(r'\s+', ' ', (t or '').replace('**', '').replace('*', '')).strip()
if _os.path.exists(_prev_path):
    _prev = {p['id']: p for p in json.load(open(_prev_path))}
    carried = []
    for r in rows:
        p = _prev.get(r['id'])
        if r['usd_per_min_720p'] or r['price_conf'] == 'compute' or not p:
            continue
        if _norm(p.get('price_text')) == _norm(r['price_text']) and (p.get('price_basis') or p.get('usd_per_min_720p')):
            r['usd_per_min_720p'] = p['usd_per_min_720p']
            r['price_basis'] = p['price_basis']
            r['price_conf'] = p.get('price_conf') or 'exact'
            carried.append(r['id'])
    json.dump(rows, open('priced2.json', 'w'), indent=1)
    print(f'carried forward (unchanged copy): {len(carried)}')
print('final still missing (non-compute):',
      [r['id'] for r in rows if not r['usd_per_min_720p'] and r['price_conf'] not in ('compute', 'token')])
