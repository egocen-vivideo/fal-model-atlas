"""Step 7b — strongest / weakest USE-CASES per family, plus side revisions.

Distinct from 07_verdicts.py on purpose: sides describe capabilities (what the
model can and cannot do), use-cases name production scenarios (what you should
and should not reach for it for). Sources: each family's fal model page
(scraped Aug 2026) plus external reviews — Artificial Analysis arena rankings,
Curious Refuge, vendor technical reports, and practitioner write-ups.

Usage: python3 07b_usecases.py [path/to/final.json]
Defaults to ./final.json, else ../data/models.json.
"""
import json
import os
import sys

# family -> (strongest use-cases, weakest use-cases)
USE = {
 'Veo 3.1': ("Dialogue-led ads and UGC-style spots, cinematic hero shots with sound, music-video beats, storyboard-to-pitch reels — anywhere one gorgeous take with audio closes the brief.",
             "Exact logos or on-screen type, characters that must survive many shots, 21:9/1:1 deliverables, high-volume iteration on a tight budget."),
 'Kling 3': ("Short films and AI dramas with real cut structure, product reveals with per-shot direction, trailers and music videos — multi-shot prompting does coverage a single-take model can't.",
             "Bulk social iteration (2.5T is faster and cheaper), dialogue scenes running past ~3 shots where face drift accumulates, pixel-exact brand frames."),
 'Kling O3': ("Restyle and anime-cel treatments of existing footage, reference-heavy composites (elements + start/end frames), stylized trailers and poster-frame concepts at 4K.",
              "Skin/fabric close-ups where fine texture decides the shot (v3 renders it better), from-scratch photoreal hero shots."),
 'Kling O1': ("Before/after transformations, timelapse morphs, scene-to-scene transitions inside an edit, product state changes (closed → open).",
              "Open-ended generation — anything without a defined end frame."),
 'Kling 2.6': ("Budget social ads with ambient audio or voiceover, fashion and product b-roll with sound.",
               "Multi-shot narratives, precisely timed dialogue, 4K deliverables."),
 'Kling 2.5T': ("High-volume social content and rapid creative iteration — the bulk-work default; silent b-roll and motion studies at the best quality-per-dollar.",
                "Anything sound-led, edgy or sensitive briefs (moderation rejects a lot), beats longer than 10 s."),
 'Kling 2.1': ("Cinematic single shots where the Master look still earns its fee; drafts on std/pro tiers.",
               "New pipelines — 2.5T/3 beat it on both price and quality for every scenario."),
 'Kling 2.0': ("Period/cinematic mood pieces on a legacy pipeline you already trust.",
               "Anything new — superseded across the board."),
 'Kling 1.6': ("Cheap drafts, effects presets, elements-based multi-subject experiments.",
               "Client deliverables at 2026 quality bars."),
 'Kling 1.5': ("Effects-preset socials, quick drafts.", "Everything client-facing."),
 'Kling 1.0': ("API smoke tests, historical comparisons.", "All production work."),
 'Kling Avatar': ("Talking-head UGC ads from one photo, podcast-clip visualization, mascot characters (animals/cartoons) that speak, multilingual dubs of a still character.",
                  "Full-body performance, scenes needing camera moves or environment change beyond the speaker."),
 'Kling Lipsync': ("Re-dubbing existing clips, localizing spokesperson videos, repairing dialogue takes.",
                   "Net-new content — it edits, it doesn't generate."),
 'Seedance 2.5': ("Full 30-second ad spots in one take, long product beats, single-shot brand films where identity must hold start to finish, composites drawing on many references.",
                  "1080p/4K masters (fal caps at 720p), budget bulk pipelines at ~$0.47/s, fast-turnaround iteration — long renders."),
 'Seedance 2.0': ("Multi-scene ad narratives with sound, choreography and camera-move transfer from reference clips, edit-and-extend workflows, sports/action physics.",
                  "Cost-sensitive volume work, simple loops that waste its power, very long scripts where adherence degrades."),
 'Seedance 1.5': ("Broadcast-style clips with dialogue and SFX on a mid budget, start/end-frame anchored spots.",
                  "Multi-shot storytelling, 4K masters."),
 'Seedance 1.0': ("Clean 1080p product b-roll at low cost (fast tier), silent loops.",
                  "Sound-led content, character dialogue."),
 'LTX-2.5': ("Dialogue shorts and music-driven content where AV sync sets the pacing; final renders in pro mode; open-weights pipelines that need audio.",
             "Non-speech ambient soundscapes (audio quality drops without dialogue), very long continuous clips."),
 'LTX-2.3': ("Narrated clips up to 20 s with native audio on per-megapixel pricing, vertical 4K social, LoRA-styled brand looks.",
             "Cheap sub-1080p drafting (no lower tier exists), teams without patience for the endpoint sprawl."),
 'LTX-2 19B': ("High-volume audio+video content farms, LoRA-fine-tuned character/brand pipelines, long frame-count clips at the best open-model cost.",
               "Single cinematic hero shots against Kling/Veo, high-res fast turnarounds (megapixel billing punishes both)."),
 'LTX-Video (legacy)': ("Instant previews and animatic drafts; prompt testing before spending on a frontier model.",
                        "Anything a client will see."),
 'Wan 2.7': ("Cinematic mid-tier spots: smooth dolly/crane/orbit moves, subject+voice reference ads, first/last-frame directed shots, complex briefs via thinking-mode planning.",
             "60-second continuous stories, LoRA-ecosystem work (2.2 still owns the tooling)."),
 'Wan 2.5/2.6': ("Audio-enabled drafts and mid-tier social; the flash tier for cheap fast image animation.",
                 "Long-lived production pipelines — the preview API keeps shifting."),
 'Wan 2.2 A14B': ("Anime and stylized character animation with community LoRAs, ComfyUI-controlled open pipelines, style-locked brand content, research.",
                  "Sound-led work, smooth high-fps deliverables without an interpolation pass, long takes."),
 'Wan 2.2 5B': ("Bulk prompt exploration, preview farms, hobby and edge deployments.",
                "Face close-ups, complex motion, anything client-facing."),
 'Wan Pro': ("One-off 1080p30 hero clips from stills.",
             "Audio content, length beyond 6 s, cost-sensitive volume."),
 'Wan 2.1': ("Legacy LoRA pipelines, effects templates, cheap drafts.",
             "Modern quality bars."),
 'Krea-Wan': ("Aesthetic-led fashion/design loops where the 'AI look' must be minimized, cheap stylish social.",
              "Precise product briefs, anything needing image input or audio."),
 'Hailuo 2.3': ("Character performance: dance, sports, fashion film, emotional close-ups — the budget pick for human motion.",
                "Physics-heavy object interaction (Veo/Seedance lead), wide aspect-ratio variety, sound-led content."),
 'Hailuo 02': ("Human-motion stress tests, cheap character b-roll.",
               "Aspect-controlled deliverables, audio content."),
 'MiniMax H3': ("Brand ads needing accurate on-screen text and logos, V2V motion transfer from reference footage, coordinated character+camera+dialogue scenes, 2K masters with stereo sound.",
                "Long-form (15 s cap), license-sensitive enterprise use without legal review, budget work where 768p-simple models suffice."),
 'MiniMax video-01': ("Director-mode camera-command experiments, anime/illustration motion on the live variant.",
                      "Anything held to current fidelity bars."),
 'Pixverse V6': ("Trend-speed TikTok/Reels content, template effects, transitions.",
                 "Understated photoreal brand film."),
 'Pixverse V5.6': ("Higher-fidelity viral effects and social spots with audio.",
                   "Budget bulk runs (V5.5 is half the price), cinematic realism."),
 'Pixverse V5.5': ("Viral template effects (AI Hug, morphs), meme-speed social volume, multi-clip social sequences.",
                   "Client film work, subtle motion."),
 'Pixverse V5': ("Cheap template-driven social content, image transitions.",
                 "Photoreal or premium-brand output."),
 'Pixverse V4.5': ("Effects-library socials on a budget.", "Anything current-gen."),
 'Pixverse V4': ("Cheap drafts, legacy effects.", "Production."),
 'Pixverse V3.5': ("Lowest-cost loops.", "Everything else."),
 'Pixverse C1': ("Film-grade 15 s spots with native audio at 1080p — the Pixverse pick for client work; @ref-named reference composites.",
                 "Budget bulk pipelines, understated realism."),
 'Pixverse misc': ("Product-placement swaps, background replacement, persona-localized ad variants of one master clip.",
                   "Net-new generation of any kind."),
 'Vidu Q3': ("Anime and illustrated character content at volume, 16-second continuous character takes, multi-reference ensemble scenes (mix mode).",
             "High-energy action where references drift, photoreal Western-style ads, audio-led briefs."),
 'Vidu Q2': ("Subject-consistent character spots on a budget, e-commerce product/model consistency.",
             "Long clips, cinematic camera language."),
 'Vidu Q1': ("2D anime shorts, VTuber OP/ED sequences, social animations, start-end transitions.",
             "Photoreal work, anything past 5 s."),
 'Vidu 1.x': ("Cheapest reference and start-end experiments, template trend clips.",
              "2026 quality bars."),
 'Grok Imagine 1.5': ("Animating stills while preserving composition and identity (arena-topping i2v), wardrobe/object edit variants, clip-continuation chains, meme-speed social with audio.",
                      "Choreographed camera paths, 1080p+ masters from i2v (720p ceiling), brand-safety-critical pipelines."),
 'Grok Imagine': ("Cheap audio-included drafts inside the X ecosystem.",
                  "Fine-controlled or high-fidelity work — 1.5 supersedes it."),
 'Luma Ray 3.2': ("Seamless product loops, HDR-graded cinematic shots for directors who think in shot lists, style/subject-locked reference work.",
                  "Budget iteration, dialogue-led content (no audio)."),
 'Luma Ray 2': ("Natural-motion b-roll, physics-plausible product demos, film previz.",
                "Detail-critical close-ups, sound, fast turnaround."),
 'Pika 2.2': ("Multi-beat keyframe sequences (2–5 stills into ~25 s), image-morph storytelling, 1080p social spots.",
              "Character identity across keyframes, audio content, photoreal fidelity against frontier models."),
 'Pika 2.1': ("Character-controlled cinematic one-offs.", "Value-conscious pipelines — 2.2 is better and same-priced."),
 'Pika 2 Turbo': ("Fast drafts.", "Final renders."),
 'FLUX.3 Video': ("Facial-expression-led performance shots, multilingual speech scenes, keyframe-controlled transitions, agent-chained sequences; draft-tier iteration graduating to quality-tier masters.",
                  "Battle-tested production (model is weeks old; the eval wins are vendor-run), community-tooling-dependent workflows."),
 'Gemini Omni Flash': ("Conversational iterate-and-edit workflows ('now make it dusk'), physics-plausible explainer and product clips, Workspace/Vids-adjacent content.",
                       "Anything over 10 s, formats beyond 16:9/9:16, strict-brand content that trips Google's filters."),
 'Alibaba Happy Horse': ("General-purpose spots at arena-topping quality, multilingual lip-synced dialogue (7 languages) for global ad variants, multi-reference composites on v1.1.",
                         "Shot-by-shot directed narratives (no multi-shot control), 4K masters, teams needing mature tooling."),
 'Bernini-R': ("Video restyle and style transfer, watermark/subtitle removal, local region edits, reference-guided edit variants — open-weights editing at commercial-tier quality.",
               "From-scratch human-centric generation (the renderer-only variant lags there), audio work."),
 'Hunyuan 1.5': ("Self-hosted consumer-GPU pipelines (Apache-2.0, ~14 GB VRAM), unrestricted research, budget drafts with strong prompt adherence.",
                 "Direct 720p+ delivery from the fal endpoint (480p only — upscale is your job), sound-led content."),
 'Hunyuan (legacy)': ("Open-weights research baselines.", "Current production."),
 'Kandinsky 5 Pro': ("1024p spots with flat predictable pricing, Russian-language briefs.",
                     "720p-optimized budgets, English-idiom-heavy prompts."),
 'Kandinsky 5': ("Flat-rate bulk drafting where cost certainty matters, distill tier for near-realtime iteration.",
                 "Fidelity-led work."),
 'LongCat': ("Minutes-long continuous takes via native continuation — walkthroughs, ambient scenes, lo-fi loops; the cheapest long-form 720p anywhere.",
             "Motion-quality-led briefs, sound, frontier fidelity."),
 'Cosmos 3': ("Robotics/AV training data, action-conditioned world simulation, sensor-realistic edge-case generation.",
              "Aesthetic content of any kind."),
 'Cosmos Predict 2.5': ("Reproducible physics-grounded simulation clips for research pipelines.",
                        "Creative briefs — no format flexibility at all."),
 'Moonvalley Marey': ("Rights-sensitive commercial film work that must survive legal review, guild-adjacent productions, projects where clean provenance is the deliverable.",
                      "Raw-fidelity shootouts against frontier models (independent reviews rank it low), budget- or speed-sensitive iteration at $18/min."),
 'Infinity-Star': ("Latency-sensitive draft loops (autoregressive ≈10x diffusion speed), interactive demos.",
                   "Final renders."),
 'MAGI': ("Physics-interaction studies, cinematic prompt experiments.",
          "Value-conscious pipelines — modern peers beat it at half the price."),
 'Ovi': ("Cheap synchronized audio+video experiments, budget talking clips.",
         "Audio polish, resolution-critical work."),
 'Decart Lucy': ("Real-time and latency-critical demos, live preview pipelines, >1x-realtime batch throughput.",
                 "Quality-led deliverables, fine-grained control."),
 'ByteDance Lynx': ("Identity-locked recurring characters from one photo — brand mascots, virtual influencers.",
                    "Cost-efficient volume ($36/min is the platform's priciest), general scenes without a locked subject."),
 'FramePack': ("Long cheap autoregressive takes on weak hardware, first/last-frame in-betweens.",
               "Sharpness-critical or fast-motion shots."),
 'CogVideoX': ("Academic baselines, full-weights LoRA experiments.",
               "Production of any kind."),
 'SVD': ("Subtle micro-animation of stills — parallax, hair, smoke nudges.",
         "Everything beyond a gentle motion pass."),
 'AnimateDiff': ("Anime/stylized loops riding SD LoRA ecosystems, retro-pipeline compatibility.",
                 "Coherent modern-quality clips."),
 'T2V-Turbo': ("Instant thumbnails and drafts.", "All final work."),
 'HeyGen': ("Presenter-led training and onboarding, personalized sales/marketing at scale, multilingual spokesperson content, a digital twin of a real founder or host.",
            "Non-presenter creative scenes, action beyond the speaker, one-off cheap clips (avatar setup overhead)."),
 'VEED': ("Cheapest talking-photo presenter clips at scale, UGC-flavored spokes-content.",
          "Full-scene creative, expressive physical performance."),
 'Mirage Avatar-X': ("Long-form avatar content (up to 180 s), identity-critical brand ambassadors, expressive delivery.",
                     "Quick one-offs (voice-reference setup friction), non-human scenes."),
 'OmniHuman': ("Audio-driven full performances — gesture and emotion, not just lips: virtual instructors, spokespeople, live-commerce hosts, multi-character scenes; works on anime and illustrated characters too (v1.5).",
               "Scene and camera direction beyond the subject, content not driven by a soundtrack."),
 'Argil': ("Script-to-UGC ads without filming, product-marketing explainers.",
           "Custom framing or scene control."),
 'fal AI-Avatar': ("Two-person conversation scenes — podcast mockups, interviews; text-driven avatar clips.",
                   "Long takes (drift), budget single-speaker work (cheaper picks exist)."),
 'Sync Lipsync': ("Lip-syncing illustrations and animated characters, localizing stylized content.",
                  "Body language, photoreal talking heads (dedicated avatar models win)."),
 'Talking-head (legacy)': ("Free/instant lip-sync previews, mouth-region localization tests.",
                           "Anything client-ready."),
 'Utility': ("Slideshow assembly, frame interpolation, probing media metadata inside pipelines.",
             "Generation of any kind."),
}

