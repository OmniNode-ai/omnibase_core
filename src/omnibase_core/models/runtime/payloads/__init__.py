# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Typed payload models for runtime directives.

This package provides type-safe payload models for each directive type defined
in EnumDirectiveType, replacing the previous untyped dict[str, Any] approach.

Exports:
    Base:
        - ModelDirectivePayloadBase: Base class for all payloads

    Payload Models:
        - ModelScheduleEffectPayload: For SCHEDULE_EFFECT directives
        - ModelEnqueueHandlerPayload: For ENQUEUE_HANDLER directives
        - ModelRetryWithBackoffPayload: For RETRY_WITH_BACKOFF directives
        - ModelDelayUntilPayload: For DELAY_UNTIL directives
        - ModelCancelExecutionPayload: For CANCEL_EXECUTION directives

    Union Type:
        - ModelDirectivePayload: Discriminated union of all payload types

Example:
    >>> from omnibase_core.models.runtime.payloads import (
    ...     ModelDirectivePayload,
    ...     ModelScheduleEffectPayload,
    ... )
    >>>
    >>> # Create a typed payload
    >>> payload = ModelScheduleEffectPayload(
    ...     effect_node_type="http_request",
    ... )
    >>>
    >>> # Use discriminated union for deserialization
    >>> data = {"kind": "cancel_execution", "execution_id": "..."}
    >>> payload = ModelDirectivePayload.model_validate(data)

See Also:
    - omnibase_core.enums.enum_directive_type: EnumDirectiveType values
    - omnibase_core.models.runtime.model_runtime_directive: ModelRuntimeDirective
"""

from __future__ import annotations

# Split payload files
import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.runtime.payloads.model_cancel_execution_payload import (
        ModelCancelExecutionPayload,
    )
    from omnibase_core.models.runtime.payloads.model_delay_until_payload import (
        ModelDelayUntilPayload,
    )
    from omnibase_core.models.runtime.payloads.model_directive_payload_base import (
        ModelDirectivePayloadBase,
    )
    from omnibase_core.models.runtime.payloads.model_directive_payload_union import (
        ModelDirectivePayload,
    )
    from omnibase_core.models.runtime.payloads.model_enqueue_handler_payload import (
        ModelEnqueueHandlerPayload,
    )
    from omnibase_core.models.runtime.payloads.model_retry_with_backoff_payload import (
        ModelRetryWithBackoffPayload,
    )
    from omnibase_core.models.runtime.payloads.model_schedule_effect_payload import (
        ModelScheduleEffectPayload,
    )

__all__ = [
    # Base
    "ModelDirectivePayloadBase",
    # Payload Models
    "ModelScheduleEffectPayload",
    "ModelEnqueueHandlerPayload",
    "ModelRetryWithBackoffPayload",
    "ModelDelayUntilPayload",
    "ModelCancelExecutionPayload",
    # Union Type
    "ModelDirectivePayload",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelCancelExecutionPayload": (
        "omnibase_core.models.runtime.payloads.model_cancel_execution_payload",
        "ModelCancelExecutionPayload",
    ),
    "ModelDelayUntilPayload": (
        "omnibase_core.models.runtime.payloads.model_delay_until_payload",
        "ModelDelayUntilPayload",
    ),
    "ModelDirectivePayloadBase": (
        "omnibase_core.models.runtime.payloads.model_directive_payload_base",
        "ModelDirectivePayloadBase",
    ),
    "ModelDirectivePayload": (
        "omnibase_core.models.runtime.payloads.model_directive_payload_union",
        "ModelDirectivePayload",
    ),
    "ModelEnqueueHandlerPayload": (
        "omnibase_core.models.runtime.payloads.model_enqueue_handler_payload",
        "ModelEnqueueHandlerPayload",
    ),
    "ModelRetryWithBackoffPayload": (
        "omnibase_core.models.runtime.payloads.model_retry_with_backoff_payload",
        "ModelRetryWithBackoffPayload",
    ),
    "ModelScheduleEffectPayload": (
        "omnibase_core.models.runtime.payloads.model_schedule_effect_payload",
        "ModelScheduleEffectPayload",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        # A submodule that the old eager __init__ loaded as a side effect
        # stays reachable as ``package.submodule``: import it on first access.
        if (
            name.isidentifier()
            and not name.startswith("__")
            and importlib.util.find_spec(f"{__name__}.{name}") is not None
        ):
            return importlib.import_module(f"{__name__}.{name}")
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
