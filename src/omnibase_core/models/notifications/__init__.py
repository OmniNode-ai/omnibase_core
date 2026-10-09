# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Notification models for the ONEX framework.

Models for various notification types used in
event-driven communication between ONEX components.

Notifications enable:
- Loose coupling between components (Observer pattern)
- Post-commit state change propagation
- Orchestrator workflow coordination
- Distributed system event handling

Models:
    ModelStateTransitionNotification: Notification emitted after state
        transitions are committed, enabling orchestrators to react.

Usage:
    >>> from omnibase_core.models.notifications import (
    ...     ModelStateTransitionNotification,
    ... )
    >>> from datetime import datetime, UTC
    >>> from uuid import uuid4
    >>>
    >>> notification = ModelStateTransitionNotification(
    ...     aggregate_type="registration",
    ...     aggregate_id=uuid4(),
    ...     from_state="pending",
    ...     to_state="active",
    ...     projection_version=1,
    ...     correlation_id=uuid4(),
    ...     causation_id=uuid4(),
    ...     timestamp=datetime.now(UTC),
    ... )

See Also:
    omnibase_core.protocols.notifications: Protocols for publishing/consuming
        notifications.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.notifications.model_state_transition_notification import (
        ModelStateTransitionNotification,
    )

__all__ = [
    "ModelStateTransitionNotification",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelStateTransitionNotification": (
        "omnibase_core.models.notifications.model_state_transition_notification",
        "ModelStateTransitionNotification",
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
