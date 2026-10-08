# HSI Native Generative Field / 1.0

A fully local HSI music generator for iSH / Alpine with **zero creative-content presets**.

The public launcher is unchanged:

```sh
wget -qO- https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-native.sh | sh
```

Then enter runtime input only:

```text
keywords>
```

Or pass it directly:

```sh
wget -qO- https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-native.sh | sh -s -- "Blue Pleiadian Stars"
```

## Zero-preset meaning

The default generation path does **not** contain preset:

- song topic
- lyrics sentences
- Verse / Chorus structure
- musical style
- BPM
- bar count
- meter
- scale bank
- chord progression bank
- melody pattern
- vowel/formant lookup table
- voice identity

Instead, the exact runtime input is encoded as:

```text
field_n = E257(runtime_input_utf8)
```

and all creative parameters are derived from that state.

```text
runtime input
   ↓
E257 field state
   ↓
derived section count / section lengths
   ↓
derived textual motifs using only runtime tokens
   ↓
derived pitch-class field
   ↓
derived tonic / meter / subdivision / BPM / bar count
   ↓
derived harmony / rhythm / melody
   ↓
derived harmonic spectra / token spectra / space / dynamics
   ↓
PCM WAV
   ↓
reversible E257 audio blocks
   ↓
HSI-NATIVE-FIELD/1.0 certificate
```

The renderer necessarily still contains **computation laws**: arithmetic state transitions, oscillator synthesis, PCM/WAV serialization, E257 encoding, and closure checks. Those are renderer semantics, not creative-content presets.

## PLEIADIAN-BLUE

`PLEIADIAN-BLUE` is retained only in the certificate as a normative identifier.

It is **not** mixed into the generation seed and is not used to choose lyrics, harmony, melody, rhythm, timbre, or structure:

```json
"blue_role": "certificate-normative-only",
"blue_conditioning": false
```

## Outputs

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

`lyrics.txt` contains only recombinations / truncations / rotations of runtime input tokens. No stock lyric sentences are inserted.

The current native vocal layer is procedural spectral/formant-like synthesis derived from each runtime token. It is not claimed to equal a neural human singer or to pronounce full natural-language lyrics perfectly.

## Closure

`closed=1` requires:

- valid RIFF/WAVE output;
- exact E257 reconstruction of the WAV bytes;
- exact E257 round-trip of runtime input;
- exact E257 round-trip of the Blue certificate identifier.

The certificate also records the actual SHA-256 of the generated WAV.

## Optional overrides

By default, creative parameters are field-derived. Optional explicit overrides remain available when the user intentionally wants one:

```sh
HSI_BPM=108 ...
HSI_BARS=24 ...
HSI_SR=32000 ...
HSI_OUT=/some/path ...
```

An override is therefore a runtime user instruction, not a built-in preset.

## Offline use

The one-line launcher downloads the latest renderer to:

```text
~/.hsi-native/hsi_native_renderer.py
```

After that, the cached renderer can run offline:

```sh
python3 ~/.hsi-native/hsi_native_renderer.py "Blue Pleiadian Stars"
```
