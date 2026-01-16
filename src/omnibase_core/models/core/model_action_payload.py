"""
Action payload model for tool-as-a-service execution.

This module provides ModelActionPayload, a comprehensive wrapper that combines
a ModelNodeAction with typed execution parameters, context, and service
composition metadata. It serves as the primary transport model for action
invocation across MCP (Model Context Protocol), GraphQL, and internal service
boundaries.

ModelActionPayload inherits from ModelOnexInputState to automatically include
standard ONEX traceability fields (correlation_id, event_id, timestamp) which
enable distributed tracing and debugging across service boundaries.

Key Features:
    - Typed execution parameters via ModelActionParameters
    - Service routing and load balancing metadata
    - Execution chain tracking for action composition
    - Trust level propagation for security boundaries
    - Tool discovery tags for dynamic service matching

Thread Safety:
    ModelActionPayload is NOT frozen (mutable) and contains mutable list fields
    (execution_chain, tool_discovery_tags). This means:

    - The model is NOT safe for concurrent modification from multiple threads
    - List fields can be mutated in place, which is NOT thread-safe
    - For multi-threaded scenarios, either:
      1. Create separate instances per thread
      2. Use external synchronization (locks)
      3. Treat all mutable fields as immutable by convention

    The add_to_execution_chain() method mutates the execution_chain list and
    is NOT thread-safe. If you need concurrent access, copy the payload first.

See Also:
    - omnibase_core.models.core.model_node_action: The action being wrapped
    - omnibase_core.models.context.model_action_parameters: Execution parameters
    - omnibase_core.models.context.model_action_execution_context: Runtime context
    - omnibase_core.models.context.model_routing_metadata: Service routing config
    - omnibase_core.models.context.model_service_discovery_metadata: Discovery info
    - omnibase_core.models.core.model_onex_base_state: Base state with traceability
"""

from typing import Any
from uuid import UUID

from pydantic import ConfigDict, Field

# Direct module imports to avoid circular import via context/__init__.py
from omnibase_core.models.context.model_action_execution_context import (
    ModelActionExecutionContext,
)
from omnibase_core.models.context.model_action_parameters import ModelActionParameters
from omnibase_core.models.context.model_routing_metadata import ModelRoutingMetadata
from omnibase_core.models.context.model_service_discovery_metadata import (
    ModelServiceDiscoveryMetadata,
)

from .model_node_action import ModelNodeAction
from .model_onex_base_state import ModelOnexInputState


