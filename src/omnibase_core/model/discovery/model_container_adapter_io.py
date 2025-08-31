"""Input/Output models for Container Adapter tool.

This module provides convenience imports for all Container Adapter models
for backward compatibility while following ONEX one-model-per-file standard.
"""

from omnibase_core.model.discovery.model_consul_event_bridge_input import (
    ModelConsulEventBridgeInput,
)
from omnibase_core.model.discovery.model_consul_event_bridge_output import (
    ModelConsulEventBridgeOutput,
)

# Import all individual models for backward compatibility
from omnibase_core.model.discovery.model_container_adapter_input import (
    ModelContainerAdapterInput,
)
from omnibase_core.model.discovery.model_container_adapter_output import (
    ModelContainerAdapterOutput,
)
from omnibase_core.model.discovery.model_event_registry_coordinator_input import (
    ModelEventRegistryCoordinatorInput,
)
from omnibase_core.model.discovery.model_event_registry_coordinator_output import (
    ModelEventRegistryCoordinatorOutput,
)

# Re-export for backward compatibility
__all__ = [
    "ModelConsulEventBridgeInput",
    "ModelConsulEventBridgeOutput",
    "ModelContainerAdapterInput",
    "ModelContainerAdapterOutput",
    "ModelEventRegistryCoordinatorInput",
    "ModelEventRegistryCoordinatorOutput",
]
