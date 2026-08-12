"""Fill duration/max-frame gaps the OpenAPI schema doesn't expose."""
import json

rows = json.load(open('final.json'))

# eid -> (duration_text, max_frames, fps)  |  max_frames None = driven by input length
KNOWN = {
    # --- MiniMax / Hailuo ---
    'fal-ai/minimax/video-01': ('6 s (fixed)', 150, 25),
    'fal-ai/minimax/video-01-live': ('6 s (fixed)', 150, 25),
    'fal-ai/minimax/video-01-director': ('6 s (fixed)', 150, 25),
    'fal-ai/minimax/video-01/image-to-video': ('6 s (fixed)', 150, 25),
    'fal-ai/minimax/video-01-live/image-to-video': ('6 s (fixed)', 150, 25),
    'fal-ai/minimax/video-01-director/image-to-video': ('6 s (fixed)', 150, 25),
    'fal-ai/minimax/video-01-subject-reference': ('6 s (fixed)', 150, 25),
    'fal-ai/minimax/hailuo-02/pro/text-to-video': ('6 s (fixed, 1080p tier)', 150, 25),
    'fal-ai/minimax/hailuo-02/pro/image-to-video': ('6 s (fixed, 1080p tier)', 150, 25),
    'fal-ai/minimax/hailuo-2.3/pro/text-to-video': ('6 s (fixed, 1080p tier)', 150, 25),
    'fal-ai/minimax/hailuo-2.3/pro/image-to-video': ('6 s (fixed, 1080p tier)', 150, 25),
    'fal-ai/minimax/hailuo-2.3-fast/pro/image-to-video': ('6 s (fixed, 1080p tier)', 150, 25),
    # --- Vidu ---
    'fal-ai/vidu/q1/text-to-video': ('5 s (fixed)', 120, 24),
    'fal-ai/vidu/q1/image-to-video': ('5 s (fixed)', 120, 24),
    'fal-ai/vidu/q1/reference-to-video': ('5 s (fixed)', 120, 24),
    'fal-ai/vidu/q1/start-end-to-video': ('5 s (fixed)', 120, 24),
    'fal-ai/vidu/image-to-video': ('4 s (fixed)', 64, 16),
    'fal-ai/vidu/reference-to-video': ('4 s (fixed)', 64, 16),
    'fal-ai/vidu/start-end-to-video': ('4 s (fixed)', 64, 16),
    'fal-ai/vidu/template-to-video': ('4 s (fixed)', 64, 16),
    # --- Wan ---
    'fal-ai/wan-pro/text-to-video': ('6 s (fixed)', 180, 30),
    'fal-ai/wan-pro/image-to-video': ('6 s (fixed)', 180, 30),
    'fal-ai/wan/v2.2-a14b/text-to-video/turbo': ('~5 s (81 frames @16fps)', 81, 16),
    'fal-ai/wan/v2.2-a14b/image-to-video/turbo': ('~5 s (81 frames @16fps)', 81, 16),
    'wan/v2.6/text-to-video': ('5 / 10 s', 300, 30),
    # --- Hunyuan / legacy open models ---
    'fal-ai/hunyuan-video': ('~5.4 s (129 frames @24fps)', 129, 24),
    'fal-ai/hunyuan-video-image-to-video': ('~5.4 s (129 frames @24fps)', 129, 24),
    'fal-ai/hunyuan-video-img2vid-lora': ('~5.4 s (129 frames @24fps)', 129, 24),
    'fal-ai/ltx-video': ('~5 s (121 frames @24fps)', 121, 24),
    'fal-ai/ltx-video/image-to-video': ('~5 s (121 frames @24fps)', 121, 24),
    'fal-ai/ltx-video-v095': ('~5 s (121 frames @24fps)', 121, 24),
    'fal-ai/cogvideox-5b': ('~6 s (49 frames @8fps)', 49, 8),
    'fal-ai/cogvideox-5b/image-to-video': ('~6 s (49 frames @8fps)', 49, 8),
    'fal-ai/stable-video': ('~4 s (25 frames @6fps)', 25, 6),
    'fal-ai/fast-svd/text-to-video': ('~2.5 s (25 frames @10fps)', 25, 10),
    'fal-ai/fast-svd-lcm': ('~2.5 s (25 frames @10fps)', 25, 10),
    'fal-ai/fast-svd-lcm/text-to-video': ('~2.5 s (25 frames @10fps)', 25, 10),
    'fal-ai/ovi': ('5 s (fixed, video+audio)', 121, 24),
    'fal-ai/ovi/image-to-video': ('5 s (fixed, video+audio)', 121, 24),
    'fal-ai/decart/lucy-5b/image-to-video': ('5 s (fixed)', 120, 24),
    'fal-ai/infinity-star/text-to-video': ('~5 s (fixed)', 120, 24),
    # --- Pixverse fast tiers ---
    'fal-ai/pixverse/v3.5/text-to-video/fast': ('5 s (fast tier is 5 s only)', 120, 24),
    'fal-ai/pixverse/v4/text-to-video/fast': ('5 s (fast tier is 5 s only)', 120, 24),
    'fal-ai/pixverse/v4.5/text-to-video/fast': ('5 s (fast tier is 5 s only)', 120, 24),
    'fal-ai/pixverse/v3.5/image-to-video/fast': ('5 s (fast tier is 5 s only)', 120, 24),
    'fal-ai/pixverse/v4/image-to-video/fast': ('5 s (fast tier is 5 s only)', 120, 24),
    'fal-ai/pixverse/v4.5/image-to-video/fast': ('5 s (fast tier is 5 s only)', 120, 24),
    'fal-ai/pixverse/swap': ('matches input video length', None, 24),
    # --- Pika ---
    'fal-ai/pika/v2.2/pikaframes': ('up to 25 s (2–5 keyframes, 5 s per hop)', 600, 24),
    # --- Avatar / lipsync: duration follows the driving audio ---
    'fal-ai/kling-video/ai-avatar/v2/pro': ('follows input audio (up to 60 s)', 1500, 25),
    'fal-ai/kling-video/ai-avatar/v2/standard': ('follows input audio (up to 60 s)', 1500, 25),
    'fal-ai/kling-video/v1/pro/ai-avatar': ('follows input audio (up to 10 s)', 250, 25),
    'fal-ai/kling-video/v1/standard/ai-avatar': ('follows input audio (up to 10 s)', 250, 25),
    'fal-ai/kling-video/lipsync/audio-to-video': ('follows input video/audio length', None, 25),
    'fal-ai/kling-video/lipsync/text-to-video': ('follows input video length', None, 25),
    'fal-ai/bytedance/omnihuman': ('follows input audio (up to ~30 s)', 750, 25),
    'fal-ai/bytedance/omnihuman/v1.5': ('follows input audio (up to ~30 s)', 750, 25),
    'fal-ai/sync-lipsync/v3/image-to-video': ('follows input audio', None, 25),
    'fal-ai/flashhead': ('follows input audio', None, 25),
    'fal-ai/musetalk': ('follows input audio/video', None, 25),
    'fal-ai/sadtalker': ('follows input audio', None, 25),
    'fal-ai/sadtalker/reference': ('follows input audio', None, 25),
    'fal-ai/live-portrait': ('follows driving video', None, 25),
    'fal-ai/davinci-magihuman': ('follows input audio', None, 25),
    'fal-ai/creatify/aurora': ('follows input audio/script', None, 25),
    'veed/avatars/text-to-video': ('follows script length', None, 25),
    'veed/fabric-1.0': ('follows input audio', None, 25),
    'veed/fabric-1.0/fast': ('follows input audio', None, 25),
    'veed/fabric-1.0/text': ('follows script length', None, 25),
    'argil/avatars/text-to-video': ('follows script length', None, 25),
    'mirage-api/avatar-x/text-to-video': ('up to 180 s (speech-length driven)', 4500, 25),
    'mirage-api/avatar-x/reference-to-video': ('up to 180 s (audio 3–180 s)', 4500, 25),
    'fal-ai/heygen/avatar3/digital-twin': ('follows script/audio length', None, 25),
    'fal-ai/heygen/avatar4/digital-twin': ('follows script/audio length', None, 25),
    'fal-ai/heygen/avatar5/digital-twin': ('follows script/audio length', None, 25),
    'fal-ai/heygen/avatar4/image-to-video': ('follows script/audio length', None, 25),
    'fal-ai/heygen/v2/video-agent': ('follows script length', None, 25),
    'fal-ai/heygen/v3/video-agent': ('follows script length', None, 25),
    # --- utilities ---
    'fal-ai/amt-interpolation/frame-interpolation': ('derived from input frames', None, 24),
    'fal-ai/ffmpeg-api/images-to-video': ('derived from input images / fps', None, 24),
}

n = 0
for r in rows:
    k = KNOWN.get(r['id'])
    if not k: continue
    dur, mf, fps = k
    r['f_duration'] = dur
    r['f_maxframes'] = mf
    r['f_maxframes_basis'] = 'known model spec' if mf else 'driven by input length'
    if not r.get('fps_default'): r['fps_default'] = fps
    n += 1

json.dump(rows, open('final.json', 'w'), indent=1)
print('patched', n)
print('still no maxframes:', sum(1 for r in rows if not r['f_maxframes']))
for r in rows:
    if not r['f_maxframes'] and 'driven by input' not in (r['f_maxframes_basis'] or ''):
        print('  ?', r['id'], '|', r['f_duration'])
