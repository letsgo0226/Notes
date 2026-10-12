# HSI Notes → Music / UTM / Trader_42 / Omega: review-only integration

**Status:** LOCAL VALIDATION; production rollout remains separate. The opt-in stage 3 runner executes bounded local audio and formal checks. It has no remote deployment, external model, or broker interface.

## Inventory scope

The 'hsi_notes_review.lock.json' file records all **22 files** in the reviewed
2026-10-11 snapshot: four numbered documents, eight files under
'HSI_Prime_Analytic_2KB_Release/', and four files under
'HSI_Sub2K_Program_Synthesizer/'.  The latter adds bounded program synthesis,
exact reconstruction tests, documentation, and a finite certificate.

The read-only audit compares file byte lengths and Git blob IDs, rejects missing, unexpected or changed files and symlinks, and emits SHA-256 content fingerprints. It does not execute any one-line program, nor does any matching fingerprint establish mathematical truth or service health.

Run from a checkout of the review branch:

~~~sh
python3 -m unittest discover -s tests -v
python3 hsi_notes_review.py --json-out /tmp/hsi-notes-review.json
# Optional, separately execute finite reference replay in temp directories:
python3 Notes/HSI_Prime_Analytic_2KB_Release/verify_prime_analytic.py
python3 Notes/HSI_Sub2K_Program_Synthesizer/verify_sub2k_synth.py
~~~

A change in 'Notes/' requires human-reviewed changes to the lock; do not automatically accept drift. The lock is a local snapshot check, not code signing or a formal proof.

## Domain review requirements

| Target | Existing component | Additional evidence required |
|---|---|---|
| Music: Corpus | 'hsi-corpus.sh' installs a pinned four-file bundle for open audio retrieval + deterministic DSP, not generative AI. | Source pin review, CC0/PDM WAV discovery, independent license inspection, real WAV output verification. The launcher does **not** read all files under Notes/. |
| Music: Native | 'hsi-native.sh' loads deterministic local synthesizer. | Explicit reviewed mapping from selected documents to musical keywords/parameters; audio and score validation. No pretrained model is implied by number encoding. |
| Music: AI Bridge | Railway Bun function 'hsi-music-render-bridge' uses an external AI lyrics and song service. | Separate authorization for API calls and costs, authenticated /render integration test, successful playable output. Online and /health are insufficient. |
| UTM | 'letsgo0226/UTM.sh' HSI branch and Railway gates. | Finite machine replay and explicit invariants; no universal halting claims. |
| Trader_42 | 'letsgo0226/Trader_42.sh' HSI branch, readonly/paper gates. | Preserve readonly/paper/dry-run; independently review staged changes and authorization; no live trading. |
| Omega | 'letsgo0226/COSMIC_LOVE_IS_THE_SOLUTIONS_FOR_EVERYTHING_HS_ZERO.sh' HSI branch. | Human oversight and revisability evidence; logical certificates are not proofs of ethical truth. |

## Why the Corpus launcher is not a three-system updater

The command 'curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-corpus.sh | sh' installs the local Corpus renderer using a pinned commit of four root-level components. It does not copy the 12 'Notes/' files, update the Native renderer, invoke the paid AI music bridge, or redeploy Railway.

The existing 'hsi_deploy.py --target all --plan' resolves the HSI core, UTM, Trader_42, and Omega repositories and emits local plans/certificates. Its TARGETS file selection does not include all Notes documents. This review does not modify deployment targets.

## Separate phased rollout after review

1. Approve source identity with the read-only inventory and finite tests; review content and provenance separately.
2. Design and review domain adapters defining **exactly how** math texts become optional music themes, formal UTM inputs, paper-only trading review evidence, or Omega governance records. No automatic semantic inference is certified.
3. Independently validate UTM, Trader_42, and Omega source gates. Never automatically apply existing Trader_42 staged changes.
4. After inspecting local output, canary-deploy each adapter in the authorized environment, preserving rollback and evidence of real endpoint behavior.
5. Review the concrete production/paid API scope before rollout. Live orders are outside this integration.

Passing 'SOURCE_INVENTORY_VERIFIED' proves only presence and byte identity of the selected 22 files. All six domain gates remain 'NOT_TESTED_NOT_DEPLOYED'; it makes no claims about audio output, license rights, production correctness, universal problem solving, or ethical axioms.

## Review-only semantic adapter (stage 2)

The new `hsi_notes_domains.py` is a **deterministic planning tool**, not a deployer. It refuses to create plans if the 22-file inventory differs from the pinned lock. All 22 files contribute to an exact manifest fingerprint. Only `Notes/1` through `Notes/4` are treated as **concept source documents**, using exact bilingual heading markers. The eighteen other files are **reference/audit materials**, not musical training data.

