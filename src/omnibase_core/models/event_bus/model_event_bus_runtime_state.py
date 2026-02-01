"""Runtime state model for event bus operations.

This model holds serializable runtime state for event bus operations.
It is designed to be mutable to allow state updates during event bus lifecycle.

Thread Safety:
    ModelEventBusRuntimeState instances are mutable (frozen=False) and are
    NOT thread-safe. Do not share instances across threads without external
    synchronization.
"""

import warnings

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants.constants_field_limits import (
    MAX_NAME_LENGTH,
    MAX_PATH_LENGTH,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelEventBusRuntimeState(BaseModel):
    """
    Serializable runtime state for event bus operations.

    This model captures the runtime state of an event bus binding, including
    the node identity, contract configuration, and binding status. It is
    designed to be lightweight and serializable for persistence or transfer.

    Note:
        This model does NOT contain threading objects (those belong in
        ListenerHandle) or dynamic bindings like registry/event_bus references.

    None Semantics:
        Both ``node_name`` and ``contract_path`` use ``None`` to mean
        "not explicitly set" with consistent semantics:

        - **node_name**: ``None`` means "no node name bound". When None,
          consumers should fall back to an alternative (e.g., class name).
          Use ``has_node_name()`` to check if explicitly set.

        - **contract_path**: ``None`` means "no contract configured".
          Use ``has_contract_path()`` to check if explicitly set.

        This design allows callers to use simple truthiness checks:
        ``if state.node_name:`` or ``if state.contract_path:`` to determine
        if a value was explicitly provided.

    Attributes:
        node_name: Identifier for the node using this event bus binding.
            ``None`` indicates no node name is bound; consumers should use
            a fallback (typically the class name).
        contract_path: Path to the contract YAML file that defines the event
            bus configuration. ``None`` means "no contract configured".
        is_bound: Flag indicating whether the event bus is currently bound
            to a node and ready for operations.

    Example:
        >>> state = ModelEventBusRuntimeState(
        ...     node_name="my_service_node",
        ...     contract_path="/path/to/contract.yaml",
        ...     is_bound=True
        ... )
        >>> state.is_ready()
        True
        >>> state.has_node_name()
        True
        >>> state.has_contract_path()
        True
    """

    # Note on from_attributes=True: Added for pytest-xdist parallel execution
    # compatibility. See CLAUDE.md "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(frozen=False, extra="forbid", from_attributes=True)

    node_name: str | None = Field(
        default=None,
        description=(
            "Node identifier for the event bus binding. None means 'not set' "
            "and consumers should fall back to class name. Use has_node_name() "
            "to check if explicitly set."
        ),
        max_length=MAX_NAME_LENGTH,
    )
    contract_path: str | None = Field(
        default=None,
        description=(
            "Path to the contract YAML file defining event bus configuration. "
            "None means 'no contract configured'. Use has_contract_path() to "
            "check if explicitly set."
        ),
        max_length=MAX_PATH_LENGTH,
    )
    is_bound: bool = Field(
        default=False,
        description="Whether the event bus is bound and ready for operations",
    )

    def is_ready(self) -> bool:
        """Check if the event bus is bound and has a valid node name.

        Returns:
            True if bound with a non-empty node name, False otherwise.
        """
        return self.is_bound and bool(self.node_name)

    def has_node_name(self) -> bool:
        """Check if a node name has been explicitly set (not None and non-empty).

        This method provides a semantic check for whether a node name was
        explicitly bound. None is treated as "not set".

        Returns:
            True if node_name is not None and non-empty, False otherwise.

        Example:
            >>> state = ModelEventBusRuntimeState(node_name="my_node")
            >>> state.has_node_name()
            True
            >>> state = ModelEventBusRuntimeState(node_name=None)
            >>> state.has_node_name()
            False
            >>> state = ModelEventBusRuntimeState()
            >>> state.has_node_name()
            False
        """
        return self.node_name is not None and bool(self.node_name)

    def has_contract_path(self) -> bool:
        """Check if a contract path has been explicitly set (not None and non-empty).

        This method provides a semantic check for whether a contract path was
        explicitly configured. None is treated as "not set".

        Note:
            This differs from ``has_contract()`` which only checks for None.
            Use this method for consistent None-aware checking.

        Returns:
            True if contract_path is not None and non-empty, False otherwise.

        Example:
            >>> state = ModelEventBusRuntimeState(contract_path="/path.yaml")
            >>> state.has_contract_path()
            True
            >>> state = ModelEventBusRuntimeState(contract_path=None)
            >>> state.has_contract_path()
            False
            >>> state = ModelEventBusRuntimeState()
            >>> state.has_contract_path()
            False
        """
        return self.contract_path is not None and bool(self.contract_path)

    def has_contract(self) -> bool:
        """Check if a contract path is configured (not None).

        .. deprecated::
            Use ``has_contract_path()`` instead for consistent None
            semantics. This method only checks for None.

        Returns:
            True if contract_path is not None, False otherwise.
        """
        warnings.warn(
            "has_contract() is deprecated, use has_contract_path() instead "
            "for consistent None semantics",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.contract_path is not None

    def reset(self) -> None:
        """Clear runtime state while preserving binding configuration.

        Use for cleanup between operations. This is a "soft unbind" that clears
        only the binding status (is_bound=False) while preserving node_name and
        contract_path for potential rebinding.

        Contrast with bind():
            - **reset()**: Clears runtime state while preserving binding config.
              Use for cleanup between operations or before rebinding with new
              configuration. Does NOT clear node_name or contract_path.
            - **bind()**: Initializes state with node identity. MUST be called
              during initialization (__init__) to establish the binding. Sets
              node_name, contract_path, and is_bound=True together.

        When to Use:
            - Use reset() for cleanup between operations (e.g., test teardown)
            - Use reset() when temporarily pausing event bus operations
            - Use reset() before calling bind() with new configuration
            - Use create_unbound() instead when you want a completely fresh
              instance with all default values (None node_name, None contract_path)

        Example:
            >>> state = ModelEventBusRuntimeState.create_bound("node1", "/path.yaml")
            >>> state.is_ready()
            True
            >>> state.reset()  # Cleanup - keeps node_name="node1"
            >>> state.is_bound
            False
            >>> state.node_name  # Still preserved for potential rebind
            'node1'
            >>> state.bind("node2", "/new.yaml")  # Rebind with new config
            >>> state.is_ready()
            True

        See Also:
            bind(): Initializes state with node identity (call in __init__).
            create_unbound(): Creates a fresh instance with all defaults.
        """
        self.is_bound = False

    def bind(self, node_name: str, contract_path: str | None = None) -> None:
        """Initialize state with node identity. MUST be called in __init__.

        This method establishes the binding by setting node_name, contract_path,
        and is_bound=True together. Call this during initialization to configure
        the runtime state before the instance is used for event bus operations.

        Note:
            This method validates max_length constraints explicitly since direct
            field assignment bypasses Pydantic's field validation. This ensures
            the same constraints defined on the model fields are enforced.

        Contrast with reset():
            - **bind()**: Initializes state with node identity. MUST be called
              during initialization (__init__) to establish the binding. Sets
              all configuration values and marks as bound.
            - **reset()**: Clears runtime state while preserving binding config.
              Use for cleanup between operations. Only clears is_bound flag.

        Common Patterns:
            - Initial binding: create_unbound() then bind() in __init__
            - Reconfiguration: reset() then bind() with new values
            - Direct creation: create_bound() for one-step initialization

        Args:
            node_name: Identifier for the node using this event bus binding.
                Must be a non-empty string with max length of MAX_NAME_LENGTH.
                Use a non-empty string for a fully ready binding.
            contract_path: Optional path to contract YAML file. Pass None
                to indicate no contract. Max length of MAX_PATH_LENGTH.
                Use ``has_contract_path()`` to check if explicitly set.

        Raises:
            ModelOnexError: If node_name is empty or whitespace-only,
                or if node_name exceeds MAX_NAME_LENGTH,
                or if contract_path exceeds MAX_PATH_LENGTH
                (error code: VALIDATION_FAILED).

        Example:
            >>> state = ModelEventBusRuntimeState.create_unbound()
            >>> state.bind("my_node", "/path/to/contract.yaml")  # Call in __init__
            >>> state.is_ready()
            True
            >>> state.reset()  # Cleanup between operations
            >>> state.bind("different_node")  # Rebind with different config
            >>> state.node_name
            'different_node'

        See Also:
            reset(): Clears runtime state for cleanup between operations.
            create_bound(): One-step factory for creating a bound instance.
        """
        if not node_name or not node_name.strip():
            raise ModelOnexError(
                message=(
                    "node_name must be a non-empty string for binding; "
                    "use reset() to unbind without clearing configuration"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            )
        # Explicit max_length validation since direct field assignment bypasses
        # Pydantic's field validation. This ensures consistency with field constraints.
        if len(node_name) > MAX_NAME_LENGTH:
            raise ModelOnexError(
                message=(
                    f"node_name exceeds max length of {MAX_NAME_LENGTH} "
                    f"(got {len(node_name)} characters)"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            )
        if contract_path is not None and len(contract_path) > MAX_PATH_LENGTH:
            raise ModelOnexError(
                message=(
                    f"contract_path exceeds max length of {MAX_PATH_LENGTH} "
                    f"(got {len(contract_path)} characters)"
                ),
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            )
        self.node_name = node_name
        self.contract_path = contract_path
        self.is_bound = True

    @classmethod
    def create_unbound(cls) -> "ModelEventBusRuntimeState":
        """Create an unbound runtime state instance.

        Returns:
            New ModelEventBusRuntimeState with default unbound values.
        """
        return cls()

    @classmethod
    def create_bound(
        cls, node_name: str, contract_path: str | None = None
    ) -> "ModelEventBusRuntimeState":
        """Create a bound runtime state instance.

        Args:
            node_name: Identifier for the node.
            contract_path: Optional path to contract file.

        Returns:
            New ModelEventBusRuntimeState in bound state.
        """
        return cls(node_name=node_name, contract_path=contract_path, is_bound=True)


__all__ = ["ModelEventBusRuntimeState"]
