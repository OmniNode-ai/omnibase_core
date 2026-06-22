# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Canonical recorded-from-real golden-chain replay harness (OMN-13499).

This package is the ONE canonical home for the recorded-from-real golden-chain
harness used across every OmniNode repo that has a golden chain (omnimarket,
omniclaude, omnibase_core itself). It consolidates three previously-divergent
per-repo replay implementations into a single core-resident surface:

  * omnimarket ``RecordedReplayInferenceAdapter`` (OMN-13498 B1),
  * omnimarket ``RecordedJudgeReplayAdapter`` (OMN-13470),
  * core ``harness_inference_curl`` / ``harness_inference_fixture`` (OMN-13420).

Architectural principle — REPLAY IS EVIDENCE, NOT AUTHORITY
-----------------------------------------------------------
A golden chain RECORDS a real chain once, freezes ONLY the model's response
bytes as a provenance-stamped fixture, and REPLAYS deterministically. On replay,
EVERYTHING except the recorded response bytes runs for real: routing-contract
resolution, model/provider selection, endpoint resolution, request construction,
and dispatch. The replay transport replaces ONLY the final model response bytes
for the CONCRETE route + request the live path constructs.

The transport seam is the HTTP boundary (``httpx.Client``-shaped). The real
delegation inference handler constructs the OpenAI-compatible payload LIVE and
posts it. The replay transport intercepts that POST and returns recorded bytes
ONLY when the live-constructed request hash matches the recorded
``request_hash`` for the recorded endpoint. A WRONG route or drifted request
produces a different hash and the replay FAILS (``ROUTE_NOT_RESOLVED`` /
``REQUEST_HASH_MISMATCH``) instead of "succeeding anyway".

Record-mode authority (operator-gated): ``OMN_RECORD_GOLDEN=1`` + a real
endpoint is the ONLY way to mint/refresh a fixture, and PR CI MUST FAIL if it
attempts recording (see ``record_guard``). Replay is the default.

Epic: OMN-13498 (golden-chain de-fake) · Foundation: OMN-13499 (Phase 0).
"""

from __future__ import annotations

from omnibase_core.models.runtime.golden_chain.model_golden_chain_fixture import (
    ModelGoldenChainFixture,
    ModelGoldenChainProvenance,
)
from omnibase_core.runtime.golden_chain.failure_classes import (
    EnumGoldenChainFailureClass,
    GoldenChainReplayError,
)
from omnibase_core.runtime.golden_chain.record_guard import (
    record_mode_enabled,
    require_record_mode_disabled,
)
from omnibase_core.runtime.golden_chain.recorded_replay_transport import (
    DELEGATION_TIER_NAMES,
    RecordedReplayInferenceTransport,
    canonical_prompt_hash,
    canonical_request_hash,
    fixture_hash,
    load_fixture,
)
from omnibase_core.runtime.golden_chain.recorder import (
    FIXTURE_VERSION,
    build_provenance,
    record_fixture,
)

__all__ = [
    "DELEGATION_TIER_NAMES",
    "FIXTURE_VERSION",
    "EnumGoldenChainFailureClass",
    "GoldenChainReplayError",
    "ModelGoldenChainFixture",
    "ModelGoldenChainProvenance",
    "RecordedReplayInferenceTransport",
    "build_provenance",
    "canonical_prompt_hash",
    "canonical_request_hash",
    "fixture_hash",
    "load_fixture",
    "record_fixture",
    "record_mode_enabled",
    "require_record_mode_disabled",
]
