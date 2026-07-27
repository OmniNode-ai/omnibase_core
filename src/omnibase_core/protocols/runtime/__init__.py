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
