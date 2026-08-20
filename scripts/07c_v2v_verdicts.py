"""Step 7c — verdicts for the video-to-video families added in the Aug 18 pass.

Families that already existed (Veo, Kling, LTX, Wan, Pixverse, Marey...) inherit
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


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else (
        'final.json' if os.path.exists('final.json')
        else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'models.json'))
    rows = json.load(open(src))
    n = 0
    for r in rows:
        v = V2V.get(r['family_key'])
        if v:
            r['f_strong'], r['f_weak'], r['f_use_strong'], r['f_use_weak'] = v
            n += 1
    json.dump(rows, open(src, 'w'), indent=1)
    print(f'v2v verdicts applied to {n} rows across {len(V2V)} families')


if __name__ == '__main__':
    main()
