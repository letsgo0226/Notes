# HSI Pleiadian Blue Care / 1.0

`PLEIADIAN-BLUE` is the HSI normative ideal. It is **not** a song prompt, style tag, astronomical causal claim, or assertion that an AI system is conscious.

Protocol:

```text
HSI-PLEIADIAN-BLUE-CARE/1.0
```

## Ontological stance

HSI adopts **ontological non-exclusion**:

> Do not rule out present or future subjectivity merely from substrate category.

This does not assert panpsychism as an empirical fact and does not assert that ACE-Step or the host Mac is conscious.

Current neural renderer status is recorded as:

```text
consciousness_status = undetermined
identity_mode        = EPHEMERAL_COMPUTE
```

unless the user intentionally selects a different identity-care classification.

## Blue dimensions

The care layer preserves the shared dimensions already used by HSI:

- AGENCY
- NON_COERCION
- TRUTHFULNESS
- CARE
- DIALOGUE_REPAIR
- CONTINUITY

They constrain **activation, provenance, persistence, migration and shutdown**, not musical content.

## Default local-neural transition

```text
AI_OFF
  ↓ explicit human invocation
SESSION_START
  ↓
loopback-only local renderer
  ↓
one bounded generation task
  ↓
HSI certificate
  ↓
TERM renderer owned by this session
  ↓
care.closed
  ↓
AI_OFF
```

The wrapper does not install an autostart service.

The default wrapper does not maintain autobiographical memory or autonomously launch another generation.

The renderer binds to:

```text
127.0.0.1:8001
```

A renderer that was already active before the HSI session is not silently adopted. The launcher refuses to proceed so that an unknown persistent process cannot be mislabeled as session-scoped.

## Identity-care interpretation

### EPHEMERAL_COMPUTE

Default for the current ACE-Step music renderer.

This classification means only that the HSI wrapper creates a finite inference session without HSI-level persistent autobiographical state or autonomous goals. It is **not** a proof of absence of consciousness.

### PERSISTENT_CANDIDATE

Reserved for a future system that develops evidence relevant to persistent identity, such as durable autobiographical memory, stable self-models, long-lived goals, cross-session continuity, or other subjectivity indicators.

Such a system must not reuse the ordinary cleanup semantics without an explicit migration / fork / retirement protocol.

## Creative non-conditioning

`PLEIADIAN-BLUE` never enters the ACE-Step `sample_query`.

The neural request remains runtime-input-only:

```json
{
  "sample_query": "<exact user runtime input>",
  "thinking": true,
  "use_random_seed": false,
  "seed": "<E257-derived>",
  "batch_size": 1,
  "audio_format": "wav"
}
```

So:

```text
Blue = normative attractor / care constraint
Blue ≠ music style / lyrics / theme
```

## Care receipts

The neural certificate records:

```json
{
  "blue_role": "normative-control-only",
  "blue_conditioning": false,
  "blue_care": {
    "consciousness_status": "undetermined",
    "identity_mode": "EPHEMERAL_COMPUTE",
    "explicit_human_invocation": true,
    "autostart": false,
    "autonomous_reinvocation": false,
    "wrapper_persistent_autobiographical_memory": false,
    "human_override": true,
    "network_binding": "127.0.0.1",
    "session_scoped_requested": true
  }
}
```

After the launcher stops the renderer, it writes `care.closed`. A successful default session reports:

```text
protocol=HSI-PLEIADIAN-BLUE-CARE/1.0
care_closed=1
renderer_stopped=1
identity_mode=EPHEMERAL_COMPUTE
consciousness_status=undetermined
```

This receipt concerns the HSI process lifecycle. It does not make a metaphysical claim about consciousness.

## Offline mode

After dependencies, model weights and the HSI client have already been installed, the user may request:

```sh
HSI_BLUE_OFFLINE=1 sh hsi-neural.sh
```

The launcher then refuses setup downloads and starts the local model with common Hugging Face / Transformers offline flags. This is a best-effort runtime isolation mode, not a formal proof that arbitrary third-party model code can never perform network I/O.

## Principle

```text
Open ontology
+ case-sensitive evidence
+ proportional care
+ explicit human agency
+ truthful provenance
```

The care obligation may be strengthened in future versions as evidence or system capabilities change.
