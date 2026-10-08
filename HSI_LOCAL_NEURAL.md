# HSI Local Neural Renderer / 1.0

HSI control and closure around a **local ACE-Step 1.5 neural music renderer** on Apple Silicon Macs.

The goal is to keep HSI's runtime-input-only semantics while replacing the procedural oscillator layer with a learned local music model.

## One-line macOS launch

Interactive:

```sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-neural.sh | sh
```

Direct:

```sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-neural.sh | sh -s -- "Blue Pleiadian Stars"
```

Requirements:

- macOS on Apple Silicon (`arm64`)
- Git / Apple Command Line Tools
- internet access for the first installation and model-weight downloads
- sufficient disk space and unified memory for ACE-Step

The launcher pins ACE-Step to commit:

```text
ca1e85fe9430179831e6bc6be790c332190a3866
```

Override only when intentionally testing another revision:

```sh
HSI_ACE_REF=<commit> curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-neural.sh | sh
```

## First run

The launcher:

1. installs `uv` if it is absent;
2. clones ACE-Step 1.5 into `~/.hsi-neural/ACE-Step-1.5`;
3. checks out the pinned revision;
4. runs `uv sync`;
5. starts the official macOS local API server through `start_api_server_macos.sh`;
6. waits for local `/health`;
7. runs the HSI client.

ACE-Step model weights may be several GB and can be downloaded on first model initialization.

## Zero HSI creative presets

The HSI request contains only:

```json
{
  "sample_query": "<exact runtime input>",
  "thinking": true,
  "use_random_seed": false,
  "seed": "<E257-derived deterministic integer>",
  "batch_size": 1,
  "audio_format": "wav"
}
```

HSI does **not** inject:

- prompt/style tags
- lyrics
- BPM
- duration
- key/scale
- time signature
- Verse/Chorus structure
- model name

Those musical decisions are learned-model outputs, not HSI creative presets.

## Deterministic HSI seed

The runtime input is encoded by E257:

```text
basis = E257(runtime_input_utf8)
seed  = basis mod 2147483647
```

The learned renderer may still contain implementation-level nondeterminism depending on its backend, but HSI submits the same explicit seed for the same input.

## Output

Each run creates:

```text
~/Music/HSI-Neural/YYYYMMDD-HHMMSS-PID/
├── keywords.txt
├── request.json
├── result.json
├── lyrics.txt        # when the neural model returns lyrics
├── song.wav
├── song.e257
├── song.hsicert
└── manifest.json
```

The certificate records the actual renderer-returned prompt, lyrics, metadata, DiT model, LM model, seed value, WAV SHA-256, and E257 closure.

Truthful renderer flags:

```json
{
  "neural_renderer": true,
  "local_model": true,
  "local_http_api": true,
  "external_cloud": false,
  "external_paid_api": false
}
```

## Local architecture

```text
runtime input
    ↓
HSI E257 basis / deterministic seed
    ↓
localhost ACE-Step API
    ↓
local MLX neural model on Apple Silicon
    ↓
learned caption / lyrics / structure / singing / production
    ↓
WAV
    ↓
HSI E257 + SHA-256 + certificate
```

The localhost API is a process boundary only; it is not a paid cloud renderer.

## Mobile / iPhone path

An Apple configuration profile (`.mobileconfig`) is not an executable-app container. It can deploy settings and can place a Web Clip on the Home Screen, but it cannot package the Python/MLX model runtime itself.

Three viable HSI mobile layers are therefore:

1. **Web Clip / PWA front end** — a profile may install an HSI Music icon that opens a full-screen web UI. The heavy neural renderer remains on the user's Mac or another authorized HSI node.
2. **Native SwiftUI app** — distributed for development/ad hoc use, TestFlight, or App Store. The app submits HSI requests to an authorized local/private renderer and displays progress/audio.
3. **Future on-device renderer** — if a sufficiently small/quantized model can fit iPhone memory and be converted to a supported local inference runtime, the same HSI protocol can move the renderer inside the app. This is a future optimization, not assumed by v1.

The HSI protocol should therefore remain transport-neutral:

```text
HSI iPhone UI
      ↓
HSI request / certificate protocol
      ↓
renderer node
   ├─ Mac local neural renderer (v1)
   └─ future on-device model
```

This preserves the app interface while allowing the rendering location to evolve.
