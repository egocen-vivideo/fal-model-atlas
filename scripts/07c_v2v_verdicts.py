"""Step 7c — verdicts for families added after the first pass.

Covers the video-to-video families of the Aug 18 pass (V2V), the unlisted
families of the Aug 28 pass (AUG_VERDICTS), and the Oct 14 refresh
(OCT_VERDICTS for new families, OCT_REVISIONS for existing families whose
facts moved — applied last, so they win over 07/07b). Any family still blank
after that inherits its previous verdict from ../data/models.json, and is
printed so it can be researched.

Oct 2026 sources: fal model pages / llms.txt (fetched 2026-10-14), Artificial
Analysis video arena (T2V v2.1 + I2V v1.1 boards, "September 2026 refresh",
fetched 2026-10-14), Creatify's Boreal launch post (vendor-run benchmark),
kandinskylab/kandinsky-6 README, Eyeline Labs ID-V2V project page, Google
Gemini API deprecations page, OpenAI API deprecations page.


Original Aug 18 note: families that already existed (Veo, Kling, LTX, Wan, Pixverse, Marey...) inherit
their verdicts from 07/07b — a v2v endpoint of an existing family is the same
model wearing a different hat. Only genuinely new families are defined here.

Same contract: sides = capabilities, use-cases = production scenarios, distinct.
Sources: fal model pages (Aug 2026) + external research (VACE ICCV 2025 paper
and Alibaba docs, Meta SAM 3 release, Topaz model docs, vendor pages).

Usage: python3 07c_v2v_verdicts.py [path/to/rows.json]
"""
import json
import os
import sys

