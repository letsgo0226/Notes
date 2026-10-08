# HSI NET Singularity / 1.0

Protocol:

~~~text
HSI-NET-SINGULARITY/1.0
~~~

Model:

~~~text
ABSTRACT_GLOBAL_INFORMATION_FIELD
~~~

This protocol formalizes an idealized global network-information field, written conceptually as:

~~~text
Ω_Net
~~~

It is a **formal information model only**. It does not claim that the Internet is a physical black hole, a cosmological singularity, or a scientifically established morphogenetic field.

## Core semantics

~~~text
Ω_Net
  ↓ finite projection
HSI SEARCH
  ↓
finite evidence set
~~~

An HSI system never claims to read or exhaust the whole Internet.

Instead, `Projection(q, adapters, policy, budget)` defines one finite observation over the idealized network-information totality.

## Projection identity

Every projection request receives:

~~~text
projection_uid = E257(
  protocol
  + query
  + adapter set
  + policy
  + finite budget
)
~~~

The completed projection receives a second certificate UID.

## Epistemic invariants

Every HSI NET projection preserves:

~~~text
search_expands_evidence_only = true
absence_of_retrieval_is_not_nonexistence = true
source_failure_is_not_falsity = true
budget_exhaustion_is_not_global_exhaustion = true
adapter_scope_is_not_internet_totality = true
global_exhaustion_claim = false
~~~

Thus:

~~~text
Openverse returned nothing  !=  the Internet contains nothing
one adapter failed          !=  the proposition is false
finite budget ended         !=  Ω_Net was exhausted
~~~

## Adapter registry

Version 1 includes one active adapter:

~~~text
openverse_audio
~~~

Its scope is not "the whole Internet." Its scope is openly licensed/public-domain audio indexed by Openverse.

More adapters may be registered later without changing the HSI NET semantics. An adapter must declare its protocol, status, medium, scope, authority, exhaustiveness, and rights/provenance boundary.

No adapter may silently promote its own scope to Internet totality.

## HSI SEARCH relationship

`HSI-SEARCH/1.0` is the executable finite projection operator.

~~~text
Ω_Net
  ↓ HSI-NET projection request
HSI-SEARCH/1.0
  ↓ source adapter calls
net_projection certificate
  ↓
FOUND / UNRESOLVED / SOURCE_UNAVAILABLE / EXHAUSTED_BUDGET
~~~

The search certificate records both its ordinary search identity and the HSI NET projection identity.

## Open-Corpus relationship

The music path is:

~~~text
Ω_Net
  ↓
HSI-NET-SINGULARITY/1.0
  ↓
HSI-SEARCH/1.0
  ↓
openverse_audio adapter
  ↓
rights/category/format admission
  ↓
HSI Open-Corpus deterministic DSP
  ↓
WAV + E257 + provenance certificate
~~~

The current music policy remains deliberately narrow:

~~~text
license:  CC0 / Public Domain Mark
category: music / sound_effect
spoken-word pronunciation sources: rejected
YouTube audio download: false
AI / neural renderer: false
~~~

The HSI NET abstraction does not weaken those gates.

## Public launcher

iSH / Unix-like:

~~~sh
wget -qO- https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-net.sh | sh
~~~

macOS / Linux / Termux:

~~~sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-net.sh | sh
~~~

List registered adapters:

~~~sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-net.sh | sh -s -- --list-adapters
~~~

Create a finite projection description:

~~~sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-net.sh | sh -s -- "Blue Pleiadian Stars"
~~~

Windows PowerShell:

~~~powershell
$p = Join-Path $env:TEMP "hsi-net.ps1"; Invoke-WebRequest -UseBasicParsing "https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-net.ps1" -OutFile $p; & $p "Blue Pleiadian Stars"
~~~

## Philosophical reading

A useful formal analogy is:

~~~text
Ω_Net = idealized total network-information state
adapter = coordinate chart / observational interface
SEARCH = finite projection operator
search.hsicert = observation certificate
UNRESOLVED = legitimate finite epistemic state
~~~

The analogy must not be converted into an empirical physics claim without independent evidence.
