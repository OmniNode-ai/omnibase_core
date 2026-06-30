# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Core-resident, infra-free in-process local runtime harness (OMN-13420).

Fast inner loop for node authors: register a node's handlers, publish a typed
command on the core in-memory bus, pump emitted events through the registered
handlers to the terminal event, and materialize a SQLite projection row — all
in-process, with NO ``omnibase_infra``, NO Kafka, NO Postgres, and NO LAN.

Uses ONLY the spi ``ProtocolMessageHandler.handle(envelope) -> ModelHandlerOutput``
contract, core envelope models, the core in-memory bus, and the core-resident
runtime protocols.

Scope: proves handler logic + the command -> terminal -> projection chain. Does
NOT exercise Kafka semantics or the image build — the infra-backed broker proof
remains the pre-merge gate. This is the inner loop only.

Epic: OMN-13442 (local-first runtime re-convergence).
"""

from omnibase_core.runtime.harness.harness_builder import build_workflow
from omnibase_core.runtime.harness.harness_dispatch import InProcessHarness
from omnibase_core.runtime.harness.harness_effect import HarnessEffectHandler
from omnibase_core.runtime.harness.harness_inference_curl import (
    CurlSubprocessInferenceAdapter,
)
from omnibase_core.runtime.harness.harness_inference_fixture import (
    RecordedFixtureInferenceAdapter,
)
from omnibase_core.runtime.harness.harness_orchestrator import (
    HarnessOrchestratorHandler,
)
from omnibase_core.runtime.harness.harness_projection_store_sqlite import (
    SqliteProjectionStore,
)
from omnibase_core.runtime.harness.harness_reducer import HarnessProjectionReducer
from omnibase_core.runtime.harness.harness_topics import (
    DELEGATION_COMMAND_TOPIC,
    DELEGATION_COMPLETED_TOPIC,
    DELEGATION_INFER_TOPIC,
    SEA_COMMAND_TOPIC,
    SEA_COMPLETED_TOPIC,
    SEA_INFER_TOPIC,
)

__all__ = [
    "DELEGATION_COMMAND_TOPIC",
    "DELEGATION_COMPLETED_TOPIC",
    "DELEGATION_INFER_TOPIC",
    "SEA_COMMAND_TOPIC",
    "SEA_COMPLETED_TOPIC",
    "SEA_INFER_TOPIC",
    "CurlSubprocessInferenceAdapter",
    "HarnessEffectHandler",
    "HarnessOrchestratorHandler",
    "HarnessProjectionReducer",
    "InProcessHarness",
    "RecordedFixtureInferenceAdapter",
    "SqliteProjectionStore",
    "build_workflow",
]
