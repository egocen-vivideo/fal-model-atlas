"""Step 6b — assign each endpoint its family (family_key) and Task (f_task).

07/07b/07c key their verdicts on family_key and 08 splits the two video tabs
on f_task, but no committed step set either field before Oct 2026 — the Aug
passes assigned them in a scratch session. This step makes that reproducible:

1. Endpoints the atlas already carried keep their family and task from
   ../data/models.json (curated in earlier passes; stable across refreshes).
2. New endpoints are matched against FAMILY_RULES / TASK_RULES below, first
   match wins. Generation endpoints (t2v / i2v / reference / audio-to-video)
   get task 'generate'; video-to-video endpoints get a repurposing task.
3. Anything still unmatched falls back to "<lab> misc" and is printed, so the
   rules can be extended before the verdict steps run.

Usage: python3 06b_families.py   (patches ./final.json)
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# first match wins — specific before general
FAMILY_RULES = [
    (r'^fal-ai/veo3\.1', 'Veo 3.1'), (r'^fal-ai/veo3', 'Veo 3'),
    (r'seedance-2\.5', 'Seedance 2.5'), (r'seedance-2\.0', 'Seedance 2.0'),
    (r'seedance/v1\.5|seedance-1\.5', 'Seedance 1.5'), (r'seedance', 'Seedance 1.0'),
    (r'minimax/h3-max-turbo', 'MiniMax H3-Max Turbo'), (r'minimax/h3-max', 'MiniMax H3-Max'),
    (r'minimax/h3', 'MiniMax H3'),
    (r'kling-video/v3', 'Kling 3'), (r'kling-video/o3', 'Kling O3'), (r'kling-video/o1', 'Kling O1'),
    (r'vidu/q4', 'Vidu Q4'), (r'vidu/q3', 'Vidu Q3'), (r'vidu/q2', 'Vidu Q2'), (r'vidu/q1', 'Vidu Q1'),
    (r'kandinsky6', 'Kandinsky 6'),
    (r'gemini-omni-flash', 'Gemini Omni Flash'),
    (r'wan-3\.0-prime', 'Wan 3.0 Prime'), (r'wan-3\.0', 'Wan 3.0'),
    (r'wan/v2\.2-14b/speech-to-video', 'Wan 2.2 S2V'),
    (r'happy-horse', 'Alibaba Happy Horse'), (r'happy-oyster', 'Alibaba Happy Oyster'),
    (r'luma/agent/ray', 'Luma Ray 3.2'), (r'ray-2', 'Luma Ray 2'),
    (r'pixverse/music-video', 'PixVerse Music Video'),
    (r'pixverse/v6', 'Pixverse V6'), (r'pixverse/c1', 'Pixverse C1'),
    (r'grok-imagine-video/v1\.5', 'Grok Imagine 1.5'), (r'grok-imagine-video', 'Grok Imagine'),
    (r'ltx-2\.5', 'LTX-2.5'), (r'ltx-2\.3', 'LTX-2.3'), (r'ltx-2-19b', 'LTX-2 19B'),
    (r'flux-3-action', 'FLUX.3 Action'), (r'flux-3', 'FLUX.3 Video'),
    (r'creatify/boreal', 'Creatify Boreal'), (r'creatify', 'Creatify Aurora'),
    (r'pixelcut/looping', 'Pixelcut Looping Video'),
    (r'fal-ai/id-v2v', 'ID-V2V'),
    (r'echomimic', 'EchoMimic'),
    (r'elevenlabs/dubbing', 'ElevenLabs Dubbing'),
    (r'mureka', 'Mureka Lyrics Video'),
    (r'sam-audio', 'SAM Audio'),
    (r'sonilo', 'Sonilo'), (r'mirelo', 'Mirelo SFX'),
    (r'scene-finder|sa2va|video-understanding|nemotron|openrouter', 'Video understanding'),
    (r'heygen', 'HeyGen'), (r'veed', 'VEED'), (r'argil', 'Argil'),
    (r'topaz', 'Topaz Video'), (r'decart', 'Decart Lucy'),
]

# video-to-video only; first match wins
TASK_RULES = [
    (r'video-to-audio|video-to-music|sound-effects|sfx|foley|visual-separate|dubbing', 'video→audio'),
    (r'scene-finder|sa2va|understanding|nemotron|openrouter|/sam|depth|pose', 'analysis/masking'),
    (r'lip-?sync', 'lipsync'),
    (r'extend|draft/complete|continue', 'extend'),
    (r'upscale|vsr|enhance|restore|super-res', 'upscale/restore'),
    (r'background|erase|inpaint|insert-video|remove', 'inpaint/erase'),
    (r'interpolat|rife|/film', 'interpolation'),
    (r'reframe|trim|merge|ffmpeg|subtitle|caption|lottie', 'utility'),
    (r'.', 'edit/restyle'),       # edit, recast, relight, restyle, reference v2v, 3d-to-video...
]

# endpoints whose fal category misleads: id -> (category, task)
OVERRIDES = {
    'fal-ai/elevenlabs/dubbing': ('video-to-video', 'video→audio'),   # filed as audio-to-video; it re-voices footage
    'fal-ai/flux-3-action/so101': ('video-to-video', 'utility'),       # robot action policy, not video
}


def main():
    rows = json.load(open('final.json'))
    prev_path = os.path.join(ROOT, 'data', 'models.json')
    prev = {r['id']: r for r in json.load(open(prev_path))} if os.path.exists(prev_path) else {}
    carried = ruled = fallback = 0
    for r in rows:
        p = prev.get(r['id'])
        if p and p.get('family_key'):
            r['family'] = r['family_key'] = p['family_key']
            r['f_task'] = p.get('f_task', 'generate')
            carried += 1
            continue
        fam = next((n for pat, n in FAMILY_RULES if re.search(pat, r['id'])), None)
        if fam is None:
            fam = f"{r.get('lab') or r['id'].split('/')[0]} misc"
            fallback += 1
            print('  unmatched family:', r['id'])
        else:
            ruled += 1
        r['family'] = r['family_key'] = fam
        if r['id'] in OVERRIDES:
            r['category'], r['f_task'] = OVERRIDES[r['id']]
        elif r['category'] == 'video-to-video':
            r['f_task'] = next(t for pat, t in TASK_RULES if re.search(pat, r['id']))
        else:
            r['f_task'] = 'generate'
    json.dump(rows, open('final.json', 'w'), indent=1)
    print(f'families: carried {carried}, by rule {ruled}, fallback {fallback}')


if __name__ == '__main__':
    main()
