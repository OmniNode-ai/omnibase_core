# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Canonical recorded-from-real replay transport for golden chains (OMN-13499).

This is the ONE canonical replay surface. It replaces ONLY the model response
bytes at the HTTP boundary. Everything before the POST — routing-contract
resolution, model/provider selection, endpoint resolution, request construction,
dispatch — runs LIVE on replay. The transport returns the recorded bytes ONLY
when the live-constructed request matches the fixture's concrete route and
``request_hash``; otherwise it raises a NAMED failure class.

It is shaped like the slice of ``httpx.Client`` the real inference handlers use::

    with replay_transport as client:
        response = client.post(url, json=payload, headers=..., timeout=...)
    response.raise_for_status()
    data = response.json()

so a golden chain can drop it in for ``httpx.Client`` (the live request
construction still runs) and prove the integrated path with recorded bytes.

REPLAY IS EVIDENCE, NOT AUTHORITY
---------------------------------
The fixture does not own the routing decision. If the live path resolves the
WRONG model / endpoint / max_tokens, the recomputed request hash will not match
the recorded ``request_hash`` and the replay FAILS (REQUEST_HASH_MISMATCH), or
the posted URL will not match a recorded endpoint (ROUTE_NOT_RESOLVED). A broken
route can never "replay successfully".
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from omnibase_core.enums.enum_golden_chain_failure_class import (
    EnumGoldenChainFailureClass,
)
from omnibase_core.errors.error_golden_chain_replay import GoldenChainReplayError
from omnibase_core.models.runtime.golden_chain.model_golden_chain_fixture import (
    ModelGoldenChainFixture,
)
from omnibase_core.runtime.golden_chain.replay_response import ReplayResponse

# Delegation TIER names — a tier name reaching the inference layer as a model_key
# is the OMN-13470 bug class. The transport rejects them so a recorded replay can
# never green-light a cheap_cloud-class routing bug. (Preserves + extends the B1
# RecordedReplayInferenceAdapter behavior.)
DELEGATION_TIER_NAMES: frozenset[str] = frozenset(
    {"cheap_cloud", "cheap_frontier", "frontier_api", "local", "unknown"}
)

# Request-body keys that participate in the canonical request hash. The hash pins
# the recorded bytes to the CONCRETE route + request the live path constructs.
_HASHED_REQUEST_KEYS = ("model", "messages", "max_tokens", "temperature")


