# HSI Open-Corpus Renderer / 1.0

A non-AI music renderer that uses openly indexed audio recordings plus deterministic traditional DSP.

Protocols:

```text
HSI-OPEN-CORPUS/1.0
HSI-PLEIADIAN-BLUE-CARE/1.0
```

## One-line launch

iSH:

```sh
wget -qO- https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-corpus.sh | sh
```

macOS:

```sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-corpus.sh | sh
```

Direct runtime input:

```sh
# iSH
wget -qO- https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-corpus.sh | sh -s -- "Blue Pleiadian Stars"
```

```sh
# macOS
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-corpus.sh | sh -s -- "Blue Pleiadian Stars"
```

## No AI

The renderer does not load or call an AI model.

```text
ai_model       = false
neural_renderer= false
machine_learning = false
```

It uses:

```text
runtime input
  ↓
E257 deterministic field
  ↓
Openverse audio search
  ↓
CC0 / Public Domain Mark metadata gate
  ↓
WAV recordings
  ↓
deterministic fragment selection
  ↓
linear-resampling playback-rate transform
  ↓
fades / gain / pan / finite stereo delay
  ↓
song.wav
  ↓
E257 + SHA-256 + provenance certificate
```

All synthesis/mixing operations are ordinary arithmetic/DSP.

## YouTube policy

YouTube is not used as an audio-download source by this renderer.

```json
"youtube_audio_used": false
```

A future discovery layer may use public web pages to identify creators, instruments or works, but any acoustic material admitted to the corpus must come from an independently permitted media source.

## Openverse gate

The automatic v1 gate accepts only results whose Openverse metadata says:

```text
license = cc0 OR pdm
filetype = wav
```

This is intentionally narrower than the full Creative Commons family.

Openverse is an index of openly licensed/public-domain media, but Openverse itself warns that its license metadata can be inaccurate. Therefore HSI keeps two closure concepts separate:

```text
technical_closed = DSP / WAV / E257 / provenance checks succeeded
rights_closed    = independent rights review has been attested
```

By default:

```text
rights_closed = 0
license_assurance = OPENVERSE_INDEX_ASSERTED_NOT_INDEPENDENTLY_VERIFIED
```

Do not interpret `technical_closed=1` as legal clearance.

After independently checking every source landing page, a user can explicitly run with:

```sh
HSI_RIGHTS_VERIFIED=1 sh hsi-corpus.sh "..."
```

That flag records a user attestation; it is not a legal opinion.

## Reproducibility

Every run writes:

```text
corpus.lock.json
```

which contains the exact selected Openverse IDs, source URLs, licensing metadata and source hashes.

To re-render from the same corpus selection:

```sh
HSI_CORPUS_LOCK=/path/to/corpus.lock.json sh hsi-corpus.sh "same runtime input"
```

Downloaded WAV files are cached under:

```text
~/.hsi-corpus/cache/
```

If the files are still cached, a lock-based rerun does not need a new Openverse search.

## Output

```text
~/Music/HSI-Corpus/YYYYMMDD-HHMMSS-PID/
├── keywords.txt
├── corpus.lock.json
├── events.json
├── song.wav
├── song.e257
├── song.hsicert
└── manifest.json
```

The certificate records every source actually used:

- Openverse ID
- title
- creator
- indexed license/version
- original media URL
- upstream landing page
- provider/source
- source SHA-256
- source byte count
- rights-assurance state

and every render event is separately recorded in `events.json`.

## Pleiadian Blue

Blue is not a genre or prompt.

Its role here is:

```text
provenance
license truthfulness
uncertainty preservation
human override
semantic non-coercion
```

If rights are not independently verified, HSI preserves that fact instead of coercing it into a false `CLEARED` state.

## Openverse authentication

Anonymous API access is supported by Openverse and is normally enough for small interactive use.

An optional Openverse bearer token can be supplied as:

```sh
export OPENVERSE_TOKEN="..."
```

No token is required by HSI v1 for ordinary anonymous operation.

## Technical limits of v1

The first version deliberately accepts only uncompressed WAV sources so that both iSH and macOS can use the Python standard library without ffmpeg.

Quality depends on the retrieved recordings. This is a retrieval-and-remix renderer, not yet a full note-by-note multisample orchestra or concatenative singing engine.

Later versions can add:

- curated multisample banks;
- instrument/phoneme indexing;
- phase-vocoder time stretching;
- PSOLA-style vocal rendering;
- convolution impulse responses;
- license-verified persistent corpus snapshots.

None of those require generative AI.
