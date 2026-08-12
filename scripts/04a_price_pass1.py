"""Normalize every fal.ai video model's pricing to $/minute of 720p output."""
import json, re

rows = json.load(open('extracted.json'))
MP720 = 1280 * 720 / 1e6          # 0.9216 MP per 720p frame
TOK720 = 1280 * 720 / 1024        # tokens per 720p frame per fal's formula


def clean(t):
    return t.replace('**', '').replace('*', '').replace(' ', ' ')


def nums(pat, t, flags=re.I):
    out = []
    for m in re.finditer(pat, t, flags):
        g = [x for x in m.groups() if x]
        out.append(g)
    return out


def fps_of(r):
    """Best-guess output fps for the endpoint."""
    for k in ('fps_default', 'fps_min'):
        v = r.get(k)
        if isinstance(v, (int, float)) and 8 <= v <= 60:
            return float(v)
    if r.get('fps_enum'):
        try:
            return float(sorted(float(str(x).rstrip('fps ')) for x in r['fps_enum'])[-1])
        except Exception:
            pass
    t = (r['pricing_raw'] + ' ' + r['about']).lower()
    m = re.search(r'calculated at (\d+) frames per second', t)
    if m: return float(m.group(1))
    if '15 frames per second' in t: return 15.0
    if '16 frames per second' in t: return 16.0
    if '30 frames per second' in t: return 30.0
    return 24.0