V2V = {
 'Wan VACE': ("Alibaba's all-in-one video creation and editing framework: reference-to-video, masked v2v, pose/depth control and inpaint/outpaint/reframe in one model, with task composition across them (Move/Swap/Expand/Animate-Anything).",
              "Open-weights complexity — masks and control maps are your job to prepare; quality varies sharply by task combination.",
              "Object replacement and removal in existing footage, character animation from pose, frame expansion, ControlNet-style directed edits.",
              "One-shot text-to-video (use a generator), zero-setup workflows."),
 'Wan Motion': ("Streamlined character animation that transfers motion from a driving video onto a reference image while preserving the character's proportions.",
                "Single purpose; needs a clean driving video and a well-framed reference.",
                "Mascot and character animation from one still, dance/action retargeting.",
                "Scene generation, non-character motion."),
 'Topaz Video': ("Professional-grade upscale/restore suite — Proteus/Artemis/Iris for faithful live-action enhancement, Astra for AI-video artifact cleanup, Aion for clean 4K interpolation; plus deblur, denoise, colorize and SDR-to-HDR endpoints.",
                 "The priciest finishing tier here ($1.20–$18/min by model and resolution); Astra's generative texture is explicitly not for photoreal fidelity.",
                 "Delivery masters, archive remastering, rescuing low-res or noisy source, cleaning artifacts out of AI-generated footage.",
                 "Content creation, budget batch processing."),
 'Video upscalers': ("Cheaper temporal-consistent super-resolution (SeedVR2, FlashVSR, ByteDance, Clarity) at a fraction of Topaz's rate.",
                     "Less model choice and less control than Topaz; can soften fine texture.",
                     "Bulk upscaling of AI output, social-delivery resolution bumps.",
                     "Archival film restoration, HDR mastering."),
 'SAM Video': ("Meta's promptable segmentation: SAM 3 tracks every instance of a text-described concept across a clip ('the guy in the pineapple shirt'), with visual prompts too; RLE variants return compact masks.",
               "Accuracy drops on tiny, occluded or poorly lit objects — plan a cleanup pass; masks only, nothing generative.",
               "Auto-masking for VFX and inpainting pipelines, object tracking, dataset labelling, rotoscoping prep.",
               "Any generation or editing task on its own."),
 'Video background/erase': ("Dedicated matting and object erasure (Bria VRMBG 3.0, BEN v2, VEED, Pixelcut) tuned for clean temporal edges on talking heads and product footage.",
                            "Struggles with hair detail and motion blur; erase quality drops on complex occlusion.",
                            "Green-screen replacement without a green screen, podcast and product compositing, removing objects from delivered footage.",
                            "Creative generation, scene-level edits."),
 'Void Inpainting': ("Removes objects along with the interactions they induce — shadows, reflections and contact effects, not just the pixels.",
                     "Single-purpose and slower than plain inpainting.",
                     "Clean plates where a naive erase leaves telltale shadows, VFX prep.",
                     "Adding content, style changes."),
 'Frame interpolation': ("Classic optical-flow interpolation (RIFE, FILM, AMT) — nearly free and deterministic.",
                         "Artifacts on fast motion and occlusion; no detail recovery.",
                         "Smoothing low-fps AI output, cheap slow-motion.",
                         "Quality-critical delivery (Topaz Aion is the paid answer)."),
 'Video preprocessors': ("Depth, pose and structure extraction across frames with temporal consistency (Video Depth Anything, DWPose).",
                         "Control maps only — output feeds another model.",
                         "Driving VACE/ControlNet pipelines, 3D and AR prep.",
                         "Standalone use."),
 'Video utilities': ("Deterministic ffmpeg-grade operations — merge, trim, reverse, scale, blend, compose, auto-subtitle.",
                     "Not generative; no creative control.",
                     "Pipeline glue around generation steps, deliverable assembly.",
                     "Content creation."),
 'LightX': ("Relight and re-camera existing footage — change lighting direction or virtual camera move after the fact.",
            "Expensive at $6/min; heavy edits can flatten materials.",
            "Fixing lighting continuity across shots, adding camera movement to locked-off footage.",
            "Full scene generation, budget work."),
 'Editto': ("Instruction-based video editing — describe the change in plain language.",
            "New and thinly documented; $4.80/min with unclear failure modes.",
            "Quick one-shot edits without mask preparation.",
            "Precise or repeatable edits (VACE gives real control)."),
 'DreamActor': ("ByteDance motion transfer that handles non-human and multi-character subjects well — a genuine gap in most animation models.",
                "$3/min; needs a clean driving performance.",
                "Animating creatures, mascots and group scenes from stills.",
                "Single-human talking heads (cheaper avatar models win), scene generation."),
 'One-to-All Animation': ("Pose-driven, alignment-free motion transfer from a single reference image across diverse styles.",
                          "1.3B tier is rough; 14B costs $3.60/min.",
                          "Stylized character animation where the reference and driver don't share a body shape.",
                          "Photoreal human performance, backgrounds."),
 'Mirelo SFX': ("Video-aware SFX that returns the clip with a synced soundtrack; three model generations on fal.",
                "SFX only — no music or dialogue.",
                "Auto-foley for generated video, ambience beds for b-roll.",
                "Scored music, speech."),
 'Sonilo': ("Generates synced music for a clip and returns a commercially licensed soundtrack, optionally preserving original speech.",
            "Music-only; less control than a composer or a prompt-driven music model.",
            "Rights-clean background scores for delivered video, social edits needing safe audio.",
            "Sound design, dialogue."),
 'ThinkSound': ("Chain-of-thought video-to-audio — reasons about on-screen events before generating.",
                "Compute-billed with no fixed rate; young model.",
                "Realistic event-matched audio for generated footage.",
                "Music composition, speech."),
 'MMAudio': ("The cheap open standard for video-synced audio ($0.06/min) — pairs with any silent video model.",
             "Fidelity below dedicated foley models; short clips.",
             "Adding cheap ambience to silent generations at volume.",
             "Broadcast-grade sound design."),
 'Hunyuan Foley': ("Tencent's foley model for event-matched sound effects.",
                   "SFX only; limited control surface.",
                   "Adding impact and ambience to AI video.",
                   "Music, dialogue."),
 'ControlFoley': ("Text-shaped foley — the prompt steers the type of sound while timing follows the action on screen.",
                  "No published schema on fal; sparse docs.",
                  "Directed sound design where you want a specific character of sound.",
                  "Music scoring."),
 'CassetteAI SFX': ("Cheap video-to-SFX at $0.20/min.",
                    "Loop-grade quality.",
                    "Bulk sound passes on social content.",
                    "Film-grade foley."),
 'Pixelcut Video': ("Consumer-grade video background removal.",
                    "Single task; quality below Bria/BEN.",
                    "Quick e-commerce clips.",
                    "Broadcast compositing."),
 'BEN video': ("High-quality temporally smooth background removal.",
               "Matting only; $1.33/min.",
               "Talking-head compositing where edge stability matters.",
               "Anything generative."),
 'Alibaba Happy Oyster': ("Realtime interactive world model — generate a world from a prompt, then explore or direct it as live video; streams at $0.014/s after a $2 world-creation fee.",
                          "Interactive-first: not a clip renderer, and quality is traded for realtime latency.",
                          "Playable world demos, interactive installations, game-style previz.",
                          "Deliverable video files, precise shot control."),
}


