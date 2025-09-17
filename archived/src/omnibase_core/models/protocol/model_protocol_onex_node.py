"""Protocol for ONEX node implementations."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ProtocolOnexNode(Protocol):
    """
    Protocol for ONEX node implementations that can be loaded by the node loader.

    All ONEX nodes must implement these methods to be compatible with the
    dynamic node loading system and container orchestration.

    This protocol defines the standard interface that node_loader.py expects
    when loading and validating nodes.
    """

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """
        Execute the node's main functionality.

        Args:
            *args: Positional arguments passed to the node
            **kwargs: Keyword arguments passed to the node

        Returns:
            Result of the node execution
        """
        ...

    def get_node_config(self) -> dict[str, Any]:
        """
        Get the node's configuration information.

        Returns:
            Dictionary containing node configuration details such as
            name, version, dependencies, capabilities, etc.
        """
        ...

    def get_input_model(self) -> type[Any]:
        """
        Get the expected input model type for this node.

        Returns:
            Type class representing the expected input structure
        """
        ...

    def get_output_model(self) -> type[Any]:
        """
        Get the expected output model type for this node.

        Returns:
            Type class representing the expected output structure
        """
        ...
