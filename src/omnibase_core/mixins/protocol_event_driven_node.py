from typing import Protocol

"""
Protocol defining the interface for event-driven nodes.

This protocol can be used for type checking and documentation
of the expected interface for event-driven nodes.
"""


class ProtocolEventDrivenNode(Protocol):
    """
    Protocol defining the interface for event-driven nodes.

    This protocol can be used for type checking and documentation
    of the expected interface for event-driven nodes.
    """

    def get_node_id(self) -> str:
        """Get the unique identifier for this node."""
        ...

    def get_node_name(self) -> str:
        """Get the name of this node."""
        ...

    def get_node_version(self) -> str:
        """Get the version of this node."""
        ...
