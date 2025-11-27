"""
Model configuration for ModelNodeIntrospectionResponse.
"""

from pydantic import ConfigDict


class ModelNodeIntrospectionResponseConfig:
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
