# fal.ai Video Model Atlas

Every video generation endpoint on fal.ai — text-to-video, image-to-video and
reference-to-video — with pricing normalised to a common unit and a capability
matrix, so we can pick models on evidence instead of vibes.

**Live tables:**
- Video — https://egocen-vivideo.github.io/fal-model-atlas/ (332 endpoints)
- Image — https://egocen-vivideo.github.io/fal-model-atlas/image.html (587 endpoints)
- Audio — https://egocen-vivideo.github.io/fal-model-atlas/audio.html (126 endpoints)

> ⚠️ **This repository and the published site are both public.** GitHub Pages is
> not available on private repos on the Free plan, and access-controlled Pages
> needs Enterprise Cloud — so public was the only way to get a working URL
> without a plan change. The site carries `noindex` and a `robots.txt` deny, so
> it should stay out of search results, but anyone with the link (or the repo
> URL) can read everything here, including the model shortlist and the
> strongest/weakest assessments. Treat it accordingly. To close that up later,
> see [Making it actually private](#making-it-actually-private).

## What's in it

**332 endpoints** across **83 model families** — 132 text-to-video, 200
image-to-video, of which 27 are reference-to-video. For each one:

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

## Caveats worth stating plainly

- **Strongest/weakest sides and use-cases are my assessment**, written per
  family. Sides describe capabilities; use-cases name production scenarios —
  deliberately distinct research objectives. Sourced from each family's fal
  model page (scraped Aug 2026) plus external research: Artificial Analysis
  arena rankings, Curious Refuge reviews, vendor technical reports, and
  practitioner write-ups. They are not benchmark results. Shortlist, then test.
- **Prices move.** fal changes pricing without notice. Re-run the pipeline before
  making a decision that depends on a specific number.
- **Schema ≠ behaviour.** A parameter existing in the OpenAPI schema doesn't
  guarantee it works well. `keyframes` support, for instance, varies a lot in
  quality between models that both expose it.

## Repo layout

```
index.html                 video atlas — self-contained, no build, no deps
image.html audio.html      image and audio atlases, same engine, separate pages
robots.txt                 deny-all
data/
  fal_video_models.csv     flat export, all 332 video rows
  fal_image_models.csv     587 image rows incl. verdicts
  fal_audio_models.csv     126 audio rows incl. verdicts
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
  07_verdicts.py           strongest/weakest side per family
  07b_usecases.py          strongest/weakest use-cases + research-driven side revisions
  08_build_site.py         emit index.html + data exports
  media/                   image + audio pipeline:
    10_fetch_catalogs.py   fal index for t2i/i2i + tts/t2a/a2a/s2s
    11_scrape_pages.py     model pages for endpoints without pricing metadata
    12_extract_media.py    fields + $/image@1MP and $/min normalisation + families
    verdicts_media.py      per-family sides + use-cases (researched Aug 2026)
    build_media.py         emit image.html + audio.html + CSVs
  head.html body.html app.js   site source
```

## Refreshing the data

The pipeline scripts read and write in the current directory, so run them from a
scratch working dir:

```bash
mkdir -p /tmp/atlas && cd /tmp/atlas
S=/path/to/fal-model-atlas/scripts
python3 $S/01_fetch_catalog.py      # → all_video_models.json
python3 $S/02_fetch_schemas.py      # → oas/, pages/, page_pricing.json
python3 $S/03_extract.py            # → extracted.json
python3 $S/04a_price_pass1.py       # → priced.json
python3 $S/04b_price_final.py       # → priced2.json
python3 $S/05_fields.py             # → final.json
python3 $S/06_known_durations.py    # patches final.json
python3 $S/07_verdicts.py           # patches final.json
python3 $S/07b_usecases.py          # patches final.json
python3 $S/08_build_site.py            # → index.html + data/
```

Then commit — Pages redeploys on push to `main`.

Steps 1–2 hit fal ~420 times over a few minutes. `oas/` and `pages/` are cached
on disk, so re-runs are cheap.

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

Video data current as of **13 August 2026**; image and audio as of **18 August 2026**.
