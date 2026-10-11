# Experimental Speaking Portrait — English Peace Address

**Status:** audibly driven original portrait animation, not filmed footage, not a human performance recording, and not a phoneme-verified lip-sync generator.

This optional system is separate from the verified static English film. It takes the existing `影音/` archive MP4, an original synthetic portrait, and the available narration audio. The voice-band RMS envelope drives a small, smooth lower-face warp with subtle camera motion. Background music and English narration remain from the existing, verified film.

## Reproducibility

- `peace_av/assets/speaker_original.jpg` is an **original AI-generated fictional character**, not a real politician. The image is a compact JPEG for deterministic automation and is not a source of real film frames.
- `peace_av/experimental_speaker.py` is deterministic given exact image/audio files and parameters (encoding can still vary by ffmpeg version).
- `experimental_speaker_en.mp4` shows the animated original portrait. Its accompanying `.provenance.json` records portrait, audio and output SHA-256, as well as an explicit **false** flag for phoneme/viseme alignment.
- The workflow `Experimental English Speaking Portrait` creates a short trial on this pull request, then accepts a manual duration. After merge, when the full English AV build succeeds, the completed-workflow event requests a long experimental animation.
- The generated animation is a **90-day GitHub Actions artifact**, **not** an endorsed and permanently archived lip-sync result in `影音/`. Independent phoneme timing and human-perceived visual quality tests must be designed before making a permanent publication claim.

## Local demo

```sh
python -m pip install numpy pillow opencv-python-headless
python peace_av/experimental_speaker.py \
  --portrait peace_av/assets/speaker_original.jpg \
  --movie 影音/runs/38131789251/peace_address_english.mp4 \
  --voice 影音/runs/38131789251/voiceover.en.mp3 \
  --seconds 20 --fps 12 \
  --output speaker_demo.mp4
```

Do not use the separate narration file as a precise drive track for the **full** duration, because the long film inserts pauses at scene boundaries and the standalone MP3 is concatenated without the exact same timeline; leave `--voice` off for a long preview. The mixed audio's background music can also affect amplitude-driven mouth movement. A proper future system should use word/phoneme alignment and a licensed facial-performance renderer.

## Boundaries

This stage demonstrates **a computational input/output mapping**: English soundtrack amplitude and time \(X_t\) determine visible mouth warp and camera pose \(Y_t\). It does not guarantee recognizable speech visemes, gesture realism, synchrony quality, or conflict-resolution outcomes. This is an original cinematic rendering, not evidence that the speaker, event, or statements actually occurred. Public-facing publications should disclose synthetic media origin in their description.