class ModelActionPayload(ModelOnexInputState):
    """
    Action payload with rich metadata for tool-as-a-service execution.

    Wraps a ModelNodeAction with execution parameters and context for use in
    MCP (Model Context Protocol), GraphQL action invocation, and internal
    service composition workflows. This is the primary transport model for
    action dispatch across service boundaries.

    Inherits from ModelOnexInputState to get standard ONEX traceability fields
    (correlation_id, event_id, timestamp, etc.) which enable distributed
    tracing, debugging, and audit logging across the entire execution chain.

    Attributes:
        action: The ModelNodeAction to execute. Required field that defines
            the action type, name, and payload to be processed.
        parameters: Typed execution parameters (ModelActionParameters) including
            timeout overrides, idempotency keys, validation flags, and format
            specifications. Defaults to empty parameters.
        execution_context: Runtime execution context (ModelActionExecutionContext)
            containing environment metadata, caller information, and execution
            flags. Defaults to empty context.
        parent_correlation_id: UUID of the parent action's correlation_id for
            action chaining. Used to build a complete trace of nested action
            invocations. None for root-level actions.
        execution_chain: List of action names in the execution chain, ordered
            from root to current. Used for composition tracking, cycle detection,
            and debugging nested action flows. WARNING: Mutable list field.
        target_service: Optional target service identifier for action routing.
            When set, bypasses discovery and routes directly to the named service.
        routing_metadata: Service routing and load balancing configuration
            (ModelRoutingMetadata) including region preferences, retry policies,
            and circuit breaker settings. Defaults to empty metadata.
        trust_level: Trust score for action execution ranging from 0.0 (untrusted)
            to 1.0 (fully trusted). Propagates through action chains, taking the
            minimum of parent and child trust levels. Used for security boundaries
            and capability restrictions.
        service_metadata: Optional service discovery metadata
            (ModelServiceDiscoveryMetadata) containing capabilities, health info,
            and version constraints for dynamic service matching.
        tool_discovery_tags: List of string tags for tool discovery and
            categorization. Used by service registries to match actions to
            capable executors. WARNING: Mutable list field.

        Inherited from ModelOnexInputState:
            version: Required ModelSemVer for the payload schema version.
            event_id: Optional UUID for event correlation.
            correlation_id: Optional UUID for distributed tracing.
            node_name: Optional name of the originating node.
            node_version: Optional ModelSemVer of the originating node.
            timestamp: Optional datetime of payload creation.

    Thread Safety:
        This model is NOT frozen and contains mutable list fields
        (execution_chain, tool_discovery_tags). It is NOT safe for concurrent
        modification. For multi-threaded scenarios, create separate instances
        per thread or use external synchronization.

    Example:
        >>> from uuid import uuid4
        >>> from omnibase_core.models.core import ModelActionPayload, ModelNodeAction
        >>> from omnibase_core.models.context import ModelActionParameters
        >>> from omnibase_core.models.primitives import ModelSemVer
        >>> from omnibase_core.enums import EnumActionType
        >>>
        >>> # Create an action payload for a transform operation
        >>> from omnibase_core.constants import TIMEOUT_DEFAULT_MS
        >>> payload = ModelActionPayload(
        ...     version=ModelSemVer(major=1, minor=0, patch=0),
        ...     action=ModelNodeAction(
        ...         action_type=EnumActionType.EXECUTE,
        ...         action_name="transform_data",
        ...         payload={"input": "data"},
        ...     ),
        ...     parameters=ModelActionParameters(
        ...         timeout_override_ms=TIMEOUT_DEFAULT_MS,
        ...         validate_input=True,
        ...     ),
        ...     target_service="data-transformer",
        ...     trust_level=0.9,
        ... )
        >>>
        >>> # Track execution chain for nested actions
        >>> payload.add_to_execution_chain("transform_data")
        >>> child_action = ModelNodeAction(
        ...     action_type=EnumActionType.EXECUTE,
        ...     action_name="validate_output",
        ...     payload={},
        ... )
        >>> child_payload = payload.create_child_payload(child_action)
        >>> child_payload.parent_correlation_id == payload.correlation_id
        True
    """

    model_config = ConfigDict(from_attributes=True)

    action: ModelNodeAction = Field(default=..., description="The action to execute")
    parameters: ModelActionParameters = Field(
        default_factory=ModelActionParameters,
        description="Action execution parameters with strong typing",
    )
    execution_context: ModelActionExecutionContext = Field(
        default_factory=ModelActionExecutionContext,
        description="Execution context and environment metadata",
    )

    # Execution tracking (in addition to base correlation_id)
    parent_correlation_id: UUID | None = Field(
        default=None,
        description="Parent action correlation ID for chaining",
    )
    execution_chain: list[str] = Field(
        default_factory=list,
        description="Execution chain for action composition tracking",
    )

    # Service composition with strong typing
    target_service: str | None = Field(
        default=None,
        description="Target service for action execution",
    )
    routing_metadata: ModelRoutingMetadata = Field(
        default_factory=ModelRoutingMetadata,
        description="Service routing and load balancing metadata",
    )
    trust_level: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Trust score for action execution (0.0-1.0)",
    )

    # Tool-as-a-Service metadata with strong typing
    service_metadata: ModelServiceDiscoveryMetadata | None = Field(
        default=None,
        description="Service discovery and composition metadata",
    )
    tool_discovery_tags: list[str] = Field(
        default_factory=list,
        description="Tags for tool discovery and categorization",
    )

    def add_to_execution_chain(self, action_name: str) -> None:
        """
        Add an action name to the execution chain for composition tracking.

        Appends the given action name to the end of the execution_chain list,
        building a trace of all actions invoked in sequence. This is useful for
        debugging nested action flows, detecting cycles, and auditing execution
        paths.

        Args:
            action_name: The name of the action being added to the chain.
                Should match the action_name field of the ModelNodeAction
                being executed.

        Returns:
            None. The execution_chain list is modified in place.

        Warning:
            This method mutates the execution_chain list in place and is NOT
            thread-safe. If multiple threads need to track execution chains,
            create separate ModelActionPayload instances per thread.

        Example:
            >>> payload.add_to_execution_chain("fetch_data")
            >>> payload.add_to_execution_chain("transform_data")
            >>> payload.execution_chain
            ['fetch_data', 'transform_data']
        """
        self.execution_chain.append(action_name)

    def create_child_payload(
        self,
        child_action: ModelNodeAction,
        **kwargs: Any,
    ) -> "ModelActionPayload":
        """
        Create a child payload for action composition with inherited context.

        Creates a new ModelActionPayload for a nested action invocation,
        automatically inheriting relevant context from the parent payload:

        - parent_correlation_id is set to this payload's correlation_id
        - execution_chain is copied (not shared) from the parent
        - trust_level takes the minimum of parent and child (security propagation)
        - service_metadata is inherited (immutable, shared reference is safe)
        - version is inherited from the parent

        This method enables safe action composition by ensuring child actions
        maintain traceability to their parent while preventing accidental
        mutation of the parent's execution chain.

        Args:
            child_action: The ModelNodeAction to wrap in the child payload.
                This becomes the 'action' field of the returned payload.
            **kwargs: Additional keyword arguments passed to the child
                ModelActionPayload constructor. Can override any field except
                those explicitly set (action, parent_correlation_id,
                execution_chain, version, service_metadata). If trust_level
                is provided, the child's trust_level will be the minimum of
                the parent's trust_level and the provided value.

        Returns:
            ModelActionPayload: A new payload configured for the child action
                with inherited context. The returned payload has its own
                execution_chain list (copied from parent) that can be
                modified independently.

        Example:
            >>> from omnibase_core.enums import EnumActionType
            >>>
            >>> # Parent action for data processing
            >>> parent_payload = ModelActionPayload(
            ...     version=ModelSemVer(major=1, minor=0, patch=0),
            ...     action=ModelNodeAction(
            ...         action_type=EnumActionType.EXECUTE,
            ...         action_name="process_batch",
            ...         payload={"batch_id": 123},
            ...     ),
            ...     trust_level=0.8,
            ... )
            >>> parent_payload.add_to_execution_chain("process_batch")
            >>>
            >>> # Create child action for validation step
            >>> validate_action = ModelNodeAction(
            ...     action_type=EnumActionType.EXECUTE,
            ...     action_name="validate_batch",
            ...     payload={"batch_id": 123},
            ... )
            >>> child_payload = parent_payload.create_child_payload(
            ...     validate_action,
            ...     target_service="validator-service",
            ... )
            >>>
            >>> # Child inherits parent context
            >>> child_payload.parent_correlation_id == parent_payload.correlation_id
            True
            >>> child_payload.trust_level  # Inherited from parent
            0.8
            >>> child_payload.execution_chain  # Copy of parent's chain
            ['process_batch']
        """
        # Pop trust_level from kwargs to avoid duplicate keyword argument error
        # Cast to float since kwargs values are typed as object
        child_trust_level_raw = kwargs.pop("trust_level", 1.0)
        child_trust_level = (
            float(child_trust_level_raw)
            if isinstance(child_trust_level_raw, (int, float))
            else 1.0
        )
        return ModelActionPayload(
            action=child_action,
            parent_correlation_id=self.correlation_id,
            execution_chain=self.execution_chain.copy(),
            trust_level=min(self.trust_level, child_trust_level),
            service_metadata=self.service_metadata,  # Immutable, no copy needed
            version=self.version,  # Required field from ModelOnexInputState
            **kwargs,
        )
