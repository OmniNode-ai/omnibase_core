# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Notification protocols for the ONEX framework.

Protocol definitions for notification publishing
and consuming in the ONEX framework.

Protocols enable:
- Duck typing for notification services
- Interface segregation (separate publish/consume concerns)
- Runtime type checking via @runtime_checkable
- Flexible implementation strategies (Kafka, in-memory, etc.)

Protocols:
    ProtocolTransitionNotificationPublisher: Contract for publishing
        state transition notifications.
    ProtocolTransitionNotificationConsumer: Contract for consuming
        state transition notifications.

Usage:
    >>> from omnibase_core.protocols.notifications import (
    ...     ProtocolTransitionNotificationPublisher,
    ...     ProtocolTransitionNotificationConsumer,
    ... )
    >>>
    >>> class MyPublisher:
    ...     async def publish(
    ...         self, notification: ModelStateTransitionNotification
    ...     ) -> None:
    ...         # Implementation
    ...         pass
    ...
    ...     async def publish_batch(
    ...         self, notifications: list[ModelStateTransitionNotification]
    ...     ) -> None:
    ...         # Implementation
    ...         pass
    >>>
    >>> publisher = MyPublisher()
    >>> isinstance(publisher, ProtocolTransitionNotificationPublisher)  # True

See Also:
    omnibase_core.models.notifications: Notification models that these
        protocols work with.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.protocols.notifications.protocol_transition_notification import (
        ProtocolTransitionNotificationConsumer,
        ProtocolTransitionNotificationPublisher,
    )

__all__ = [
    "ProtocolTransitionNotificationPublisher",
    "ProtocolTransitionNotificationConsumer",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ProtocolTransitionNotificationConsumer": (
        "omnibase_core.protocols.notifications.protocol_transition_notification",
        "ProtocolTransitionNotificationConsumer",
    ),
    "ProtocolTransitionNotificationPublisher": (
        "omnibase_core.protocols.notifications.protocol_transition_notification",
        "ProtocolTransitionNotificationPublisher",
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
