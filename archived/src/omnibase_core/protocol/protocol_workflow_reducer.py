# Re-export SPI ProtocolWorkflowReducer
from omnibase_spi.protocols.core.protocol_workflow_reducer import (
    ProtocolWorkflow,
    ProtocolWorkflowReducer,
)

# Re-export SPI types
Workflow = ProtocolWorkflow  # Alias for current standards

# Re-export SPI workflow types
__all__ = ["ProtocolWorkflow", "ProtocolWorkflowReducer", "Workflow"]
