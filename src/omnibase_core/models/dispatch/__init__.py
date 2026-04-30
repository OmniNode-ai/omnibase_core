# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Dispatch Engine Models.

Core models for the ONEX runtime dispatch engine that routes messages
based on topic category and message type, and publishes handler outputs.

Exports:
- **ModelDispatchRoute**: Routing rules that map topic patterns to handlers
- **ModelDispatchResult**: Results of dispatch operations with metrics
- **ModelHandlerRegistration**: Handler registration metadata
- **EnumDispatchStatus**: Status values for dispatch outcomes

Design Principles:
    - **Pure Domain Models**: No I/O dependencies, no infrastructure concerns
    - **Immutable**: All models are frozen (thread-safe after creation)
    - **Typed**: Strong typing with validation constraints
    - **Serializable**: Full JSON serialization support

Data Flow:
    ```
    ┌──────────────────────────────────────────────────────────────────┐
    │                     Dispatch Engine Flow                          │
    ├──────────────────────────────────────────────────────────────────┤
    │                                                                  │
    │   Incoming Message      Route Matching       Handler Execution   │
    │        │                     │                      │            │
    │        │  (topic, category)  │                      │            │
    │        │────────────────────>│                      │            │
    │        │                     │  ModelDispatchRoute  │            │
    │        │                     │─────────────────────>│            │
    │        │                     │                      │            │
    │        │                     │                      │ execute    │
    │        │                     │                      │────────>   │
    │        │                     │                      │            │
    │        │                     │  ModelDispatchResult │            │
    │        │<────────────────────│<─────────────────────│            │
    │                                                                  │
    └──────────────────────────────────────────────────────────────────┘
    ```

Usage:
    >>> from omnibase_core.models.dispatch import (
    ...     ModelDispatchRoute,
    ...     ModelDispatchResult,
    ...     ModelHandlerRegistration,
    ...     EnumDispatchStatus,
    ... )
    >>> from omnibase_core.enums import EnumMessageCategory, EnumNodeKind
    >>> from uuid import uuid4
    >>>
    >>> # Register a handler
    >>> handler = ModelHandlerRegistration(
    ...     handler_id="user-handler",
    ...     handler_name="User Event Handler",
    ...     node_kind=EnumNodeKind.REDUCER,
    ...     supported_categories=[EnumMessageCategory.EVENT],
    ... )
    >>>
    >>> # Create a route
    >>> route = ModelDispatchRoute(
    ...     route_id="user-route",
    ...     topic_pattern="*.user.events.*",
    ...     message_category=EnumMessageCategory.EVENT,
    ...     handler_id="user-handler",
    ... )
    >>>
    >>> # Check if route matches
    >>> route.matches_topic("dev.user.events.v1")
    True
    >>>
    >>> # Create a dispatch result
    >>> result = ModelDispatchResult(
    ...     dispatch_id=uuid4(),
    ...     status=EnumDispatchStatus.SUCCESS,
    ...     topic="dev.user.events.v1",
    ...     route_id="user-route",
    ...     handler_id="user-handler",
    ... )

See Also:
    omnibase_core.enums.EnumMessageCategory: Message category classification
    omnibase_core.enums.EnumExecutionShape: Valid execution patterns
    omnibase_core.models.events.ModelEventEnvelope: Event wrapper with routing info
"""

from omnibase_core.enums.enum_dispatch_lifecycle_emitter import (
    EnumDispatchLifecycleEmitter,
)
from omnibase_core.enums.enum_dispatch_lifecycle_state import (
    EnumDispatchLifecycleState,
)
from omnibase_core.enums.enum_dispatch_status import EnumDispatchStatus
from omnibase_core.enums.enum_dispatch_verdict import EnumDispatchVerdict
from omnibase_core.errors.error_lifecycle_emitter import LifecycleEmitterError
from omnibase_core.errors.error_lifecycle_transition import (
    LifecycleTransitionError,
)
from omnibase_core.models.dispatch.model_dispatch_bus_command import (
    ModelDispatchBusCommand,
)
from omnibase_core.models.dispatch.model_dispatch_bus_route import (
    ModelDispatchBusRoute,
)
from omnibase_core.models.dispatch.model_dispatch_bus_terminal_result import (
    ModelDispatchBusTerminalResult,
)
from omnibase_core.models.dispatch.model_dispatch_claim import (
    ModelDispatchClaim,
    compute_blocker_id,
)
from omnibase_core.models.dispatch.model_dispatch_eval_result import (
    ModelDispatchEvalResult,
)
from omnibase_core.models.dispatch.model_dispatch_lifecycle_event import (
    ModelDispatchLifecycleEvent,
)
from omnibase_core.models.dispatch.model_dispatch_result import ModelDispatchResult
from omnibase_core.models.dispatch.model_dispatch_route import ModelDispatchRoute
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.dispatch.model_handler_registration import (
    ModelHandlerRegistration,
)
from omnibase_core.models.dispatch.model_lifecycle_chain import (
    DEFAULT_HEARTBEAT_REQUIRED_SECONDS,
    HEARTBEAT_REQUIRED_ENV_VAR,
    ModelLifecycleChain,
)
from omnibase_core.models.dispatch.model_model_call_record import ModelCallRecord
from omnibase_core.models.dispatch.model_topic_parser import (
    EnumTopicStandard,
    ModelParsedTopic,
    ModelTopicParser,
)

__all__ = [
    # Constants
    "DEFAULT_HEARTBEAT_REQUIRED_SECONDS",
    "HEARTBEAT_REQUIRED_ENV_VAR",
    # Enums
    "EnumDispatchLifecycleEmitter",
    "EnumDispatchLifecycleState",
    "EnumDispatchStatus",
    "EnumDispatchVerdict",
    "EnumTopicStandard",
    # Errors
    "LifecycleEmitterError",
    "LifecycleTransitionError",
    # Models
    "ModelLifecycleChain",
    "ModelDispatchClaim",
    "ModelDispatchBusCommand",
    "ModelDispatchBusRoute",
    "ModelDispatchBusTerminalResult",
    "ModelDispatchLifecycleEvent",
    "ModelDispatchEvalResult",
    "ModelDispatchResult",
    "ModelDispatchRoute",
    "ModelCallRecord",
    "ModelHandlerOutput",
    "ModelHandlerRegistration",
    "ModelParsedTopic",
    "ModelTopicParser",
    # Functions
    "compute_blocker_id",
]
