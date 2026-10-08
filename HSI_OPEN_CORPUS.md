# HSI Open-Corpus Renderer / 1.0

A non-AI music renderer that uses openly indexed audio recordings plus deterministic traditional DSP.

Protocols:

```text
HSI-OPEN-CORPUS/1.0
HSI-PLEIADIAN-BLUE-CARE/1.0
```

## Cross-platform launch

The same HSI Open-Corpus + HSI-SEARCH semantics are available through platform-native launchers.

### iPhone / iPad — iSH

```sh
wget -qO- https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-corpus.sh | sh
```

### macOS

```sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-corpus.sh | sh
```

### Android — Termux

```sh
pkg install -y python curl && curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-corpus.sh | sh
```

After Python is installed once, the shorter form is:

```sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-corpus.sh | sh
```

### Windows — PowerShell

```powershell
$p = Join-Path $env:TEMP "hsi-corpus.ps1"; Invoke-WebRequest -UseBasicParsing "https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-corpus.ps1" -OutFile $p; & $p
```

The native Windows launcher downloads the same `hsi_net.py`, `hsi_search.py`, and `hsi_open_corpus.py` used by Unix-like systems. It accepts Python through the Windows `py -3` launcher, `python3`, or `python`.

If Python is missing:

```powershell
winget install Python.Python.3.13
```

### Windows — WSL

Inside Ubuntu/Debian WSL:

```sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-corpus.sh | sh
```

If Python is missing:

```sh
sudo apt-get update && sudo apt-get install -y python3 curl
```

### Linux

For Linux distributions with Python 3 already installed:

```sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-corpus.sh | sh
```

or:

```sh
wget -qO- https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-corpus.sh | sh
```

On Alpine, the launcher can install Python using `apk`. On Termux it can use `pkg`. Other Linux distributions should install Python 3 with their own package manager first.

### ChromeOS — Linux development environment (Crostini)

Inside the Linux terminal:

```sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-corpus.sh | sh
```

If needed:

```sh
sudo apt-get update && sudo apt-get install -y python3 curl
```

### Raspberry Pi OS

```sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-corpus.sh | sh
```

### FreeBSD / other POSIX-like systems

When Python 3 plus either `curl` or `wget` are already installed:

```sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-corpus.sh | sh
```

## Direct runtime input

Unix-like systems:

```sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-corpus.sh | sh -s -- "Blue Pleiadian Stars"
```

iSH may substitute `wget -qO-` for `curl -fsSL`.

Windows PowerShell after downloading the launcher:

```powershell
& $p "Blue Pleiadian Stars"
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
HSI-NET-SINGULARITY/1.0
  ↓ finite projection
HSI-SEARCH/1.0
  ↓
network_audio union
  ↓
Openverse + Wikimedia Commons
  ↓
local CC0 / Public Domain Mark + WAV admission gate
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
category = music OR sound_effect
selected playable variant = WAV
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
├── search.hsicert
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

The renderer deliberately decodes only uncompressed WAV so that iSH/macOS/Windows/Linux can use the Python standard library without ffmpeg. A record may qualify through either its primary Openverse file or a WAV listed in Openverse `alt_files`; HSI records which variant was selected.

Quality depends on the retrieved recordings. This is a retrieval-and-remix renderer, not yet a full note-by-note multisample orchestra or concatenative singing engine.

Later versions can add:

- curated multisample banks;
- instrument/phoneme indexing;
- phase-vocoder time stretching;
- PSOLA-style vocal rendering;
- convolution impulse responses;
- license-verified persistent corpus snapshots.

None of those require generative AI.


## HSI SEARCH integration

As of Open-Corpus renderer 1.1, discovery is no longer implemented inside the music renderer.

```text
hsi_open_corpus.py
      ↓
HSI-SEARCH/1.0
      ↓
source adapter
      ↓
search.hsicert
      ↓
corpus admission / DSP
```

A failed or exhausted search remains epistemically distinct from a claim of nonexistence:

```text
SOURCE_UNAVAILABLE ≠ NO SUCH AUDIO EXISTS
EXHAUSTED_BUDGET   ≠ SEARCH SPACE EXHAUSTED
UNRESOLVED         ≠ FALSE
```

The exact search certificate is embedded in `corpus.lock.json`, so a later locked rerender preserves the original discovery provenance and status.


## HSI NET integration

Open-Corpus now treats public-network discovery as:

```text
Ω_Net (idealized information totality)
    ↓
HSI-NET-SINGULARITY/1.0
    ↓ finite projection
HSI-SEARCH/1.0
    ↓
openverse_audio adapter
    ↓
local rights/category/format gate
    ↓
DSP renderer
```

This does **not** claim to search the whole Internet. The `net_projection` certificate explicitly records that adapter scope is not Internet totality.

The current network projection is conservative and multi-adapter:

```text
Openverse preference: freesound
fallback adapter: Wikimedia Commons
licenses: CC0 / PDM only
categories: music / sound_effect only
spoken-word pronunciation: rejected
playable format: WAV primary or WAV alt_file
```