Declared human-curated, contestable analogies:

| Concept source | Candidate music concepts |
|---|---|
| `Notes/1` prime formulas | prime, pulse, counterpoint |
| `Notes/2` analytic continuation | continuation, transition, legato |
| `Notes/3` formal correspondence | correspondence, call and response |
| `Notes/4` bitwise metatheory | binary, rhythm |

The output is a JSON **candidate** with six separate gates: `music_corpus`, `music_native`, `music_ai_bridge`, `utm`, `trader_42`, and `omega`. Every gate is intentionally `NOT_EXECUTED_NOT_DEPLOYED`.

- Music Corpus receives only proposed search keywords. No network request or public-domain license confirmation takes place.
- Music Native receives only a suggested local keyword string, not an audio render.
- AI Music Bridge remains disabled; no external calls, charges, lyrics or song requests.
- UTM receives a **32-bit manifest-hash prefix** as an illustrative bounded word, **not** an encoding of full document semantics or a halting proof.
- Trader_42 receives only a source-provenance record, with paper-only / zero orders / no broker calls.
- Omega receives only a revisability/human-override review checklist, **not** a proof of ethical correctness.

Generate the proposed inputs without taking any deployment action:

~~~sh
python3 hsi_notes_domains.py --out /tmp/hsi-notes-domains.json
python3 -m unittest discover -s tests -v
~~~

Any mapping from prime numbers, formal correspondence, or mathematical continuation to musical choices remains an **editorial design decision**. This stage changes no launcher, Railway project, paid provider, production branch, or trading mode.

## Offline execution and independent verification (stage 3)

`hsi_notes_validate.py` consumes the current locked 22-file plan, verifies the pinned local renderer and common invariant gate, and produces a new directory of real output and evidence:

~~~sh
python3 hsi_notes_validate.py --out "$HOME/Music/HSI-Notes/validation-01"
~~~

Use a new output directory each time; existing directories are preserved. Python 3.9+ and POSIX `sh`/Bash are required for the isolated finite release audit. No package installation is needed.

| Output | Actual validation and remaining scope |
|---|---|
| Native `song.wav` | Rendered twice; WAV, score and lyrics bytes match on the same runtime. Independently check PCM format, frame completeness, duration, RMS, peak, clip/silence ratios, full E257 reconstruction and SHA-256. This does not assess artistic quality or intelligible human singing. |
| 32 TM enumeration records | The 32-bit manifest-prefix word executes in the plaintext reference and 2KB core with per-candidate budget 8. Compare complete traces and checkpoints; independently recompute emitted transitions. `UNRESOLVED` is not proof of nonhalting. |
| Three common invariant gates | Use an exact 5008-byte snapshot fetched from all three pinned repositories. Accept a valid finite request for each role and reject a forbidden halting-decider claim. Trader uses HOLD/FLAT with zero broker calls and orders. These tests do not execute the full three applications. |
| Prime/analytic finite release | Run the existing seven-case audit in an isolated copy because that verifier rewrites its own certificate. Original locked sources stay unchanged. Finite replay and interpolation tests remain distinct from universal equivalence or unique analytic continuation. |
| Corpus and AI Bridge | Remain unexecuted. Corpus discovery, source license review and rendered audio are still needed; AI Bridge requires a successful real provider request within the authorized cost scope. |

All 22 files contribute to the exact manifest fingerprint appended to the Native prompt. Four documents also provide the previously declared creative keywords; the other eighteen remain reference/audit sources. Fingerprint conditioning is a deterministic input binding, not extraction of the full philosophical meaning of each document.

The runtime lock records Native source commit and SHA-256, plus all three upstream commits whose `hsi_common/core.py` files match the stored snapshot. It is a versioned integrity check, not a signed attestation. The runner clears inherited HSI environment variables, sets finite subprocess timeouts, rejects source drift before execution, checks drift again after execution, and writes no output into the locked Notes tree.

CI runs the real offline workflow at 8 kHz and uploads WAV and validation artifacts. The default local preview uses 24 kHz, 120 BPM and four bars. Floating point synthesis is only checked for repeatability on the same runtime; cross-platform byte equality is not asserted.

The resulting status is `LOCAL_VALIDATION_PASSED_NOT_DEPLOYED`. The original `main/hsi-corpus.sh` command continues to launch the existing Corpus bundle; it does not invoke this runner or import the locked documents until the reviewed integration is rolled out.
