# Re-export SPI ProtocolWorkflowReducer
from omnibase_spi.protocols.core.protocol_workflow_reducer import (
    ProtocolWorkflow,
    ProtocolWorkflowReducer,
)

# Re-export SPI types
Workflow = ProtocolWorkflow  # Alias for compatibility

# Re-export SPI workflow types
__all__ = ["ProtocolWorkflow", "ProtocolWorkflowReducer", "Workflow"]
