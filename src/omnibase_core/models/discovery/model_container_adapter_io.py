# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input/Output models for Container Adapter tool.

Convenience imports for all Container Adapter models
for current standards while following ONEX one-model-per-file standard.
"""

# Import all individual models for current standards
from omnibase_core.models.discovery.model_container_adapter_input import (
    ModelContainerAdapterInput,
)
from omnibase_core.models.discovery.model_container_adapter_output import (
    ModelContainerAdapterOutput,
)
from omnibase_core.models.discovery.model_event_registry_coordinator_input import (
    ModelEventRegistryCoordinatorInput,
)
from omnibase_core.models.discovery.model_event_registry_coordinator_output import (
    ModelEventRegistryCoordinatorOutput,
)

# Re-export for current standards
__all__ = [
    "ModelContainerAdapterInput",
    "ModelContainerAdapterOutput",
    "ModelEventRegistryCoordinatorInput",
    "ModelEventRegistryCoordinatorOutput",
]
