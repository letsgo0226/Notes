# HSI UPDATE / 1.0

`HSI-UPDATE/1.0` makes system evolution itself a finite HSI operation.

It consumes an existing HSI Open-Corpus artifact directory:

```text
manifest.json
song.hsicert
corpus.lock.json
events.json
search.hsicert
```

and computes:

```text
OBSERVE
  ↓
DIAGNOSE
  ↓
PROPOSE
  ↓
VERIFYABLE UPDATE PLAN
  ↓
HUMAN APPROVAL
  ↓
DEPLOY / HOLD
```

It is deterministic rule-based analysis, not an AI model.

## Current diagnoses

The first version recognizes, among others:

```text
TECHNICAL_NOT_CLOSED
RIGHTS_REVIEW_OPEN
SINGLE_SOURCE_COLLAPSE
SOURCE_DIVERSITY_LOW
SOURCE_DOMINANCE_HIGH
FINITE_PREFIX_SAMPLING_USED
SPEECH_GATE_OBSERVED
```

## Current update candidates

### MULTI_SOURCE_COMPOSITION_V1

Triggered when a technically closed work is dominated by one retrieved source.

Its contract is:

```text
if usable_sources >= 2:
    unique_event_sources >= 2

if usable_sources >= 3:
    unique_event_sources >= 3

if unique_event_sources >= 2:
    max_event_source_share <= 0.60
```

while preserving:

```text
CC0/PDM only
WAV only
music/sound_effect only
spoken-word pronunciation rejection
provenance
deterministic replay
E257
no AI/ML
```

If the finite network projection really finds only one usable source, HSI must not fabricate diversity. It may report a degraded single-source state, or use an explicitly enabled deterministic Native connective layer.

### OPTIONAL_NATIVE_CONNECTIVE_LAYER

This is a separate optional fallback proposal. Retrieved material and Native-generated material must remain distinguishable in provenance.

### RIGHTS_ATTESTATION_WORKFLOW

`rights_closed` remains independent from `technical_closed`. Search/index metadata alone never closes publication rights.

## Mutation boundary

The update solver currently enforces:

```text
automatic_source_code_rewrite = false
automatic_git_push = false
human_approval_required_before_repository_mutation = true
regression_tests_required_before_commit = true
```

This means HSI may solve **what should change**, but it does not silently mutate its repository.

## macOS / Linux / Termux

```sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-update.sh | sh -s -- \
  ~/Music/HSI-Corpus/<artifact-directory>
```

## iSH

```sh
wget -qO- https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-update.sh | sh -s -- \
  ~/Music/HSI-Corpus/<artifact-directory>
```

## Windows PowerShell

```powershell
$p = Join-Path $env:TEMP "hsi-update.ps1"
Invoke-WebRequest -UseBasicParsing "https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-update.ps1" -OutFile $p
& $p "C:\path\to\HSI-Corpus\artifact"
```

## Unified deployed invocation

After `HSI-DEPLOY/1.0` installs the self target:

```sh
python3 ~/.hsi/hsi.py update ~/Music/HSI-Corpus/<artifact-directory>
```

The resulting artifact directory receives:

```text
update.hsicert
```

which records the observation, findings, candidate updates, acceptance criteria, and E257-derived plan identity.
