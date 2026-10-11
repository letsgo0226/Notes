# Notes local validation result — 2026-10-11

The 12-file `Notes/` inventory at main commit `5084ffadcce34d6460d313eb7b6a0c4451d9a5e6` was used by the stage 3 offline runner. The local result was **`LOCAL_VALIDATION_PASSED_NOT_DEPLOYED`**.

| Check | Observed result |
|---|---|
| Unit tests | 35 passed, including source drift, execution boundaries, truncated WAV, silence and clipping rejection. |
| Native synthesis | 12 seconds, 24 kHz, mono, 16-bit PCM, 288000 frames. Two renders had identical WAV, score and lyrics bytes on the same runtime. |
| Independent measurements | RMS 0.1077028638; peak 0.4896850586; clip ratio 0; silence ratio 0.0073020833. Full E257 reconstruction matched the WAV bytes. |
| Bounded TM replay | 32 enumeration records; 99 independently recomputed transitions; 7 HALTED and 25 UNRESOLVED; no budget skips. Reference and 2KB core traces/checkpoints matched. |
| Common invariant snapshots | Valid UTM, Trader HOLD/FLAT, and Omega HOLD requests passed. Each role rejected a forbidden halting-decider claim. Zero broker calls and zero orders. |
| Finite prime/analytic release | Seven replay cases passed, with exact finite interpolation and a nonunique interpolant witness. Run in a copy, preserving all original Notes files. |

Manifest SHA-256: `817dd6a4c19ac9c1c844396188f1af27035eb4de624d1da0d2287d80574c2dd7`.

24 kHz preview WAV SHA-256: `4bf4765af9de76047c2716ad5cda7e1118a5c2fcfd4f8828efb4e2554de54267`.

The default preview is technical local synthesis. Musical quality, intelligible singing, and cross-platform byte equality were not evaluated. `UNRESOLVED` means no halt was witnessed within that candidate's finite budget.

## Deployment state checked separately

Railway's music bridge and the UTM/Trader/Omega gates had successful active deployments and were Online when queried. Their deployed configurations still point to the existing provider function or three-system branches; this Notes PR has not been deployed to them. Trader's environment still has eight staged changes, which were not applied.

The Corpus launcher on `main` still pins `7ab944d924efa03cc15bb4722d9db3e5d25980b5` and downloads four root-level files. Corpus source search/license/audio acceptance and AI Bridge song generation were not executed by the offline runner.

## Reproduce

From the PR review branch, use a new output directory:

~~~sh
python3 -m unittest discover -s tests -v
python3 hsi_notes_validate.py --out "$HOME/Music/HSI-Notes/validation-01"
~~~

`validation-certificate.json` holds all six distinct domain results; `native/song.wav` is playable output. CI uses 8 kHz for a shorter render; it is not expected to match the 24 kHz WAV digest above.
