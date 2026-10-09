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

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "build_workflow": (
        "omnibase_core.runtime.harness.harness_builder",
        "build_workflow",
    ),
    "InProcessHarness": (
        "omnibase_core.runtime.harness.harness_dispatch",
        "InProcessHarness",
    ),
    "HarnessEffectHandler": (
        "omnibase_core.runtime.harness.harness_effect",
        "HarnessEffectHandler",
    ),
    "CurlSubprocessInferenceAdapter": (
        "omnibase_core.runtime.harness.harness_inference_curl",
        "CurlSubprocessInferenceAdapter",
    ),
    "RecordedFixtureInferenceAdapter": (
        "omnibase_core.runtime.harness.harness_inference_fixture",
        "RecordedFixtureInferenceAdapter",
    ),
    "HarnessOrchestratorHandler": (
        "omnibase_core.runtime.harness.harness_orchestrator",
        "HarnessOrchestratorHandler",
    ),
    "SqliteProjectionStore": (
        "omnibase_core.runtime.harness.harness_projection_store_sqlite",
        "SqliteProjectionStore",
    ),
    "HarnessProjectionReducer": (
        "omnibase_core.runtime.harness.harness_reducer",
        "HarnessProjectionReducer",
    ),
    "DELEGATION_COMMAND_TOPIC": (
        "omnibase_core.runtime.harness.harness_topics",
        "DELEGATION_COMMAND_TOPIC",
    ),
    "DELEGATION_COMPLETED_TOPIC": (
        "omnibase_core.runtime.harness.harness_topics",
        "DELEGATION_COMPLETED_TOPIC",
    ),
    "DELEGATION_INFER_TOPIC": (
        "omnibase_core.runtime.harness.harness_topics",
        "DELEGATION_INFER_TOPIC",
    ),
    "SEA_COMMAND_TOPIC": (
        "omnibase_core.runtime.harness.harness_topics",
        "SEA_COMMAND_TOPIC",
    ),
    "SEA_COMPLETED_TOPIC": (
        "omnibase_core.runtime.harness.harness_topics",
        "SEA_COMPLETED_TOPIC",
    ),
    "SEA_INFER_TOPIC": (
        "omnibase_core.runtime.harness.harness_topics",
        "SEA_INFER_TOPIC",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
