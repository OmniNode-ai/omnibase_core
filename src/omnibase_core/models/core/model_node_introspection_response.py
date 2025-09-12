"""
Node introspection response model for ONEX nodes.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_node_capability import EnumNodeCapability
from omnibase_core.models.core.model_contract import ModelContract
from omnibase_core.models.core.model_dependencies import ModelDependencies
from omnibase_core.models.core.model_error_codes import ModelErrorCodes
from omnibase_core.models.core.model_event_channels import ModelEventChannels
from omnibase_core.models.core.model_node_metadata_info import ModelNodeMetadataInfo
from omnibase_core.models.core.model_state_models import ModelStates


class ModelNodeIntrospectionResponse(BaseModel):
    """
    Canonical response model for ONEX node introspection.

    This is the standardized format that all ONEX nodes must return
    when called with the --introspect command.
    """

    node_metadata: ModelNodeMetadataInfo = Field(
        ...,
        description="Node metadata and identification",
    )
    contract: ModelContract = Field(
        ...,
        description="Node contract and interface specification",
    )
    state_models: ModelStates = Field(
        ...,
        description="Input and output state model specifications",
    )
    error_codes: ModelErrorCodes = Field(
        ...,
        description="Error codes and exit code mapping",
    )
    dependencies: ModelDependencies = Field(
        ...,
        description="Runtime and optional dependencies",
    )
    capabilities: list[EnumNodeCapability] = Field(
        default_factory=list,
        description="Node capabilities",
    )
    event_channels: ModelEventChannels | None = Field(
        None,
        description="Event channels this node subscribes to and publishes to",
    )
    introspection_version: str = Field(
        "1.0.0",
        description="Introspection format version",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "node_metadata": {
                    "name": "stamper_node",
                    "version": "1.0.0",
                    "description": "ONEX metadata stamper for file annotation",
                    "author": "ONEX Team",
                    "schema_version": "1.1.1",
                },
                "contract": {
                    "input_state_schema": "stamper_input.schema.json",
                    "output_state_schema": "stamper_output.schema.json",
                    "cli_interface": {
                        "entrypoint": "python -m omnibase.nodes.stamper_node.v1_0_0.node",
                        "required_args": [
                            {
                                "name": "files",
                                "type": "List[str]",
                                "required": True,
                                "description": "Files to stamp",
                            },
                        ],
                        "optional_args": [
                            {
                                "name": "--author",
                                "type": "str",
                                "required": False,
                                "description": "Author name for metadata",
                            },
                        ],
                        "exit_codes": [0, 1, 2],
                    },
                    "protocol_version": "1.1.0",
                },
                "capabilities": [
                    "supports_dry_run",
                    "supports_batch_processing",
                    "supports_event_discovery",
                ],
                "event_channels": {
                    "subscribes_to": [
                        "onex.discovery.broadcast",
                        "onex.node.health_check",
                    ],
                    "publishes_to": ["onex.discovery.response", "onex.node.status"],
                },
            },
        },
    )
