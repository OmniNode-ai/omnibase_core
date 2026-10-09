# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.enums.enum_model_health_state import EnumModelHealthState
    from omnibase_core.enums.enum_quality_gate_result import (
        EnumQualityGateResult,
    )
    from omnibase_core.enums.enum_redaction_policy import EnumRedactionPolicy
    from omnibase_core.models.delegation.model_a2a_task_request import (
        ModelA2ATaskRequest,
    )
    from omnibase_core.models.delegation.model_a2a_task_response import (
        ModelA2ATaskResponse,
    )
    from omnibase_core.models.delegation.model_agent_task_lifecycle_event import (
        ModelAgentTaskLifecycleEvent,
    )
    from omnibase_core.models.delegation.model_delegation_request import (
        ModelDelegationRequest,
    )
    from omnibase_core.models.delegation.model_escalation_event import (
        ModelEscalationEvent,
    )
    from omnibase_core.models.delegation.model_invocation_command import (
        ModelInvocationCommand,
    )
    from omnibase_core.models.delegation.model_model_health_status import (
        ModelModelHealthStatus,
    )
    from omnibase_core.models.delegation.model_remote_task_state import (
        ModelRemoteTaskState,
    )
    from omnibase_core.models.delegation.model_routing_rule import ModelRoutingRule
    from omnibase_core.models.delegation.model_target_agent import ModelTargetAgent

__all__ = [
    "EnumQualityGateResult",
    "EnumModelHealthState",
    "EnumRedactionPolicy",
    "ModelA2ATaskRequest",
    "ModelA2ATaskResponse",
    "ModelAgentTaskLifecycleEvent",
    "ModelDelegationRequest",
    "ModelEscalationEvent",
    "ModelInvocationCommand",
    "ModelModelHealthStatus",
    "ModelRemoteTaskState",
    "ModelRoutingRule",
    "ModelTargetAgent",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "EnumModelHealthState": (
        "omnibase_core.enums.enum_model_health_state",
        "EnumModelHealthState",
    ),
    "EnumQualityGateResult": (
        "omnibase_core.enums.enum_quality_gate_result",
        "EnumQualityGateResult",
    ),
    "EnumRedactionPolicy": (
        "omnibase_core.enums.enum_redaction_policy",
        "EnumRedactionPolicy",
    ),
    "ModelA2ATaskRequest": (
        "omnibase_core.models.delegation.model_a2a_task_request",
        "ModelA2ATaskRequest",
    ),
    "ModelA2ATaskResponse": (
        "omnibase_core.models.delegation.model_a2a_task_response",
        "ModelA2ATaskResponse",
    ),
    "ModelAgentTaskLifecycleEvent": (
        "omnibase_core.models.delegation.model_agent_task_lifecycle_event",
        "ModelAgentTaskLifecycleEvent",
    ),
    "ModelDelegationRequest": (
        "omnibase_core.models.delegation.model_delegation_request",
        "ModelDelegationRequest",
    ),
    "ModelEscalationEvent": (
        "omnibase_core.models.delegation.model_escalation_event",
        "ModelEscalationEvent",
    ),
    "ModelInvocationCommand": (
        "omnibase_core.models.delegation.model_invocation_command",
        "ModelInvocationCommand",
    ),
    "ModelModelHealthStatus": (
        "omnibase_core.models.delegation.model_model_health_status",
        "ModelModelHealthStatus",
    ),
    "ModelRemoteTaskState": (
        "omnibase_core.models.delegation.model_remote_task_state",
        "ModelRemoteTaskState",
    ),
    "ModelRoutingRule": (
        "omnibase_core.models.delegation.model_routing_rule",
        "ModelRoutingRule",
    ),
    "ModelTargetAgent": (
        "omnibase_core.models.delegation.model_target_agent",
        "ModelTargetAgent",
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
