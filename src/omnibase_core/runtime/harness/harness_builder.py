# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Workflow wiring for the core-resident local runtime harness (OMN-13420).

``build_workflow`` wires a complete orchestrator -> effect -> reducer chain for the
delegation or sea workflow against an ``InProcessHarness`` and returns it with the
command topic to publish on.
"""

from __future__ import annotations

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.protocols.runtime.protocol_harness_inference_adapter import (
    ProtocolHarnessInferenceAdapter,
)
from omnibase_core.protocols.runtime.protocol_harness_projection_store import (
    ProtocolHarnessProjectionStore,
)
from omnibase_core.runtime.harness.harness_dispatch import InProcessHarness
from omnibase_core.runtime.harness.harness_effect import HarnessEffectHandler
from omnibase_core.runtime.harness.harness_orchestrator import (
    HarnessOrchestratorHandler,
)
from omnibase_core.runtime.harness.harness_reducer import HarnessProjectionReducer
from omnibase_core.runtime.harness.harness_topics import (
    command_topic,
    completed_topic,
    infer_topic,
)

_SUPPORTED_WORKFLOWS = frozenset({"delegation", "sea"})


def build_workflow(
    *,
    workflow: str,
    adapter: ProtocolHarnessInferenceAdapter,
    store: ProtocolHarnessProjectionStore,
) -> tuple[InProcessHarness, str]:
    """Wire a complete harness for ``workflow`` and return (harness, command_topic).

    The returned harness has the orchestrator/effect/reducer registered against the
    correct topics and the completed topic declared terminal.
    """
    if workflow not in _SUPPORTED_WORKFLOWS:
        raise ModelOnexError(
            message=(f"unknown workflow {workflow!r}; expected 'delegation' or 'sea'"),
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    cmd_topic = command_topic(workflow)
    done_topic = completed_topic(workflow)
    request_topic = infer_topic(workflow)

    harness = InProcessHarness(terminal_topics=frozenset({done_topic}))
    harness.register(cmd_topic, HarnessOrchestratorHandler(workflow))
    harness.register(request_topic, HarnessEffectHandler(workflow, adapter))
    harness.register(done_topic, HarnessProjectionReducer(workflow, store))
    return harness, cmd_topic


__all__ = ["build_workflow"]