def compute(r):
    """Return (usd_per_min_720p, basis_string)."""
    t = clean(r['pricing_raw'])
    tl = t.lower()
    fps = fps_of(r)

    # ---- 1. per-megapixel (LTX family) ----
    m = re.search(r'\$?([0-9.]+)\s*\$?\s*per megapixel', t, re.I)
    if m:
        mp = float(m.group(1))
        return mp * MP720 * fps * 60, f"${mp}/MP x 0.9216MP x {fps:g}fps x 60s"

    # ---- 2. per-1000-tokens (Seedance 2.x) ----
    m = re.search(r'\$?([0-9.]+)\s*per 1000 tokens', t, re.I)
    persec = re.search(r'(?:for|at)\s*720p[^.]{0,80}?\$([0-9.]+)\s*(?:/|per\s*)?second', t, re.I)
    if persec:
        return float(persec.group(1)) * 60, f"${persec.group(1)}/s at 720p x 60s"
    if m:
        tk = float(m.group(1))
        return tk * (TOK720 * 24 * 60) / 1000, f"${tk}/1k tok x 720p@24fps x 60s"

    # ---- 3. explicit resolution -> $/sec tables ----
    # "480p at $0.08/sec, 720p at $0.14/sec"
    pairs = nums(r'(\d{3,4}p|4k|2k)\s*(?:at|:)?\s*\$([0-9.]+)\s*/?\s*(?:per\s*)?sec', t)
    d = {}
    for g in pairs:
        try: d[g[0].lower()] = float(g[1].rstrip('.'))
        except Exception: pass
    # "$0.17 $ per second of generated video at 720p, and 0.29 $ per second at 1080p"
    for g in nums(r'([0-9.]+)\s*\$?\s*per second[^.]{0,40}?(\d{3,4}p|4k|2k)', t):
        try: d.setdefault(g[1].lower(), float(g[0].rstrip('.')))
        except Exception: pass
    for g in nums(r'\$([0-9.]+)\s*per\s*(\d{3,4}P|4K|2K)\s*video second', t):
        try: d.setdefault(g[1].lower(), float(g[0].rstrip('.')))
        except Exception: pass
    if '720p' in d:
        return d['720p'] * 60, f"${d['720p']}/s at 720p x 60s"

    # ---- 4. audio-off / audio-on per second (Kling, Veo) ----
    m = re.search(r'charged\s*\$([0-9.]+)\s*\(audio off\)', t, re.I)
    if m:
        v = float(m.group(1).rstrip('.'))
        m2 = re.search(r'\$([0-9.]+)\s*\(audio on\)', t, re.I)
        extra = f" / ${float(m2.group(1).rstrip('.'))*60:.2f} audio-on" if m2 else ""
        return v * 60, f"${v}/s audio-off x 60s{extra}"
    m = re.search(r'\$([0-9.]+)\s*\(audio off\)', t, re.I)
    if m:
        return float(m.group(1).rstrip('.')) * 60, f"${m.group(1)}/s audio-off x 60s"

    # ---- 5. "For 5s video ... $X. For every additional second ... $Y" ----
    m = re.search(r'for\s*(\d+)\s*s(?:econd)?\s*video[^.]{0,60}?cost\s*\$([0-9.]+)', t, re.I)
    m2 = re.search(r'(?:aditional|additional)\s*second[^.$]{0,40}\$([0-9.]+)', t, re.I)
    if m and m2:
        base, n, add = float(m.group(2).rstrip('.')), float(m.group(1)), float(m2.group(1).rstrip('.'))
        return base + (60 - n) * add, f"${base} for {n:g}s + ${add}/extra s"
    if m:
        base, n = float(m.group(2).rstrip('.')), float(m.group(1))
        return base / n * 60, f"${base} per {n:g}s -> x60"

    # ---- 6. "$X per N second video generation" ----
    m = re.search(r'\$([0-9.]+)\s*per\s*(\d+)\s*second video', t, re.I)
    if m:
        return float(m.group(1).rstrip('.')) / float(m.group(2)) * 60, f"${m.group(1)} per {m.group(2)}s -> x60"

    # ---- 7. "Each 720p 5 second video ... costs roughly $X" ----
    m = re.search(r'each\s*(\d{3,4}p)?\s*(\d+)\s*second video[^.]{0,40}?\$([0-9.]+)', t, re.I)
    if m:
        res, n, v = (m.group(1) or '').lower(), float(m.group(2)), float(m.group(3).rstrip('.'))
        if res in ('', '720p'):
            return v / n * 60, f"${v} per {n:g}s {res or ''} -> x60"

    # ---- 8. "$X for a 5-second video" ----
    m = re.search(r'\$([0-9.]+)\s*for (?:a|one)?\s*(\d+)[- ]second video', t, re.I)
    if m:
        return float(m.group(1).rstrip('.')) / float(m.group(2)) * 60, f"${m.group(1)} per {m.group(2)}s -> x60"
    m = re.search(r'\$([0-9.]+)\s*for a (\d+)s video', t, re.I)
    if m:
        return float(m.group(1).rstrip('.')) / float(m.group(2)) * 60, f"${m.group(1)} per {m.group(2)}s -> x60"

    # ---- 9. plain per-second / per-output-second ----
    m = re.search(r'\$([0-9.]+)\s*per\s*(?:output|generated)?\s*(?:video\s*)?second', t, re.I)
    if not m:
        m = re.search(r'\$([0-9.]+)\s*/\s*sec', t, re.I)
    if not m:
        m = re.search(r'charged\s*\$([0-9.]+)\s*\.?\s*(?:for every second|per second)', t, re.I)
    if not m:
        m = re.search(r'(?:for every second|each second)[^.$]{0,60}\$([0-9.]+)', t, re.I)
    if m:
        v = float(m.group(1).rstrip('.'))
        return v * 60, f"${v}/s x 60s"

    # ---- 10. cents/s ----
    m = re.search(r'([0-9.]+)\s*cents?\s*/\s*s', t, re.I)
    if m:
        return float(m.group(1)) / 100 * 60, f"{m.group(1)} cents/s x 60s"

    # ---- 11. per-video flat with known duration ----
    m = re.search(r'\$?([0-9.]+)\s*\$?\s*(?:per|for every)\s*(?:generated\s*)?video', t, re.I)
    if m:
        v = float(m.group(1).rstrip('.'))
        dd = r.get('duration_default')
        n = None
        try: n = float(re.sub(r'[^0-9.]', '', str(dd))) if dd else None
        except Exception: n = None
        if n and n > 0:
            return v / n * 60, f"${v} per {n:g}s video -> x60"
        return None, f"${v} per video (duration varies)"

    # ---- 12. 720p flat per video ----
    m = re.search(r'\$?([0-9.]+)\s*\$?\s*(?:at|for)\s*720p', t, re.I)
    if m:
        v = float(m.group(1).rstrip('.'))
        dd = r.get('duration_default')
        try: n = float(re.sub(r'[^0-9.]', '', str(dd))) if dd else None
        except Exception: n = None
        if n and n > 0:
            return v / n * 60, f"${v} per {n:g}s 720p video -> x60"
        return None, f"${v} per 720p video"

    return None, ''


out = []
for r in rows:
    v, basis = compute(r)
    r['usd_per_min_720p'] = round(v, 2) if v else None
    r['price_basis'] = basis
    out.append(r)

json.dump(out, open('priced.json', 'w'), indent=1)
ok = sum(1 for r in out if r['usd_per_min_720p'])
print(f'priced: {ok}/{len(out)}')
miss = [r for r in out if not r['usd_per_min_720p'] and r['pricing_raw']]
print('has text, still unpriced:', len(miss))
for r in miss[:40]:
    print(' -', r['id'], '||', clean(r['pricing_raw'])[:120].replace('\n', ' '))
print('\nno pricing text at all:', sum(1 for r in out if not r['pricing_raw']))
