# 影音｜HSI Peace AV Archive

This folder is the **persistent archive** for the original English-language peace-address video system.

## Layout

- `index.json`: all verified run indexes, newest first.
- `runs/<github-run-id>/peace_address_english.mp4`: final English film.
- `runs/<github-run-id>/voiceover.en.mp3`: English narration audio, without score.
- `runs/<github-run-id>/captions.en.srt`: English subtitles (timing estimated at sentence-fragment level).
- `runs/<github-run-id>/transcript.en.md`: full English transcript and sources.
- `runs/<github-run-id>/correspondence.json`: each scene's finite input-to-output association, musical properties, Notes inventory hashes, and policy goal.
- `runs/<github-run-id>/frame_correspondence.jsonl`: frame-indexed parameters actually recorded by this renderer.
- `runs/<github-run-id>/SHA256SUMS` and `manifest.json`: integrity checks and archive verification.

The above folders are written to `main` only when the new GitHub Actions workflow runs on `main`, by schedule (every Monday, 09:30 Taiwan time) or manually. Pull requests create **downloadable temporary artifacts only**, and do not archive to the default branch. Scheduled runs activate after this PR has been merged.

## The philosophical correspondence is scoped

This is a finite, explicit input/output specification informed by `Notes/1`, `Notes/2`, `Notes/3`, `Notes/4` and the eight-file `Notes/HSI_Prime_Analytic_2KB_Release` collection. Each run fingerprints these sources, without executing them. Scene-to-peace-goal associations, musical keys, and emotional cues are **editorial choices**, not deductions from Gödel coding or proofs that conflict has ended. World peace cannot be verified by a successful video render.

**Video limitations:** Today the renderer outputs original English title scenes and optional still-speaker artwork. It DOES NOT synthesize a natural moving human mouth, generate authentic facial motion, or validate phoneme-to-lip synchronization. Photorealistic speaking video requires separately licensed source footage or a properly configured video/lip-sync generator plus independent quality checks; neither is silently assumed. No public official is impersonated. If a speaker still is provided, it is clearly documented as a still image.

**Voice:** Microsoft Edge English neural voice via the community `edge-tts` integration; this is not the Azure commercial API. This online dependency can fail when external service behavior changes. Background music is original bounded deterministic DSP, designed per topic at a modest volume, not derived by a physical equation proving a corresponding emotion.

**Storage warning:** Keeping every movie in Git eventually grows repository history. The workflow rejects files larger than 60 MiB and archives only one run each week. If volume grows, migrate movie bytes to GitHub Releases or an object store while retaining the run-index and integrity hashes in this folder. No automatic deletion of past archive runs is configured.

## Manual execution

```sh
python3 -m pip install edge-tts pillow
python3 peace_av/render_long.py --engine edge --output 影音/manual
```

On GitHub, view *Actions → HSI English Peace AV Continuous Build*. Actual duration must be at least 600 seconds. The first PR build can be retrieved from its workflow artifact before any merge.