def _canonical_json(value: object) -> str:
    """Stable JSON encoding for hashing (sorted keys, no whitespace drift)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_request_hash(payload: Mapping[str, object]) -> str:
    """Canonical hash over the load-bearing request fields (model/messages/params).

    Only the fields that determine WHICH model produced WHICH bytes are hashed:
    ``model``, ``messages``, ``max_tokens``, ``temperature``. A wrong model, wrong
    token budget, or drifted messages changes the hash and fails the replay.
    """
    projected = {k: payload.get(k) for k in _HASHED_REQUEST_KEYS if k in payload}
    return _sha256(_canonical_json(projected))


def canonical_prompt_hash(messages: list[dict[str, object]]) -> str:
    """Canonical hash over the prompt messages only (provenance / drift triage)."""
    return _sha256(_canonical_json(messages))


def fixture_hash(fixture: ModelGoldenChainFixture) -> str:
    """Stable content hash of a fixture (provenance + raw_response) for drift reports."""
    return _sha256(
        _canonical_json(
            {
                "provenance": fixture.provenance.model_dump(mode="json"),
                "raw_response": fixture.raw_response,
            }
        )
    )


def load_fixture(path: str | Path) -> ModelGoldenChainFixture:
    """Load + validate a golden-chain fixture, raising ``INVALID_FIXTURE`` on any defect."""
    fixture_path = Path(path)
    if not fixture_path.is_file():
        raise GoldenChainReplayError(
            EnumGoldenChainFailureClass.INVALID_FIXTURE,
            f"fixture file not found: {fixture_path}",
        )
    try:
        raw = json.loads(fixture_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise GoldenChainReplayError(
            EnumGoldenChainFailureClass.INVALID_FIXTURE,
            f"fixture {fixture_path} is not valid JSON: {exc}",
        ) from exc
    try:
        fixture = ModelGoldenChainFixture.model_validate(raw)
    except Exception as exc:  # pydantic ValidationError -> INVALID_FIXTURE
        raise GoldenChainReplayError(
            EnumGoldenChainFailureClass.INVALID_FIXTURE,
            f"fixture {fixture_path} failed provenance validation: {exc}",
        ) from exc
    _validate_completion(fixture, fixture_path)
    return fixture


def _extract_completion_text(raw_response: Mapping[str, object]) -> str:
    choices = raw_response.get("choices") or []
    if not isinstance(choices, list) or not choices:
        return ""
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return ""
    message = first_choice.get("message") or {}
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    return content if isinstance(content, str) else ""


def _validate_completion(fixture: ModelGoldenChainFixture, path: Path) -> None:
    """Reject empty/echo recorded completions at load time (fail-closed honesty)."""
    completion = _extract_completion_text(fixture.raw_response).strip()
    if not completion:
        raise GoldenChainReplayError(
            EnumGoldenChainFailureClass.EMPTY_COMPLETION,
            f"fixture {path} recorded an empty completion — a golden chain cannot "
            "prove an empty model response.",
        )


class RecordedReplayInferenceTransport:
    """``httpx.Client``-shaped replay transport returning recorded model bytes.

    Construct with one or more loaded fixtures. On ``post(url, json=payload, ...)``
    it:

      1. rejects a delegation TIER name handed in as ``payload['model']``
         (ROUTE_NOT_RESOLVED — the OMN-13470 bug class),
      2. matches the posted ``url`` to a fixture recorded for that endpoint
         (ROUTE_NOT_RESOLVED if none),
      3. recomputes the canonical request hash from the LIVE payload and compares
         it to the fixture's recorded ``request_hash`` (REQUEST_HASH_MISMATCH on
         drift),
      4. guards against an echo completion (ECHO_COMPLETION),

    and only then returns the recorded ``raw_response`` bytes. Steps 1-3 are the
    proof that replay is evidence, not authority: a wrong route / drifted request
    fails closed instead of "succeeding anyway".

    Use ``enforce_request_hash=False`` ONLY for callers that cannot reconstruct
    the exact recorded request (e.g. a non-payload-deterministic prompt); endpoint
    + model matching still applies, but the hash check is relaxed. The default is
    strict (the routing-failure proof requires strict).
    """

    def __init__(
        self,
        fixtures: list[ModelGoldenChainFixture],
        *,
        enforce_request_hash: bool = True,
    ) -> None:
        if not fixtures:
            raise GoldenChainReplayError(
                EnumGoldenChainFailureClass.INVALID_FIXTURE,
                "RecordedReplayInferenceTransport requires at least one fixture.",
            )
        self._fixtures = list(fixtures)
        self._enforce_request_hash = enforce_request_hash
        # Recorded calls captured for assertions (model, url, request_hash).
        self.calls: list[dict[str, object]] = []

    # ----- httpx.Client-shaped surface -------------------------------------
    def __enter__(self) -> RecordedReplayInferenceTransport:
        return self

    def __exit__(self, *exc: object) -> Literal[False]:
        return False

    def post(
        self,
        url: str,
        *,
        json: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> ReplayResponse:
        """Return recorded bytes for the live-constructed request, or fail closed."""
        payload = json or {}
        model = str(payload.get("model", ""))

        if model in DELEGATION_TIER_NAMES:
            raise GoldenChainReplayError(
                EnumGoldenChainFailureClass.ROUTE_NOT_RESOLVED,
                f"a delegation TIER name {model!r} reached the inference layer as a "
                "model_key (the OMN-13470 bug class). The caller must resolve a "
                "CONCRETE model route from the routing authority before dispatch.",
            )

        endpoint_matches = [f for f in self._fixtures if f.provenance.endpoint == url]
        if not endpoint_matches:
            recorded = sorted({f.provenance.endpoint for f in self._fixtures})
            raise GoldenChainReplayError(
                EnumGoldenChainFailureClass.ROUTE_NOT_RESOLVED,
                f"live path posted to endpoint {url!r}, but no fixture was recorded "
                f"for it. Recorded endpoints: {recorded}. The route resolved a "
                "different endpoint than any recorded chain — replay cannot vouch "
                "for it.",
            )

        live_hash = canonical_request_hash(payload)
        self.calls.append({"model": model, "url": url, "request_hash": live_hash})

        if self._enforce_request_hash:
            hash_matches = [
                f for f in endpoint_matches if f.provenance.request_hash == live_hash
            ]
            if not hash_matches:
                recorded_hashes = sorted(
                    {f.provenance.request_hash for f in endpoint_matches}
                )
                raise GoldenChainReplayError(
                    EnumGoldenChainFailureClass.REQUEST_HASH_MISMATCH,
                    f"live request hash {live_hash} (model={model!r}) does not match "
                    f"any recorded request_hash for endpoint {url!r}: {recorded_hashes}. "
                    "The routing/selection/request-construction drifted from what was "
                    "recorded — the recorded bytes are NOT evidence for this request.",
                )
            fixture = hash_matches[0]
        else:
            # Relaxed-hash mode still enforces endpoint + concrete-model matching;
            # a missing model_id cannot select a trusted fixture and fails closed.
            if not model:
                raise GoldenChainReplayError(
                    EnumGoldenChainFailureClass.ROUTE_NOT_RESOLVED,
                    "live payload is missing 'model'; relaxed-hash mode still "
                    "requires a CONCRETE model_id to select a trusted fixture.",
                )
            model_matches = [
                f for f in endpoint_matches if f.provenance.model_id == model
            ]
            if not model_matches:
                recorded_models = sorted(
                    {f.provenance.model_id for f in endpoint_matches}
                )
                raise GoldenChainReplayError(
                    EnumGoldenChainFailureClass.REQUEST_HASH_MISMATCH,
                    f"live path resolved model {model!r}, but no fixture for "
                    f"endpoint {url!r} was recorded with that model. Recorded "
                    f"models: {recorded_models}. Re-record if the backend changed.",
                )
            fixture = model_matches[0]

        # Concrete-model cross-check: the recorded provenance model must match the
        # model the live path actually resolved (defense beyond the hash, and a
        # second guard on the strict-hash path).
        if model and model != fixture.provenance.model_id:
            raise GoldenChainReplayError(
                EnumGoldenChainFailureClass.REQUEST_HASH_MISMATCH,
                f"live path resolved model {model!r} but the fixture for endpoint "
                f"{url!r} was recorded against concrete model "
                f"{fixture.provenance.model_id!r}. Re-record if the backend changed.",
            )

        completion = _extract_completion_text(fixture.raw_response).strip()
        prompt_text = _canonical_json(payload.get("messages") or [])
        if completion and completion == prompt_text:
            raise GoldenChainReplayError(
                EnumGoldenChainFailureClass.ECHO_COMPLETION,
                "recorded completion echoes the request payload — that is the "
                "hand-written-fake tell, not recorded-from-real bytes.",
            )

        return ReplayResponse(status_code=200, json_body=dict(fixture.raw_response))


__all__ = [
    "DELEGATION_TIER_NAMES",
    "RecordedReplayInferenceTransport",
    "canonical_prompt_hash",
    "canonical_request_hash",
    "fixture_hash",
    "load_fixture",
]
