# HSI SEARCH / 1.0

`HSI-SEARCH/1.0` is a finite evidence-expansion operator.

It does **not** mean "the internet says this is true" and it does not treat failure to retrieve evidence as evidence of nonexistence.

Core rule:

```text
SEARCH expands evidence.
SEARCH does not totalize reality.
```

Formally:

```text
E_t --SEARCH--> E_(t+1)
E_t ⊆ E_(t+1)
```

## States

A search run returns one of:

```text
FOUND
UNRESOLVED
SOURCE_UNAVAILABLE
EXHAUSTED_BUDGET
```

Individual records may also be:

```text
ADMITTED
REJECTED
INDEX_ASSERTED
USER_ATTESTED
```

The important semantic distinction is:

```text
no retrieval ≠ proof of nonexistence
timeout      ≠ false
budget end   ≠ exhaustive knowledge
```

## Search identity

Every request is encoded as:

```text
search_uid = E257(
  protocol
  + query
  + source adapter
  + admission policy
  + finite budget
)
```

The completed certificate receives a second E257 identifier over the actual returned run.

## Current source adapter

Version 1 ships with:

```text
openverse_audio
```

It searches the Openverse audio API. The operator itself supports a local admission policy, so the calling system may say, for example:

```json
{
  "license_allow": ["cc0", "pdm"],
  "extension_allow": ["wav"]
}
```

The search operator performs the final admission decision locally.

## Finite budget

The request specifies:

```text
max_results
max_calls
page_size
timeout_seconds
retries
```

When the call budget is reached, the operator does not pretend the search space was exhausted. It returns `EXHAUSTED_BUDGET` unless admissible evidence has already been found.

## Pleiadian Blue

The search certificate carries:

```text
semantic_non_coercion = true
search_expands_evidence_only = true
unresolved_is_valid = true
forced_totalization = false
```

This is the operational form of semantic humility.

## Public launcher

iSH:

```sh
wget -qO- https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-search.sh | sh
```

macOS:

```sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-search.sh | sh
```

Example for the current Openverse adapter:

```sh
curl -fsSL https://raw.githubusercontent.com/letsgo0226/Notes/main/hsi-search.sh | sh -s -- \
  --license cc0,pdm --extension wav "Blue Pleiadian Stars"
```

## Integration

The HSI Open-Corpus renderer no longer implements its own Openverse discovery logic. It invokes `HSI-SEARCH/1.0` and records the result as:

```text
search.hsicert
```

The resulting `corpus.lock.json` embeds that search certificate so a locked offline rerender preserves the provenance and epistemic state of the original discovery event.

Future adapters can use the same protocol for other explicitly permitted public corpora without changing the semantics of the caller.
