# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Runtime protocols for ONEX message handler integration.

Core-native protocol definitions for runtime handlers.
These protocols establish the contracts that handler implementations (in SPI
or other packages) must satisfy, enabling dependency inversion.

Design Principles:
- Use typing.Protocol with @runtime_checkable for duck typing support
- Keep interfaces minimal - only define what Core actually needs
- Use TYPE_CHECKING imports to avoid runtime dependency cycles
- Provide complete type hints for mypy strict mode compliance

Module Organization:
- protocol_delegation_dispatch_port.py: Delegation dispatch port (OMN-19838)
- protocol_handler_registry.py: Handler registry protocol for DI abstraction
- protocol_message_handler.py: Category-based message handler protocol

Dependency Injection:
    Register handler registry under "ProtocolHandlerRegistry" DI token:

    .. code-block:: python

        container.register_service("ProtocolHandlerRegistry", registry)

    Resolve via DI in node constructors:

    .. code-block:: python

        registry = container.get_service("ProtocolHandlerRegistry")

Related:
    - OMN-934: Handler registry for message dispatch engine
    - OMN-1293: Contract-driven handler routing

.. versionadded:: 0.4.0
.. versionchanged:: 0.6.3
   Added ProtocolHandlerRegistry for handler registry abstraction.
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.protocols.runtime.protocol_delegation_dispatch_port import (
        ProtocolDelegationDispatchPort,
    )
    from omnibase_core.protocols.runtime.protocol_handler_registry import (
        ProtocolHandlerRegistry,
    )
    from omnibase_core.protocols.runtime.protocol_harness_inference_adapter import (
        ProtocolHarnessInferenceAdapter,
    )
    from omnibase_core.protocols.runtime.protocol_harness_projection_store import (
        ProtocolHarnessProjectionStore,
    )
    from omnibase_core.protocols.runtime.protocol_local_runtime_bus import (
        ProtocolLocalRuntimeBus,
        UnsubscribeCallback,
    )
    from omnibase_core.protocols.runtime.protocol_local_runtime_callable_target import (
        ProtocolLocalRuntimeCallableTarget,
    )
    from omnibase_core.protocols.runtime.protocol_local_runtime_dump_model import (
        ProtocolLocalRuntimeDumpModel,
    )
    from omnibase_core.protocols.runtime.protocol_local_runtime_message import (
        ProtocolLocalRuntimeMessage,
    )
    from omnibase_core.protocols.runtime.protocol_local_runtime_payload_model import (
        ProtocolLocalRuntimePayloadModel,
    )
    from omnibase_core.protocols.runtime.protocol_message_handler import (
        ProtocolMessageHandler,
    )
    from omnibase_core.protocols.runtime.protocol_runtime_skill_client import (
        ProtocolRuntimeSkillClient,
    )
    from omnibase_core.protocols.runtime.protocol_transport_consumer import (
        ProtocolTransportConsumer,
    )
    from omnibase_core.protocols.runtime.protocol_transport_message import (
        ProtocolTransportMessage,
    )
    from omnibase_core.protocols.runtime.protocol_transport_producer import (
        ProtocolTransportProducer,
    )

__all__ = [
    "ProtocolDelegationDispatchPort",
    "ProtocolHandlerRegistry",
    "ProtocolHarnessInferenceAdapter",
    "ProtocolHarnessProjectionStore",
    "ProtocolLocalRuntimeBus",
    "ProtocolLocalRuntimeCallableTarget",
    "ProtocolLocalRuntimeDumpModel",
    "ProtocolLocalRuntimeMessage",
    "ProtocolLocalRuntimePayloadModel",
    "ProtocolMessageHandler",
    "ProtocolRuntimeSkillClient",
    "ProtocolTransportConsumer",
    "ProtocolTransportMessage",
    "ProtocolTransportProducer",
    "UnsubscribeCallback",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ProtocolDelegationDispatchPort": (
        "omnibase_core.protocols.runtime.protocol_delegation_dispatch_port",
        "ProtocolDelegationDispatchPort",
    ),
    "ProtocolHandlerRegistry": (
        "omnibase_core.protocols.runtime.protocol_handler_registry",
        "ProtocolHandlerRegistry",
    ),
    "ProtocolHarnessInferenceAdapter": (
        "omnibase_core.protocols.runtime.protocol_harness_inference_adapter",
        "ProtocolHarnessInferenceAdapter",
    ),
    "ProtocolHarnessProjectionStore": (
        "omnibase_core.protocols.runtime.protocol_harness_projection_store",
        "ProtocolHarnessProjectionStore",
    ),
    "ProtocolLocalRuntimeBus": (
        "omnibase_core.protocols.runtime.protocol_local_runtime_bus",
        "ProtocolLocalRuntimeBus",
    ),
    "UnsubscribeCallback": (
        "omnibase_core.protocols.runtime.protocol_local_runtime_bus",
        "UnsubscribeCallback",
    ),
    "ProtocolLocalRuntimeCallableTarget": (
        "omnibase_core.protocols.runtime.protocol_local_runtime_callable_target",
        "ProtocolLocalRuntimeCallableTarget",
    ),
    "ProtocolLocalRuntimeDumpModel": (
        "omnibase_core.protocols.runtime.protocol_local_runtime_dump_model",
        "ProtocolLocalRuntimeDumpModel",
    ),
    "ProtocolLocalRuntimeMessage": (
        "omnibase_core.protocols.runtime.protocol_local_runtime_message",
        "ProtocolLocalRuntimeMessage",
    ),
    "ProtocolLocalRuntimePayloadModel": (
        "omnibase_core.protocols.runtime.protocol_local_runtime_payload_model",
        "ProtocolLocalRuntimePayloadModel",
    ),
    "ProtocolMessageHandler": (
        "omnibase_core.protocols.runtime.protocol_message_handler",
        "ProtocolMessageHandler",
    ),
    "ProtocolRuntimeSkillClient": (
        "omnibase_core.protocols.runtime.protocol_runtime_skill_client",
        "ProtocolRuntimeSkillClient",
    ),
    "ProtocolTransportConsumer": (
        "omnibase_core.protocols.runtime.protocol_transport_consumer",
        "ProtocolTransportConsumer",
    ),
    "ProtocolTransportMessage": (
        "omnibase_core.protocols.runtime.protocol_transport_message",
        "ProtocolTransportMessage",
    ),
    "ProtocolTransportProducer": (
        "omnibase_core.protocols.runtime.protocol_transport_producer",
        "ProtocolTransportProducer",
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
