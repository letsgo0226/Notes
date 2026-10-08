# HSI Native Renderer / 1.0

A fully local HSI music renderer for iSH / Alpine. It does **not** call Runway, fal, Mureka, Railway, or any other generation API.

## Public one-line launch

Interactive:

```sh
wget -qO- https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-native.sh | sh
```

Then enter keywords at:

```text
keywords>
```

Direct:

```sh
wget -qO- https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-native.sh | sh -s -- "Blue Pleiadian Stars"
```

The bootstrap installs Python 3 with `apk` only when Python is absent, downloads the current native renderer into `~/.hsi-native/`, and executes it locally.

After the renderer has been downloaded once, the cached program can be run directly:

```sh
python3 ~/.hsi-native/hsi_native_renderer.py "Blue Pleiadian Stars"
```

That direct cached invocation is offline.

## Output

Each run creates:

```text
~/Music/HSI/YYYYMMDD-HHMMSS-PID/
├── keywords.txt
├── lyrics.txt
├── score.json
├── song.wav
├── song.e257
├── song.hsicert
└── manifest.json
```

The default render is 20 bars at a deterministic tempo derived from the keyword seed. The renderer uses only the Python standard library.

## Native synthesis pipeline

```text
keywords
  ↓
deterministic seed
  ↓
procedural original lyrics
  ↓
scale / chord progression / melody
  ↓
pad + bass + percussion
  ↓
vocal-like formant synthesis
  ↓
PCM WAV
  ↓
128-byte reversible E257 blocks
  ↓
HSI-NATIVE-RENDER/1.0 certificate
```

The current v1 vocal layer is a procedural formant synthesizer. It is intentionally not described as a human-quality neural singer: `lyrics.txt` contains the generated words, while the audio maps lyric tokens to vowel/formant gestures rather than fully intelligible natural speech.

## HSI closure

The certificate closes only when:

- the output is a RIFF/WAVE file;
- E257 blocks reconstruct the exact WAV bytes;
- keyword E257 round-trips exactly;
- the `PLEIADIAN-BLUE` normative identifier round-trips exactly.

It also records the actual SHA-256 of the generated WAV. SHA-256 is used in the full native renderer; the separate 2 KB compact kernel retains its no-SHA constraint.

## Controls

Examples:

```sh
HSI_BARS=32 wget -qO- https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-native.sh | sh -s -- "moon cat home"
```

```sh
HSI_BPM=108 HSI_SR=32000 wget -qO- https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-native.sh | sh -s -- "月光 貓 回家"
```

Supported environment controls:

- `HSI_BARS`: 4–64, default 20
- `HSI_BPM`: optional explicit tempo
- `HSI_SR`: 8000–48000 Hz, default 22050
- `HSI_OUT`: optional output directory
- `HSI_NATIVE_HOME`: cache directory for the renderer

## Scope

This version demonstrates that HSI can replace the **external rendering service** with a transparent local computation. It does not imply that a small procedural synthesizer has the learned acoustic quality of a large commercial neural music model. Future native versions can add higher-quality local synthesis or local model weights without changing the public one-line launcher.
