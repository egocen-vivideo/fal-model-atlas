# fal.ai Video Model Atlas

Every video generation endpoint on fal.ai — text-to-video, image-to-video and
reference-to-video — with pricing normalised to a common unit and a capability
matrix, so we can pick models on evidence instead of vibes.

**Live tables:**
- Video — https://egocen-vivideo.github.io/fal-model-atlas/ (403 generation endpoints)
- Video repurpose — https://egocen-vivideo.github.io/fal-model-atlas/repurpose.html (232 video-to-video endpoints)
- Image — https://egocen-vivideo.github.io/fal-model-atlas/image.html (612 endpoints)
- Audio — https://egocen-vivideo.github.io/fal-model-atlas/audio.html (139 endpoints)

> ⚠️ **This repository and the published site are both public.** GitHub Pages is
> not available on private repos on the Free plan, and access-controlled Pages
> needs Enterprise Cloud — so public was the only way to get a working URL
> without a plan change. The site carries `noindex` and a `robots.txt` deny, so
> it should stay out of search results, but anyone with the link (or the repo
> URL) can read everything here, including the model shortlist and the
> strongest/weakest assessments. Treat it accordingly. To close that up later,
> see [Making it actually private](#making-it-actually-private).

## What's in it

**635 video endpoints across 126 model families, split over two tabs** so
neither gets crowded:

- **Video** (`index.html`) — the **403 generation** endpoints: text-to-video,
  image-to-video, reference-to-video and audio-to-video. Second column is
  **Type** (T2V / I2V / REF).
- **Video repurpose** (`repurpose.html`) — the **232 video-to-video** endpoints:
  everything that takes finished footage and changes it. Second column is
  **Task** (extend, edit/restyle, inpaint/erase, lipsync, upscale/restore,
  interpolation, video→audio, analysis/masking, utility).

Both run the same engine and carry the same columns and verdict panels. For
each endpoint:

| Field | Source |
| --- | --- |
| Cost per minute @ 720p | fal's pricing copy, normalised (see below) |
| Max frame count | `num_frames` max, or duration × fps |
| Duration options | `duration` enum / range |
| Quality options | `resolution` enum |
| Aspect ratio options | `aspect_ratio` enum |
| Audio | `generate_audio` / audio input params |
| Start frame | `image_url`, `start_image_url`, `first_frame_url`… |
| End frame | `end_image_url`, `tail_image_url`, `keyframes`… |
| More than one cut | `multi_prompt`, `shot_type`, `multi_shots` |
| Lipsync | endpoint class + audio-driven params |
| fal status | active / unlisted / deprecated / retiring (dated fal notice) — see below |
| Task | what the endpoint does — generate / extend / edit / upscale / lipsync / … |
| Strongest / weakest side | capability verdict per family — **judgement, not benchmark** |
| Strongest / weakest use-cases | production-scenario verdict per family — what to reach for it for, and what to avoid |

Every column is operable: click the Endpoint/Type/$-min/Max-frames headers to
sort ascending or descending, filter any column through its checkbox dropdown
(duration is enumerated as explicit seconds), and set min–max ranges on price
and frames. All filters, ranges, the sort, and text search apply concurrently.

## How to read the price column

fal bills in five incompatible units: per second, per video, per 5s-plus-extra,
per megapixel, and per 1000 tokens. Everything is converted to **USD per 60
seconds of 720p output** purely so the numbers are comparable.

**It is a rate, not a shopping cart.** Most of these models cap out at 5–15
seconds, so a full minute is not a single generation. Where a model bills per
megapixel or per token, 720p at the endpoint's native frame rate is assumed.
Where audio-on and audio-off differ, the table shows **audio-off**; the audio-on
figure is in the expanded row.

Range: **$0.24/min** (`fal-ai/ltx-video`) to **$36/min** (`bytedance/lynx`),
median **$4.80**.

Twelve legacy endpoints (SVD, AnimateDiff, SadTalker, MuseTalk, LivePortrait,
T2V-Turbo…) are billed per GPU compute-second and have no fixed output rate —
they show as `compute-billed`. **Max frames** is blank where output length simply
follows the driving audio or video.

### Two corrections to fal's own copy

- **Hunyuan 1.5** — the pricing blurb says `0.075 cents/s`; the same page body
  says `$0.075 per second`. The latter is used ($4.50/min). It is also 480p, not
  720p.
- **Veo 3.1** — the copy places the 4K price where a naive parse picks it up. The
  720p no-audio rate is $0.20/s → $12.00/min.

## Unlisted, deprecated and retiring endpoints

fal's `/api/models` index does not return every endpoint it serves. Since
September 2026 it hides the **whole Veo 3.1 family** (`status: unlisted`) and
everything it marks **deprecated** (Kling 1.x / 2.0 / 2.1, Veo 3), yet those
endpoints still have a model page and a working queue schema. The sitemap no
longer helps — `sitemap-0.xml` is gone and `sitemap.xml` mirrors the index — so
`scripts/09_unlisted.py` now discovers them by (1) re-checking every endpoint
the atlas carried before, (2) probing sibling paths of fast-moving families,
and (3) reading the sibling records embedded in each model page. Each candidate
is confirmed live against its OpenAPI schema, and its page's embedded model
record supplies title, category, pricing copy and status.

Every row carries a **fal status** (filterable, and badged in the table):

- **active** — listed in fal's index.
- **unlisted** — live, not in the index (31 video rows).
- **deprecated** — fal marks it deprecated; still callable (20 video rows: Kling
  1.x–2.1, Veo 3).
- **retiring** — fal publishes a dated notice (`endpoint_messages` on every
  model page): **Veo 3.1, all 14 endpoints, deprecated on 17 Nov 2026**; Luma
  Ray 2 / Ray 2 Flash (8) on 25 Oct 2026; Decart Lucy Edit Pro on 22 Oct 2026.

Endpoints whose schema and page are gone are **dropped**, not flagged. This
pass dropped `alibaba/happy-oyster` (video) and Reve 2.1 ×3 (image). **Sora 2**
was never in the atlas; OpenAI removed the Sora API on 24 Sep 2026 and fal's
`sora-2` endpoints no longer resolve.

> ⚠️ **fal rate-limits the OpenAPI endpoint.** Probing thousands of candidates
> at high concurrency returns near-100% false 404s. Keep concurrency ≤ 3 with
> backoff — otherwise every "dead" result is a lie. This bit during the Aug 28
> pass: 49 endpoints reported dead at 16 threads were all live at 4.

## Promotional prices

Where fal's copy states a promo and the price that applies afterwards, the table
records the **regular** rate and the expanded row names the promo rate and its
end date: MiniMax H3-Max / H3-Max Turbo (40% off until 15 Oct 2026 →
$0.08 / $0.04 per second at 768p), Vidu Q4 (30% off until 30 Nov 2026 →
$0.095/s at 720p), FLUX.3 image (launch promo ended 8 Oct → $0.048 per 1 MP).

## Caveats worth stating plainly

- **Strongest/weakest sides and use-cases are my assessment**, written per
  family. Sides describe capabilities; use-cases name production scenarios —
  deliberately distinct research objectives. Sourced from each family's fal
  model page (scraped Aug 2026, refreshed Oct 2026) plus external research:
  Artificial Analysis arena rankings (Sept 2026 refresh), Curious Refuge reviews, vendor technical reports, and
  practitioner write-ups. They are not benchmark results. Shortlist, then test.
- **Prices move.** fal changes pricing without notice. Re-run the pipeline before
  making a decision that depends on a specific number.
- **Schema ≠ behaviour.** A parameter existing in the OpenAPI schema doesn't
  guarantee it works well. `keyframes` support, for instance, varies a lot in
  quality between models that both expose it.

## Repo layout

```
index.html                 video generation atlas (403) — self-contained, no deps
repurpose.html             video-to-video atlas (232), same engine
image.html audio.html      image and audio atlases, same engine, separate pages
robots.txt                 deny-all
data/
  fal_video_models.csv     flat export, all 635 video rows incl. Task + fal status
  fal_image_models.csv     612 image rows incl. verdicts
  fal_audio_models.csv     139 audio rows incl. verdicts
  image_rows.json audio_rows.json   full extracted records
  models.json              full records incl. raw pricing text and schema fields
  payload.json             compact payload the page embeds
scripts/
  01_fetch_catalog.py      paginate fal's model index
  02_fetch_schemas.py      pull each endpoint's openapi.json + fallback page scrape
  03_extract.py            read spec fields out of the schemas
  04a_price_pass1.py       first-pass price parse
  04b_price_final.py       final price engine → USD/min @720p
  05_fields.py             derive duration/quality/aspect/audio/frame/cut/lipsync
  06_known_durations.py    fill durations the schema doesn't expose
  06b_families.py          family + Task per endpoint (carried from data/, rules for new ids)
  07_verdicts.py           strongest/weakest side per family
  07b_usecases.py          strongest/weakest use-cases + research-driven side revisions
  07c_v2v_verdicts.py      verdicts for families added after the first pass (+ Oct revisions)
  09_unlisted.py           endpoints live on fal but absent from its index (runs after 01)
  08_build_site.py         emit index.html + repurpose.html + data exports
  media/                   image + audio pipeline:
    10_fetch_catalogs.py   fal index for t2i/i2i + tts/t2a/a2a/s2s (+ re-check dropped ids)
    10b_fetch_schemas.py   queue OpenAPI schemas → oas2/
    11_scrape_pages.py     model pages for endpoints without pricing metadata
    12_extract_media.py    fields + $/image@1MP and $/min normalisation + families
    verdicts_media.py      per-family sides + use-cases (Aug 2026, Oct 2026 additions)
    build_media.py         emit image.html + audio.html + CSVs
  head.html body.html app.js   site source
```

## Refreshing the data

The pipeline scripts read and write in the current directory, so run them from a
scratch working dir. Order matters — `09` runs straight after `01` (it appends
unlisted endpoints to the catalog so every later step treats them like listed
ones):

```bash
mkdir -p /tmp/atlas/video /tmp/atlas/media
S=/path/to/fal-model-atlas/scripts

# image + audio first (08 reads their row counts for the tab bar)
cd /tmp/atlas/media
python3 $S/media/10_fetch_catalogs.py   # → all_image_models.json, all_audio_models.json (+ re-checks dropped ids)
python3 $S/media/10b_fetch_schemas.py   # → oas2/
python3 $S/media/11_scrape_pages.py     # → pages2/ (pricing copy where metadata has none)
python3 $S/media/12_extract_media.py    # → image_rows.json, audio_rows.json
python3 $S/media/build_media.py .       # → image.html + audio.html + data/

# video
cd /tmp/atlas/video
python3 $S/01_fetch_catalog.py      # → all_video_models.json (t2v, i2v, v2v + audio-to-video, video-to-audio, video-to-text)
python3 $S/09_unlisted.py           # → appends live-but-unlisted endpoints; endpoint_messages.json
python3 $S/02_fetch_schemas.py      # → oas/, pages/, page_pricing.json
python3 $S/03_extract.py            # → extracted.json
python3 $S/04a_price_pass1.py       # → priced.json
python3 $S/04b_price_final.py       # → priced2.json
python3 $S/05_fields.py             # → final.json
python3 $S/06_known_durations.py    # patches final.json
python3 $S/06b_families.py          # patches final.json: family_key + Task
python3 $S/07_verdicts.py           # patches final.json
python3 $S/07b_usecases.py          # patches final.json
python3 $S/07c_v2v_verdicts.py      # patches final.json
python3 $S/08_build_site.py         # → index.html + repurpose.html + data/
cd ../media && python3 $S/media/build_media.py .   # refresh the tab counts on image/audio
```

Then commit — Pages redeploys on push to `main`.

Steps 01/09/02 hit fal roughly 1,000 times over 20–30 minutes at ≤3 concurrent
requests. `oas/`, `pages/` and `pages_unlisted/` are cached on disk, so re-runs
are cheap.

## Making it actually private

If the public URL isn't acceptable, the options are:

1. **Make the repo private again and drop Pages.** `index.html` is one
   self-contained file — clone the repo and open it. GitHub's repo ACL becomes
   the only gate. Costs nothing.
2. **Cloudflare Pages + Access.** Free. Make the repo private again, connect it
   to Cloudflare Pages, add an Access policy for `@vivideo.ai` emails. Real
   auth, real URL, auto-deploys on push. This is the option to take if the
   public URL ever becomes a problem.
3. **GitHub Pro ($4/mo).** Repo goes back to private and Pages keeps working —
   but the site URL stays publicly reachable. Only fixes repo exposure.
4. **GitHub Enterprise Cloud.** Move the repo to an org on Enterprise Cloud and
   set Pages visibility to private. The only setup where the *site* is gated.

---

Video, image and audio data current as of **14 October 2026**.
