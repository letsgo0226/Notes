# Dolphin-Logos / 777ALAJE feedback

This module performs real local language-model inference in three separate passes:
source encounter → questions and interpretation → objections → revised questions.
Every third completed round revisits a source with a large residual. Other rounds
expand coverage across the bounded official-channel catalog.

The default is Ollama with Qwen3 4B. There is no hosted inference API, API key,
cloud model, paid-model fallback, trading operation or automatic weight update.
GitHub's official documentation records GitHub Models retirement on July 30, 2026.

## Source encounter

The channel identity is pinned to UCLoHjca5L0KJ3i14MvhcroA (777ALAJE).
The initial catalog was actually read and contained 238 video records.
The intake scan is bounded at 512 entries and marks possible truncation.

The source reader tries publicly available English or Chinese caption tracks.
If captions are unavailable, it reads the video's description, or just its title,
and records the exact modality. Captions burned into video frames are not extracted.
It does not claim to watch video frames or hear audio. Full transcripts, signed
caption links and source prompts are never published in the journal.

An optional authorized text directory can provide <video-id>.txt files. These are
marked USER_PROVIDED_TEXT, rather than attributed to a verified official caption
track. An optional local 16-bit PCM WAV provides duration, RMS and peak features;
these features do not amount to semantic music listening.

## Run on a Mac

Install and start [Ollama](https://ollama.com/download), then in this repository:

    ollama pull qwen3:4b
    python3 -m venv .venv-dolphin
    .venv-dolphin/bin/python -m pip install yt-dlp==2026.8.19
    .venv-dolphin/bin/python Notes/Dolphin_Logos_Riemann_Feedback/dolphin_logos.py --sync
    .venv-dolphin/bin/python Notes/Dolphin_Logos_Riemann_Feedback/dolphin_logos.py --run --rounds 3

Plan without network calls or writes:

    python3 Notes/Dolphin_Logos_Riemann_Feedback/dolphin_logos.py --plan

Replay independent evidence without the model or network:

    python3 Notes/Dolphin_Logos_Riemann_Feedback/verify_feedback.py books/dolphin-logos

Each invocation completes at most three rounds. Each round needs three inference
passes. There is a hard ceiling of 12 attempted requests per Taipei calendar day;
failed and interrupted attempts consume this budget too. The first successful
phases of an interrupted round are resumed without asking the model again.
Source changes during an incomplete round fail explicitly. Concurrent processes
cannot enter the same output directory.

The module uses a loopback Ollama server and records the actual local model digest.
The model is a separate download (about 2.5 GB); this program is not a sub-2KB model.
Inference quality remains subject to the selected model and human assessment.

## Hosted automation

The Dolphin-Logos workflow runs offline tests on relevant pull requests and pushes.
On a relevant push to main, it performs one bounded local-model round on a GitHub
runner. The daily schedule is 19:17 Asia/Taipei (11:17 UTC); scheduled runs honor
the repository variable DOLPHIN_LOGOS_ENABLED if it is explicitly set to false.
The first empty setting enables the requested daily program.
The runner installs a pinned Ollama release, downloads/caches Qwen weights, and
does not enable GitHub paid inference. Model access and source failures remain
failures, with saved attempt state and an uploaded diagnostic journal.
Hosting this workflow does not start software on the user's Mac.

## Memory and meaning

Completed rounds and recent questions are working history. They are not approved
long-term insights. A round enters approved prompt memory only after an explicit
human review command:

    python3 Notes/Dolphin_Logos_Riemann_Feedback/dolphin_logos.py --review ROUND_ID --decision approve --note "My reason"

Use decision reject to revoke a previous approval. Synthetic test rounds and
echo-rejected rounds cannot be approved. The model cannot write review decisions.

External factual claims remain UNVERIFIED; spiritual interpretations remain
creative interpretations; the dolphin cosmic traveler is a symbolic persona.
The schema checker and byte certificates cannot determine philosophical truth.
Even the critic is another pass of the same model, with correlated limitations.

The residual vector tracks missing primary content, trigram question overlap,
self-reported open objections and unverified fact checks. Its finite Dirichlet
sum is F_N(s)=sum(r_n/n^s), sampled at s=2, 2+i and 2+2i. It is diagnostic history,
not the Riemann zeta function, a proof of the Riemann hypothesis or a guarantee of
all possible evolution. The actual source choice and subsequent prompts consume
this history. E257 encodes the final structured output reversibly, using hex for
large integers; it is a provenance encoding, not information compression.

Outputs live in books/dolphin-logos: catalog.json, state.json, immutable rounds
and daily Markdown journals. The immutable Notes snapshot contains only source
code, configuration, this explanation and the finite verification certificate.

Primary interface references:

- [Ollama chat API](https://docs.ollama.com/api/chat)
- [Qwen3 model family](https://ollama.com/library/qwen3)
- [GitHub Models retirement](https://docs.github.com/en/github-models)
- [777ALAJE official channel](https://www.youtube.com/user/777ALAJE)
