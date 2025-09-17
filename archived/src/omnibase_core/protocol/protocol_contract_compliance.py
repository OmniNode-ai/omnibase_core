"""Protocol interface for contract compliance validation tools.

This protocol defines the interface that contract compliance validation tools must implement.
"""

from abc import ABC, abstractmethod

from omnibase_core.protocol.protocol_event_bus import ProtocolEventBus
from omnibase_core.protocol.protocol_file_io import ProtocolFileIO


class ProtocolContractCompliance(ABC):
    """Protocol interface for contract compliance validation operations."""

    @abstractmethod
    def __init__(
        self,
        file_io: ProtocolFileIO | None = None,
        event_bus: ProtocolEventBus | None = None,
    ):
        """Initialize the contract compliance tool.

        Args:
            file_io: File I/O protocol implementation
            event_bus: Event bus protocol implementation
        """

    @abstractmethod
    def process(self, input_state) -> any:
        """Process contract compliance validation.

        Args:
            input_state: Input state with discovered nodes and configuration

        Returns:
            Output state with validation results
        """
