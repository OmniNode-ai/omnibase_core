"""
Dispatch Engine Models.

Core models for the ONEX runtime dispatch engine that routes messages
based on topic category and message type, and publishes handler outputs.

This module provides:
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

from omnibase_core.enums.enum_dispatch_status import EnumDispatchStatus
from omnibase_core.models.dispatch.model_dispatch_result import ModelDispatchResult
from omnibase_core.models.dispatch.model_dispatch_route import ModelDispatchRoute
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.dispatch.model_handler_registration import (
    ModelHandlerRegistration,
)
from omnibase_core.models.dispatch.model_topic_parser import (
    EnumTopicStandard,
    ModelParsedTopic,
    ModelTopicParser,
)

__all__ = [
    # Enums
    "EnumDispatchStatus",
    "EnumTopicStandard",
    # Models
    "ModelDispatchResult",
    "ModelDispatchRoute",
    "ModelHandlerOutput",
    "ModelHandlerRegistration",
    "ModelParsedTopic",
    "ModelTopicParser",
]