# Targeted side revisions where Aug-2026 research contradicted or sharpened
# the original capability verdicts.  family -> (strong or None, weak or None)
SIDE_REVISIONS = {
 'Alibaba Happy Horse': (
   "Arena-topping quality — #1 T2V and I2V Elo on Artificial Analysis (Apr 2026); single-pass audio+video with native lip-sync in 7 languages; up to 9 reference images on v1.1. Built by Taotian's Future Life Lab under a former Kling tech lead.",
   "No multi-shot or start/end-frame control, 1080p ceiling, and a young ecosystem — few third-party workflows exist yet."),
 'MiniMax H3': (
   "Frontier omni-modal model — 2K native with stereo audio, V2V motion transfer, accurate on-screen text and brand rendering, LoRA and reference modes, 5–15 s across seven aspect ratios.",
   "Premium pricing at 2K/4K; 15 s hard cap; the open-weights license needs legal review for commercial use."),
 'FLUX.3 Video': (
   "BFL's frontier multimodal model: strong facial expressiveness, sound-event association and multilingual speech, with a full control surface (t2v/i2v/first-last/keyframes) and cheap draft modes. Vendor evals claim wins over Kling v3 Pro and Ray 3.2.",
   "Weeks old — the flattering comparisons are vendor-run with no published methodology; quality tier is pricey at 1080p; little community knowledge."),
 'Hunyuan 1.5': (
   "Fully open Apache-2.0 8.3B model that runs on ~14 GB consumer GPUs; strong prompt adherence and motion for its size; ~2x faster inference via SSTA attention.",
   "fal's endpoint serves 480p only — 1080p needs the self-hosted super-resolution pass; no audio; smaller LoRA ecosystem than Wan."),
 'Moonvalley Marey': (
   "Trained exclusively on fully licensed data — the only clearly clean-rights model here, with 3D-aware camera/motion controls aimed at director-grade precision.",
   "Independent reviews rank its raw output quality near the bottom of the frontier field; by far the most expensive ($18/min); no audio."),
 'LongCat': (
   "Natively pretrained on video continuation — sustains minutes-long 720p/30fps output without color drift or degradation, a first-class long-video design no other open model has. Distilled tier costs pennies.",
   "Motion quality trails frontier models; no audio; separate endpoints per resolution."),
 'Wan 2.7': (
   "Thinking-mode prompt planning, subject+voice references, first/last-frame control and 9-grid multi-image input; reviewers call it the most cinematic mid-tier model of 2026 — camera moves stopped looking AI-made.",
   "Effective range is 5–10 s clips — not built for long coherent stories; LoRA/community tooling still lags Wan 2.2."),
 'Kling O3': (
   "Kling's omni line: reference-driven generation and editing — elements, start/end frames, restyle of existing footage — at a lower price than v3, with a 4K variant tuned for stylized/anime looks.",
   "Fine texture (skin pores, fabric, water) renders softer than v3; audio surcharge; photoreal close-ups favor the v3 line."),
 'Vidu Q3': (
   "Best-in-class multi-reference consistency (mix mode) with 1–16 s continuous takes — holds character features a full 16 s without the melting-face effect; particularly strong anime/illustrated output.",
   "The 2.2x multiplier for 720p/1080p makes it pricey (~$9.24/min); fast motion breaks reference lock; audio support is thin."),
 'Kling 2.5T': (
   "Excellent motion fluidity and prompt precision at a low flat rate — topped the Artificial Analysis arena at release at ~10x less than Veo; the value pick in the Kling line.",
   "No audio at all, 5 s/10 s only, and noticeably aggressive content moderation rejects borderline prompts."),
 'Grok Imagine 1.5': (
   "Debuted #1 on the Image-to-Video Arena — animates stills while preserving composition and identity; audio at every tier; editing mode for wardrobe/object swaps; clip continuation from the last frame.",
   "720p ceiling on i2v output; limited camera-path control; 15 s cap; X-ecosystem moderation is idiosyncratic — and violations still bill."),
 'OmniHuman': (
   "Generates performance, not just lip-sync — gesture, emotion and intent correlate with the audio (trained on 18,700 h of human motion); v1.5 handles minute-plus takes, multi-character scenes, and anime/illustrated styles.",
   "Needs a good reference image and clean audio; no scene/camera direction beyond the subject."),
 'Bernini-R': (
   "Open-weights renderer (fine-tuned from Wan) whose editing quality reaches the first tier of commercial closed models — style transfer, watermark/subtitle removal, local edits, reference-guided variants.",
   "Renderer-only: skips the semantic planner, so complex instructions and from-scratch human generation lag; no audio."),
 'Gemini Omni Flash': (
   "Conversational video editing — generate, then refine through natural-language turns; Gemini world-knowledge grounding with physics-aware output; 3–10 s at 720p/24fps.",
   "Preview model: 10 s cap, 16:9/9:16 only, aggressive Google safety filtering."),
 'Seedance 2.5': (
   "Native 30-second single-shot generation with whole-shot reasoning; accepts dozens of multimodal references in one joint pass, plus region-level editing. Seven aspect ratios.",
   "By far the priciest per second at 720p (~$0.47/s) — and 720p is the ceiling on fal; long renders make iteration slow."),
}


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else (
        'final.json' if os.path.exists('final.json')
        else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'models.json'))
    rows = json.load(open(src))
    missing = set()
    n_use = n_rev = 0
    for r in rows:
        fam = r['family_key']
        if fam in USE:
            r['f_use_strong'], r['f_use_weak'] = USE[fam]
            n_use += 1
        else:
            missing.add(fam)
            r.setdefault('f_use_strong', '')
            r.setdefault('f_use_weak', '')
        if fam in SIDE_REVISIONS:
            s, w = SIDE_REVISIONS[fam]
            if s: r['f_strong'] = s
            if w: r['f_weak'] = w
            n_rev += 1
    json.dump(rows, open(src, 'w'), indent=1)
    print(f'use-cases applied to {n_use} rows; side revisions to {n_rev} rows')
    print('families lacking use-cases:', sorted(missing) or 'none')


if __name__ == '__main__':
    main()
