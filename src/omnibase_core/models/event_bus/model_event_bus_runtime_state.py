# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
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


class ModelEventBusRuntimeState(BaseModel):
    """
    Serializable runtime state for event bus operations.

    This model captures the runtime state of an event bus binding, including
    the node identity, contract configuration, and binding status. It is
    designed to be lightweight and serializable for persistence or transfer.

    Note:
        This model does NOT contain threading objects (those belong in
        ListenerHandle) or dynamic bindings like registry/event_bus references.

    Empty String Semantics:
        Both ``node_name`` and ``contract_path`` use empty string to mean
        "not explicitly set" with consistent semantics:

        - **node_name**: Empty string ``""`` means "no node name bound".
          When empty, consumers should fall back to an alternative (e.g.,
          class name). Use ``has_node_name()`` to check if explicitly set.

        - **contract_path**: Empty string ``""`` OR ``None`` means "no contract
          configured". Both are treated equivalently as "not set". Use
          ``has_contract_path()`` to check if explicitly set.

        This design allows callers to use simple truthiness checks:
        ``if state.node_name:`` or ``if state.contract_path:`` to determine
        if a value was explicitly provided.

    Attributes:
        node_name: Identifier for the node using this event bus binding.
            Empty string ``""`` indicates no node name is bound; consumers
            should use a fallback (typically the class name).
        contract_path: Path to the contract YAML file that defines the event
            bus configuration. Empty string ``""`` or ``None`` both mean
            "no contract configured".
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

    node_name: str = Field(
        default="",
        description=(
            "Node identifier for the event bus binding. Empty string means "
            "'not set' and consumers should fall back to class name. Use "
            "has_node_name() to check if explicitly set."
        ),
        max_length=MAX_NAME_LENGTH,
    )
    contract_path: str | None = Field(
        default=None,
        description=(
            "Path to the contract YAML file defining event bus configuration. "
            "Both empty string and None mean 'no contract configured'. Use "
            "has_contract_path() to check if explicitly set."
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
        """Check if a node name has been explicitly set (non-empty).

        This method provides a semantic check for whether a node name was
        explicitly bound. Empty string is treated as "not set".

        Returns:
            True if node_name is a non-empty string, False otherwise.

        Example:
            >>> state = ModelEventBusRuntimeState(node_name="my_node")
            >>> state.has_node_name()
            True
            >>> state = ModelEventBusRuntimeState(node_name="")
            >>> state.has_node_name()
            False
        """
        return bool(self.node_name)

    def has_contract_path(self) -> bool:
        """Check if a contract path has been explicitly set (non-empty).

        This method provides a semantic check for whether a contract path was
        explicitly configured. Both empty string and None are treated as
        "not set" for consistency with empty string semantics.

        Note:
            This differs from ``has_contract()`` which only checks for None.
            Use this method for consistent empty-string-aware checking.

        Returns:
            True if contract_path is a non-empty string, False otherwise.

        Example:
            >>> state = ModelEventBusRuntimeState(contract_path="/path.yaml")
            >>> state.has_contract_path()
            True
            >>> state = ModelEventBusRuntimeState(contract_path="")
            >>> state.has_contract_path()
            False
            >>> state = ModelEventBusRuntimeState(contract_path=None)
            >>> state.has_contract_path()
            False
        """
        return bool(self.contract_path)

    def has_contract(self) -> bool:
        """Check if a contract path is configured (not None).

        .. deprecated::
            Use ``has_contract_path()`` instead for consistent empty-string
            semantics. This method only checks for None, not empty string.

        Returns:
            True if contract_path is not None, False otherwise.
            Note: Returns True for empty string, which may not be intended.
        """
        warnings.warn(
            "has_contract() is deprecated, use has_contract_path() instead "
            "for consistent empty-string semantics",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.contract_path is not None

    def reset(self) -> None:
        """Perform a soft unbind, preserving identity and configuration.

        This is a "soft unbind" operation that clears only the binding status
        (is_bound=False) while preserving node_name and contract_path. The
        instance retains its identity and can be rebound using bind() with
        potentially different configuration.

        Semantic Difference from bind():
            - reset(): Soft unbind - marks as unbound but keeps node_name and
              contract_path. Use when temporarily pausing operations or when
              you need to rebind with new configuration.
            - bind(): Full bind - sets node_name, contract_path, and is_bound=True.
              Use after reset() to re-establish binding, or to change configuration.

        When to Use:
            - Use reset() when temporarily pausing event bus operations
            - Use reset() before calling bind() with new configuration
            - Use create_unbound() instead when you want a completely fresh
              instance with all default values (empty node_name, None contract_path)

        Example:
            >>> state = ModelEventBusRuntimeState.create_bound("node1", "/path.yaml")
            >>> state.is_ready()
            True
            >>> state.reset()  # Soft unbind - keeps node_name="node1"
            >>> state.is_bound
            False
            >>> state.node_name  # Still preserved
            'node1'
            >>> state.bind("node2", "/new.yaml")  # Rebind with new config
            >>> state.is_ready()
            True

        See Also:
            bind(): Sets node_name, contract_path, and is_bound together.
            create_unbound(): Creates a fresh instance with all defaults.
        """
        self.is_bound = False

    def bind(self, node_name: str, contract_path: str | None = None) -> None:
        """Bind the event bus to a node with full configuration.

        This is a "full bind" operation that sets node_name, contract_path,
        and is_bound=True together. Use this to establish or re-establish
        a binding, potentially with new configuration.

        Semantic Difference from reset():
            - bind(): Full bind - sets all values and marks as bound. Use to
              establish a new binding or rebind after reset() with new config.
            - reset(): Soft unbind - only clears is_bound, preserving node_name
              and contract_path. Use when temporarily pausing operations.

        Common Patterns:
            - Initial binding: create_unbound() then bind()
            - Reconfiguration: reset() then bind() with new values
            - Direct creation: create_bound() for one-step initialization

        Args:
            node_name: Identifier for the node using this event bus binding.
                Must be a non-empty string. Use a non-empty string for a
                fully ready binding.
            contract_path: Optional path to contract YAML file. Pass None
                to clear any existing contract_path.

        Raises:
            ValueError: If node_name is empty or whitespace-only.

        Example:
            >>> state = ModelEventBusRuntimeState.create_unbound()
            >>> state.bind("my_node", "/path/to/contract.yaml")
            >>> state.is_ready()
            True
            >>> state.reset()  # Temporarily unbind
            >>> state.bind("different_node")  # Rebind with different config
            >>> state.node_name
            'different_node'

        See Also:
            reset(): Soft unbind that preserves node_name and contract_path.
            create_bound(): One-step factory for creating a bound instance.
        """
        if not node_name or not node_name.strip():
            raise ValueError(
                "node_name must be a non-empty string for binding; "
                "use reset() to unbind without clearing configuration"
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
