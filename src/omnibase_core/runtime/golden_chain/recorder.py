# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Provenance-stamped fixture recorder for the golden-chain harness (OMN-13499).

The recorder is the ONLY way to mint/refresh a fixture, and it is operator-gated:
it calls ``require_record_mode_disabled`` first, which fails closed in PR CI
(``OMN_RECORD_GOLDEN=1`` is honored only locally or in the gated nightly job).

The recorder does NOT itself resolve routing or post — that is the caller's LIVE
path (so record mode exercises routing-contract resolution, model/provider
selection, endpoint resolution, request construction, and dispatch FOR REAL). The
caller hands the recorder the concrete route it resolved, the request payload it
constructed, the routing-contract/overlay bytes it loaded, and the real provider
response it captured; the recorder computes the provenance hashes and writes the
fixture envelope.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from omnibase_core.enums.enum_golden_chain_failure_class import (
    EnumGoldenChainFailureClass,
)
from omnibase_core.errors.error_golden_chain_replay import GoldenChainReplayError
from omnibase_core.models.runtime.golden_chain.model_golden_chain_fixture import (
    ModelGoldenChainFixture,
    ModelGoldenChainProvenance,
)
from omnibase_core.runtime.golden_chain.record_guard import (
    require_record_mode_disabled,
)
from omnibase_core.runtime.golden_chain.recorded_replay_transport import (
    DELEGATION_TIER_NAMES,
    canonical_prompt_hash,
    canonical_request_hash,
)

FIXTURE_VERSION = "golden_chain_fixture.v1"
_OVERLAY_SENTINEL_NONE = "none"


def _hash_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def hash_contract_file(path: str | Path | None, *, required: bool = False) -> str:
    """Hash a routing-contract/overlay file, or the sentinel 'none' when absent.

    When ``required=True`` a missing path/file fails closed with a named replay
    error instead of degrading to the sentinel — a required routing contract that
    is absent must NOT yield a fixture that silently claims incomplete provenance.
    """
    if path is None:
        if required:
            raise GoldenChainReplayError(
                EnumGoldenChainFailureClass.ROUTE_NOT_RESOLVED,
                "routing_contract_path is required but was None; refusing to "
                "record a fixture with routing_contract_hash='none'.",
            )
        return _OVERLAY_SENTINEL_NONE
    file_path = Path(path)
    if not file_path.is_file():
        if required:
            raise GoldenChainReplayError(
                EnumGoldenChainFailureClass.ROUTE_NOT_RESOLVED,
                f"routing contract file not found: {file_path}; refusing to "
                "record a fixture with routing_contract_hash='none'.",
            )
        return _OVERLAY_SENTINEL_NONE
    return _hash_bytes(file_path.read_bytes())


def build_provenance(
    *,
    provider: str,
    model_id: str,
    endpoint_ref: str,
    endpoint: str,
    request_payload: dict[str, object],
    routing_contract_path: str | Path,
    routing_overlay_path: str | Path | None,
) -> ModelGoldenChainProvenance:
    """Compute the full provenance bundle from the LIVE-resolved route + request.

    Fails closed (ROUTE_NOT_RESOLVED) if a delegation tier name is handed in as the
    concrete model — a recorded fixture must pin a CONCRETE model, never a tier.
    """
    if model_id in DELEGATION_TIER_NAMES:
        raise GoldenChainReplayError(
            EnumGoldenChainFailureClass.ROUTE_NOT_RESOLVED,
            f"refusing to record a fixture pinned to delegation TIER name "
            f"{model_id!r}; the recorder requires a CONCRETE resolved model id.",
        )
    raw_messages = request_payload.get("messages")
    messages: list[dict[str, object]] = (
        [item for item in raw_messages if isinstance(item, dict)]
        if isinstance(raw_messages, list)
        else []
    )
    return ModelGoldenChainProvenance(
        provider=provider,
        model_id=model_id,
        endpoint_ref=endpoint_ref,
        endpoint=endpoint,
        request_hash=canonical_request_hash(request_payload),
        prompt_hash=canonical_prompt_hash(messages),
        routing_contract_hash=hash_contract_file(routing_contract_path, required=True),
        routing_overlay_hash=hash_contract_file(routing_overlay_path),
        recorded_at=datetime.now(UTC).isoformat(),
        fixture_version=FIXTURE_VERSION,
    )


def record_fixture(
    *,
    output_path: str | Path,
    provider: str,
    model_id: str,
    endpoint_ref: str,
    endpoint: str,
    request_payload: dict[str, object],
    raw_response: dict[str, object],
    routing_contract_path: str | Path,
    routing_overlay_path: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> ModelGoldenChainFixture:
    """Write a provenance-stamped golden-chain fixture (operator-gated).

    Raises in PR CI before doing any work (``require_record_mode_disabled``), so
    an accidental record attempt during a PR run fails the build.
    """
    require_record_mode_disabled(env)
    provenance = build_provenance(
        provider=provider,
        model_id=model_id,
        endpoint_ref=endpoint_ref,
        endpoint=endpoint,
        request_payload=request_payload,
        routing_contract_path=routing_contract_path,
        routing_overlay_path=routing_overlay_path,
    )
    fixture = ModelGoldenChainFixture(
        fixture_version=FIXTURE_VERSION,
        provenance=provenance,
        raw_response=raw_response,
    )
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(fixture.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return fixture


__all__ = [
    "FIXTURE_VERSION",
    "build_provenance",
    "hash_contract_file",
    "record_fixture",
]
