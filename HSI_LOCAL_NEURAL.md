# HSI Local Neural Renderer — Archived

The ACE-Step neural-renderer path has been **removed from the active HSI entry points**.

Current status:

```text
ACE launcher        = DISABLED
ACE auto-install    = DISABLED
ACE model startup   = DISABLED
active music path   = hsi-corpus.sh
AI requirement      = none
```

The former implementation is preserved only as research history under:

```text
experimental/neural/
├── hsi-neural.archived.sh
├── hsi_local_neural.archived.py
└── HSI_LOCAL_NEURAL_ARCHIVED.md
```

The old public command is intentionally safe:

```sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-neural.sh | sh
```

It now prints an archival notice and exits without cloning ACE-Step, downloading model weights, installing a neural runtime, opening a local API server, or performing inference.

## Active non-AI renderer

iSH:

```sh
wget -qO- https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-corpus.sh | sh
```

macOS:

```sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-corpus.sh | sh
```

This uses the HSI Open-Corpus renderer: openly indexed audio material plus deterministic traditional DSP, with provenance and E257 closure.

Archiving the neural path is a deployment-policy decision. It is not a claim that AI systems are conscious or non-conscious.
