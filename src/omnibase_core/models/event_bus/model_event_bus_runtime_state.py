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

    Attributes:
        node_name: Identifier for the node using this event bus binding.
            Empty string indicates unbound state.
        contract_path: Optional path to the contract YAML file that defines
            the event bus configuration. None if not using contract-based config.
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
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    node_name: str = Field(
        default="",
        description="Node identifier for the event bus binding",
        max_length=MAX_NAME_LENGTH,
    )
    contract_path: str | None = Field(
        default=None,
        description="Path to the contract YAML file defining event bus configuration",
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

    def has_contract(self) -> bool:
        """Check if a contract path is configured.

        Returns:
            True if contract_path is set, False otherwise.
        """
        return self.contract_path is not None

    def reset(self) -> None:
        """Reset state to unbound defaults.

        This clears the binding status while preserving configuration.
        """
        self.is_bound = False

    def bind(self, node_name: str, contract_path: str | None = None) -> None:
        """Bind the event bus to a node.

        Args:
            node_name: Identifier for the node.
            contract_path: Optional path to contract file.
        """
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