# Aug 28 2026 pass (formerly NEW_VERDICTS in 09_unlisted.py — moved here when 09
# became a discovery-only step). family -> (strong side, weak side, strong uses, weak uses)
AUG_VERDICTS = {
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


OCT_VERDICTS = {
 'Veo 3': (
   "Google's first native-audio Veo (dialogue, SFX, ambience in one pass), still callable on fal in standard, fast and image-to-video variants.",
   "fal marks every Veo 3 endpoint deprecated and hides it from its index; superseded by Veo 3.1, which is itself being retired on 17 Nov 2026.",
   "Only reproducing an existing Veo 3 pipeline's look while migrating.",
   "Any new work — start on Gemini Omni Flash 1.1 or another current model."),
 'MiniMax H3-Max Turbo': (
   "The cheapest H3-class generator: $0.04/s at 768p regular ($0.024 promo to Oct 15) — half of H3-Max — with the same 0.9–15 s range, six aspect ratios incl. 21:9, start + end frame on i2v, optional target audio track, and an extend endpoint for 1.6–60 s sources.",
   "Native 768p (1080p is a refinement pass); not yet on the Artificial Analysis boards, so its quality gap to H3-Max is unmeasured.",
   "High-volume social and ad variants, storyboard animatics, keyframed i2v drafts before an H3-Max or H3 hero render.",
   "Hero shots and 2K/4K masters (base H3 has 2K/4K tiers); anything where the last increment of aesthetics matters."),
 'Vidu Q4': (
   "Character performance with native dialogue and SFX: 3–16 s i2v from 540p to 4K, camera cuts, and a reference mode taking up to 12 images plus 3 voice clips tagged in the prompt. $0.095/s at 720p regular ($0.0665 promo until Nov 30).",
   "Only i2v and reference endpoints on fal (no text-to-video); new (Q4 Preview launched Oct 7, 2026) and not on the current AA v1.1 boards — a #3 debut on the older I2V v1.0 board is reported second-hand only.",
   "Multi-character dialogue scenes from reference sheets, recurring mascots with a consistent voice, 2K/4K deliveries of animated stills.",
   "Pure text-to-video briefs, workflows that need independent benchmark evidence before committing."),
 'Kandinsky 6': (
   "Open weights (MIT, Lite 3B / Pro 29B) with synchronized 44 kHz audio and lip-sync in one pass; Lite at $0.16 per 5 s clip is among the cheapest audio-video on fal; bilingual English/Russian prompting; a matching VSR upscaler.",
   "Fixed 5 s at native 480p (1080p only via the paid upscale factor); Pro is slow and costs $1.35 per 5 s clip at 50 steps.",
   "Cheap drafts with sound, Russian-language content, self-hostable pipelines that want the same model on fal and on-prem.",
   "Anything longer than 5 s, native-HD deliverables, latency-sensitive work on Pro."),
 'Creatify Boreal': (
   "Ad/UGC model post-trained from LTX-2.5: 1–20 s with native audio at 720p/1080p/2K, prompt sections for visual/speech/sounds/on-screen text, and $0.01/s at 720p with roughly realtime rendering — the cheapest audio-video generation in the atlas.",
   "Ranks last (29/29) on the AA text-to-video board; English-only; fal warns identity, logos, small text and hands can vary; vendor benchmark shows its smallest gain on single-person talking clips.",
   "Bulk product and UGC ad variants, A/B creative testing at volume, presenter-style drafts where speed and cost dominate.",
   "Hero brand films, logo- or text-exact shots, non-English dialogue."),
 'Pixelcut Looping Video': (
   "Turns one product photo into a seamless 5–15 s loop that starts and ends on that photo, locked camera, with subtle ambient motion or a full 360° spin.",
   "Single-purpose, and $0.16/s at 768p is expensive for what it does; no maker documentation or benchmarks found.",
   "E-commerce product cards, marketplace listings and web hero loops from packshots.",
   "Any narrative or camera-moving shot."),
 'ID-V2V': (
   "Identity-preserving restyle of real footage (Eyeline Labs / Netflix research on Wan 2.1 + VACE, Apache-2.0): the source keeps identity, expression, gaze and motion while the rest of the frame follows a restyled first frame; a relight mode propagates a relit first frame.",
   "Needs a prepared first frame (and optional keyframes); 480p/720p only; $0.20/s.",
   "Look development and relighting on live-action plates, wardrobe/set restyles that must not change the actor.",
   "Generation from scratch, 1080p+ finishing."),
 'FLUX.3 Action': (
   "Not a video generator: a vision-language-action policy for the SO-101 robot arm — two camera images, joint state and an instruction in, a 30 Hz action chunk out — at ~$0.003 per compute second.",
   "Outputs are unclipped (joint, velocity and workspace limits are the caller's job); useless for media work.",
   "Robotics research and SO-101 teleop/automation prototypes.",
   "Any video production task — listed here only because fal files it under video-to-video."),
 'EchoMimic': (
   "Talking avatar from one image + audio + prompt, billed by audio length at $0.20/s.",
   "An older open model newly listed on fal, priced above newer avatar options; no independent evaluation found.",
   "Quick talking-portrait tests where an open-model pipeline is preferred.",
   "Volume avatar work (VEED Fabric, Kling Avatar are cheaper) and client-ready presenters."),
 'ElevenLabs Dubbing': (
   "Dubs an existing video or audio track into another language at $0.60 per minute — the full localisation step in one call.",
   "Audio-only change: lips are not re-synced (pair with a lipsync endpoint for that).",
   "Localising explainers, ads and talking-head content into many languages.",
   "Lip-accurate close-ups without a follow-up lipsync pass."),
 'Wan 2.2 S2V': (
   "Open speech-to-video: image + audio to a film-style talking or singing shot with body motion, not just lips; $0.20/s at 720p.",
   "16 fps output, 2025-era quality, and more expensive per second than Wan 3.0 generation.",
   "Open-weights talking scenes and music performances from a still.",
   "Smooth-motion deliverables without interpolation; cost-sensitive volume avatar work."),
 'Mureka Lyrics Video': (
   "Flat $0.15 per video: a lyric video built from a song, with layout and background presets.",
   "Template output — typography and motion, not generated scenes.",
   "Lyric videos for releases and social snippets from Mureka-generated or uploaded songs.",
   "Narrative music videos (see PixVerse Music Video)."),
 'PixVerse Music Video': (
   "Whole music videos from a 10 s–6 min track: 15 style presets, character and style references, lyric subtitles, a lip-sync switch and five aspect ratios, at $0.06/s at 720p.",
   "PixVerse's stylised look; 10 s minimum billing; long songs mean long, costly renders to iterate.",
   "Full-length visualisers and AI music videos for independent artists, social cut-downs of a track.",
   "Photoreal performance footage, frame-exact edit control."),
 'SAM Audio': (
   "Meta's SAM Audio for video: isolates the sound of a visual subject (optionally masked or prompted) and returns target + residual tracks, $0.05 per 30 s.",
   "Separation, not generation — quality depends on how distinct the source is in the mix.",
   "Pulling one speaker or instrument out of footage, cleaning dialogue under ambience, prepping stems for re-mix.",
   "Creating new sound or music."),
}

# existing families whose facts moved between Aug 28 and Oct 14 2026
# family -> (strong side, weak side); '' keeps the current text
OCT_REVISIONS = {
 'Seedance 2.5': (
   "Native 30-second single-shot generation (4–30 s) with whole-shot reasoning, up to 50 multimodal references, a 480p draft → 1080p complete workflow, and #3 text-to-video / #2 image-to-video on the AA arena (Sept 2026 refresh). US-hosted variants exist for US companies.",
   "The priciest mainstream rate per second: $0.473/s at 720p and $1.164/s at 1080p; US-hosted variants cost ~1.2x and are restricted to US companies."),
 'Seedance 2.0': (
   '', "720p costs ~$0.30/s and 1080p more than doubles it ($0.68/s); now behind Seedance 2.5 on both AA boards (#7 T2V, #6 I2V). Prompt-following degrades on very long multi-shot scripts."),
 'MiniMax H3-Max': (
   "Post-trained H3 (fal's own stack) tuned for prompt adherence and aesthetics — #5 on both AA video boards — wrapped in the broadest suite on fal: t2v/i2v with end frame, reference, extend, insert-video, recast (swap up to 4 people), relight, camera-controls, 3D-to-video previs, lip-sync, five style presets and a realtime WebRTC director.",
   "Native 768p (1080p is a refinement pass) and $0.08/s regular at 768p — now dearer than base H3 ($0.06/s); recast costs $0.30/s; 3D-to-video does not guarantee geometry or camera paths."),
 'MiniMax H3': (
   "Frontier MiniMax model — #1 image-to-video and #4 text-to-video on the AA arena (Sept 2026 refresh) at 768p — with 2K and 4K output, 5–15s, seven aspect ratios, LoRA and reference modes.",
   "No 720p tier (768p at $0.06/s is the cheap one); 2K/4K tiers cost $0.13–$0.16/s; ecosystem still young."),
 'Wan 3.0': (
   "Alibaba's third generation and #1 on the AA text-to-video arena (with and without audio, Sept 2026 refresh): t2v, i2v with optional last frame, and a reference mode taking images, video, audio, a document or a web page — at $0.10/s at 720p.",
   ''),
 'Veo 3.1': (
   '', "Being retired: every fal Veo 3.1 endpoint is unlisted and fal will deprecate it on 17 Nov 2026 (Google names Gemini Omni Flash 1.1 as the replacement); it now sits #20 T2V / #14 I2V on the AA arena. Only 16:9 and 9:16, 8 s ceiling, heavy content filtering."),
 'Grok Imagine 1.5': (
   '', "720p ceiling on i2v output; 15 s cap; X-ecosystem moderation is idiosyncratic and violations still bill. The 1.5 Lite tier ($0.03/s at 720p) trades quality for price — #18 vs #11 for full 1.5 on the AA T2V board."),
 'Luma Ray 2': (
   '', "Being retired: fal deprecates every Ray 2 / Ray 2 Flash endpoint on 25 Oct 2026 (migrate to Ray 3.2). No audio, fixed 5s, and detail resolution trails newer models."),
}


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else (
        'final.json' if os.path.exists('final.json')
        else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'models.json'))
    rows = json.load(open(src))
    n = 0
    table = {**AUG_VERDICTS, **V2V, **OCT_VERDICTS}
    for r in rows:
        v = table.get(r['family_key'])
        if v:
            r['f_strong'], r['f_weak'], r['f_use_strong'], r['f_use_weak'] = v
            n += 1
        rv = OCT_REVISIONS.get(r['family_key'])
        if rv:
            if rv[0]: r['f_strong'] = rv[0]
            if rv[1]: r['f_weak'] = rv[1]
    # last resort: a family that lost its verdict inherits the previous one
    prev_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'models.json')
    prev = {}
    if os.path.exists(prev_path) and os.path.abspath(prev_path) != os.path.abspath(src):
        for p in json.load(open(prev_path)):
            if p.get('f_strong'):
                prev.setdefault(p['family_key'], (p['f_strong'], p['f_weak'],
                                                  p.get('f_use_strong', ''), p.get('f_use_weak', '')))
    inherited, blank = set(), set()
    for r in rows:
        if not r.get('f_strong'):
            if r['family_key'] in prev:
                r['f_strong'], r['f_weak'], r['f_use_strong'], r['f_use_weak'] = prev[r['family_key']]
                inherited.add(r['family_key'])
            else:
                blank.add(r['family_key'])
        elif not r.get('f_use_strong') and r['family_key'] in prev:
            r['f_use_strong'], r['f_use_weak'] = prev[r['family_key']][2:]
            inherited.add(r['family_key'])
    json.dump(rows, open(src, 'w'), indent=1)
    print(f'verdicts applied to {n} rows across {len(table)} families; '
          f'{len(OCT_REVISIONS)} Oct revisions')
    print('inherited from previous data:', sorted(inherited) or 'none')
    print('STILL BLANK:', sorted(blank) or 'none')


if __name__ == '__main__':
    main()
