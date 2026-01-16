"""
Notification models for the ONEX framework.

This module provides models for various notification types used in
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

from omnibase_core.models.notifications.model_state_transition_notification import (
    ModelStateTransitionNotification,
)

__all__ = [
    "ModelStateTransitionNotification",
]
