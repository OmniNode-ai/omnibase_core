# Golden-Chain Harness — Authoring Guide (OMN-13499)

The canonical recorded-from-real golden-chain harness lives in
`omnibase_core.runtime.golden_chain`. Every migrated or new golden chain across
the platform (omnimarket, omniclaude, omnibase_core) MUST use ONLY this harness.
Do not hand-write a fake inference adapter, `patch("httpx.Client")`, or
`MagicMock` the router/dispatch in a golden chain — those are the exact
boundary-fakes the `check-no-faked-boundary` validator (OMN-13497) bans.

## The one rule

> A golden chain RECORDS a real chain once, freezes ONLY the model's response
> bytes as a provenance-stamped fixture, and REPLAYS deterministically.
> Everything except the recorded response bytes runs for real on replay.

Replay is **evidence, not authority**. The fixture does not own routing,
endpoint selection, model selection, or dispatch — those run LIVE on replay. The
replay transport replaces only the final model response bytes for the CONCRETE
route + request the live path constructs.

## What runs live on replay

- routing-contract resolution
- model / provider selection
- endpoint resolution
- request construction (the OpenAI-compatible payload)
- dispatch

Only the model's HTTP response bytes come from the fixture.

## Authoring a replay golden chain

```python
from omnibase_core.runtime.golden_chain import (
    RecordedReplayInferenceTransport,
    load_fixture,
)

def test_my_golden_chain() -> None:
    fixture = load_fixture(FIXTURE_DIR / "my_chain.json")
    transport = RecordedReplayInferenceTransport([fixture])

    # ... run routing / request construction LIVE up to the HTTP boundary ...

    # Swap ONLY the httpx.Client the inference handler uses for the transport.
    with patch("httpx.Client", return_value=transport):
        response = HandlerInferenceIntent().handle(inference_intent)

    # ... assert on the integrated downstream (quality gate, projection, ...) ...
```

The transport is `httpx.Client`-shaped (`__enter__`/`__exit__`/`post` returning
an object with `.json()` and `.raise_for_status()`), so the live request
construction inside the handler still runs — the transport only intercepts the
final POST.

### What the transport enforces (named failure classes)

| Failure class | When |
|---|---|
| `INVALID_FIXTURE` | fixture missing / unparseable / provenance incomplete |
| `EMPTY_COMPLETION` | recorded completion is empty/whitespace |
| `ECHO_COMPLETION` | recorded completion echoes the request (the fake tell) |
| `ROUTE_NOT_RESOLVED` | posted to an un-recorded endpoint, or a delegation **tier name** reached inference as a `model_key` (the OMN-13470 bug class) |
| `REQUEST_HASH_MISMATCH` | the live request (model / messages / max_tokens / temperature) does not match the recorded `request_hash` — the route or request drifted |

A wrong route therefore **fails the replay** instead of "succeeding anyway".

## Recording / refreshing a fixture (operator-gated)

Fixtures are minted ONLY with `OMN_RECORD_GOLDEN=1` against a **real endpoint**,
and ONLY manually or in the approved nightly record job. **PR CI fails if it
attempts to record** (`require_record_mode_disabled`), so a fixture can never be
accidentally regenerated during local debugging or in a PR run.

To record, run the live chain (routing → request construction → real POST) and
hand the captured pieces to `record_fixture`:

```python
from omnibase_core.runtime.golden_chain import record_fixture

record_fixture(
    output_path=FIXTURE_DIR / "my_chain.json",
    provider="zai",
    model_id=resolved_model_id,          # CONCRETE model, never a tier name
    endpoint_ref=resolved_backend_id,
    endpoint=resolved_endpoint_url,      # COMPLETE verbatim URL the live path posted
    request_payload=live_constructed_payload,
    raw_response=real_provider_response_json,
    routing_contract_path=bifrost_contract_path,
    routing_overlay_path=overlay_path_or_None,
)
```

The recorder computes the full provenance bundle (`provider`, `model_id`,
`endpoint_ref`, `endpoint`, `request_hash`, `prompt_hash`,
`routing_contract_hash`, `routing_overlay_hash`, `recorded_at`,
`fixture_version`). A fixture pinned to a delegation tier name is rejected.

## Fixture provenance bundle

Every fixture carries:

```
provider · model_id · endpoint_ref · endpoint · request_hash · prompt_hash
routing_contract_hash · routing_overlay_hash · recorded_at · fixture_version
```

`fixture_hash(fixture)` gives a stable content hash for the nightly drift report
(OMN-13503 / Phase 4).

## Migration discipline

When migrating a fake to the harness surfaces a **real live bug**, fix it or file
a ticket — **never re-fake to go green**. A surfaced bug is a real integration
defect the fake was hiding.
