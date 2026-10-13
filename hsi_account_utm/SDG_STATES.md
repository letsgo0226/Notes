# HSI SDG 16 — national/geographic state as a symbolic tape (review only)

**Status:** independent module staged in Draft PR #40. It does NOT change the original COSMIC LOVE 1674-byte self-encoded core and does not claim to be a world simulator or ASI.

## Official public data and limits

- Primary source: [UNSD SDG API](https://unstats.un.org/SDGAPI/swagger/).
- Live reads: `GET /v1/sdg/GeoArea/List`, `GET /v1/sdg/Indicator/16.1.1/Series/List`, `GET /v1/sdg/Indicator/16.1.2/Series/List`, paginated `GET /v1/sdg/Series/Data`.
- [SDG Goal 16](https://sdgs.un.org/goals/goal16): **16.1.1** intentional homicide deaths per 100,000 by age/sex; **16.1.2** conflict-related deaths per 100,000 by sex/age/cause. Neither is an instantaneous account of current conflicts.
- The API is queried **at run time**, but the observation periods are the *published year* on each record. No value is labeled "live" merely because it was retrieved now.
- Official geographies include countries **and potentially regional groupings**. Only geographic rows with an explicit official `type=Country` label are tagged `country`; others remain `unclassified_area`. This is conservative, not a geopolitical judgment.
- If the UN API has no observation for an area/series, **unknown** is kept distinct from zero. If there are multiple conflicting observations at the same year/dimensions, all are retained without averaging or selecting a preferred source.

## Mathematical construction

A geographic/indicator state is a finite canonical JSON byte string:
`S = Encode(geo_area_code, observation_year, series, dimensions, value, provenance)`.

The *short geography identifier* is reversibly encoded by E257:

```text
E257(b_0 ... b_n): z_0=1, z_{i+1}=257*z_i+b_i+1
D257(E257(x))=x
```

A SHA-256 digest detects changes to the serialized state. Unlike E257, SHA-256 is not reversible. The complete state remains available as the JSON snapshot.

Any feedback is a **comparison of published observations with the same country, indicator, series and disaggregation**; it is *not* the original two-step Turing transition, and it does not automatically choose government policy.

## Proposed automation

- On PRs: **offline fixture tests only**, zero external writes.
- After reviewed merge to the default branch: GitHub Actions may run a **finite daily** read-only query around **03:37 UTC**; GitHub may delay or skip scheduled jobs.
- A successful run uploads a 7-day **downloadable JSON artifact**. It never commits or modifies a repository or deploys any external application.
- Missing data, unsupported API shapes, excessive pagination, network failure or an incomplete dataset cause visible failure; no fake values or fallback forecasts.
- **Not a continuous streaming service**, not a live war monitor, and not an automated peacekeeping or diplomatic system.

## Boundaries

No autonomous country ranking, political advocacy, military action, automatic policy prescription, country-specific manipulation, fund transfer, cross-repository write, cloud deployment, code execution from source data, secret access or live trading. All later actions would require separately reviewable, explicitly authorized connectors and defined human accountability.

## Reproduce

```sh
python3 -m unittest discover -s hsi_account_utm -p test_sdg_state.py -v
python3 hsi_account_utm/sdg_state.py --out /tmp/hsi-sdg16-public-state.json
```

The second command requires access to the official UNSD endpoint and may fail if the API is unavailable or its contract changes. The offline fixture tests alone do **not** demonstrate successful live data retrieval.

## Future expansion

Start with SDG 16 as a peace-related, verifiable prototype. Add other SDG indicators, and a vetted country-list mapping if needed, only after verifying each indicator's official series, units, definition, release cadence, missing-data behavior and comparability. A mathematical "country state" is a data representation; no finite indicator vector is the complete state of a sovereign country.
