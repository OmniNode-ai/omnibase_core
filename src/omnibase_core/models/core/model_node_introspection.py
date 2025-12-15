# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:25.668084'
# description: Stamped by ToolPython
# entrypoint: python://model_node_introspection
# hash: 1709b3ea8e9130471ccbdd51d9b66cd150c007c0bac054ed1e75268484d96414
# last_modified_at: '2025-06-18T14:00:00.000000+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_node_introspection.py
# namespace: python://omnibase.model.model_node_introspection
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: 1d58424c-14a6-4b4d-b27a-0fd1baa8062c
# version: 1.0.0
# === /OmniNode:Metadata ===


"""
Node Introspection Models for ONEX.

This module defines the canonical Pydantic models for node introspection responses.
All ONEX nodes must return data conforming to these models when called with --introspect.

The introspection system enables:
- Auto-discovery of node capabilities
- Generic validation tooling
- Third-party ecosystem development
- Self-documenting node contracts
- Event-driven discovery and communication
"""

from typing import TYPE_CHECKING

from omnibase_core.enums.enum_node_capability import EnumNodeCapability
from omnibase_core.models.core.model_cli_argument import ModelCLIArgument
from omnibase_core.models.core.model_cli_command import ModelCLICommand
from omnibase_core.models.core.model_cli_interface import ModelCLIInterface
from omnibase_core.models.core.model_contract import ModelContract
from omnibase_core.models.core.model_dependencies import ModelDependencies
from omnibase_core.models.core.model_error_code import ModelErrorCode
from omnibase_core.models.core.model_error_codes import ModelErrorCodes

# Import all separated models
from omnibase_core.models.core.model_event_channels import ModelEventChannels
from omnibase_core.models.core.model_performance_profile_info import (
    ModelPerformanceProfileInfo,
)
from omnibase_core.models.core.model_state_field import ModelStateField
from omnibase_core.models.core.model_state_models import ModelStates
from omnibase_core.models.core.model_version_status import ModelVersionStatus
from omnibase_core.models.infrastructure.model_state import ModelState
from omnibase_core.models.node_metadata.model_node_metadata_info import (
    ModelNodeMetadataInfo,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

if TYPE_CHECKING:
    from omnibase_core.models.core.model_node_introspection_response import (
        ModelNodeIntrospectionResponse,
    )

# Compatibility aliases
EventChannelsModel = ModelEventChannels
CLIArgumentModel = ModelCLIArgument
CLICommandModel = ModelCLICommand
CLIInterfaceModel = ModelCLIInterface
StateFieldModel = ModelStateField
ModelStateModel = ModelState
ModelStatesModel = ModelStates
ErrorCodeModel = ModelErrorCode
ErrorCodesModel = ModelErrorCodes
DependenciesModel = ModelDependencies
VersionStatusModel = ModelVersionStatus
PerformanceProfileModel = ModelPerformanceProfileInfo
NodeModelMetadata = ModelNodeMetadataInfo
ContractModel = ModelContract
NodeCapabilityEnum = EnumNodeCapability


def create_node_introspection_response(
    node_metadata: ModelNodeMetadataInfo,
    contract: ModelContract,
    state_models: ModelStates,
    error_codes: ModelErrorCodes,
    dependencies: ModelDependencies,
    capabilities: list[EnumNodeCapability] | None = None,
    event_channels: ModelEventChannels | None = None,
    introspection_version: ModelSemVer = ModelSemVer(major=1, minor=0, patch=0),
) -> "ModelNodeIntrospectionResponse":
    """
    Factory function to create a standardized node introspection response.

    Args:
        node_metadata: Node metadata and identification
        contract: Node contract and interface specification
        state_models: Input and output state model specifications
        error_codes: Error codes and exit code mapping
        dependencies: Runtime and optional dependencies
        capabilities: Node capabilities (optional)
        event_channels: Event channels for publish/subscribe (optional)
        introspection_version: Introspection format version

    Returns:
        ModelNodeIntrospectionResponse: Standardized introspection response
    """
    from omnibase_core.models.core.model_node_introspection_response import (
        ModelNodeIntrospectionResponse,
    )

    return ModelNodeIntrospectionResponse(
        node_metadata=node_metadata,
        contract=contract,
        state_models=state_models,
        error_codes=error_codes,
        dependencies=dependencies,
        capabilities=capabilities if capabilities is not None else [],
        event_channels=event_channels,
        introspection_version=introspection_version,
    )


# Models that need rebuilding after circular imports are resolved
ModelNodeMetadataInfo.model_rebuild()
ModelVersionStatus.model_rebuild()
ModelPerformanceProfileInfo.model_rebuild()
