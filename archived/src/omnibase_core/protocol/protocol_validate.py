# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:27.306553'
# description: Stamped by ToolPython
# entrypoint: python://protocol_validate
# hash: 88bcd387819771c90df72a41a04b454ace7a2a24a936c1523ec962441e80c78c
# last_modified_at: '2025-05-29T14:14:00.395638+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: protocol_validate.py
# namespace: python://omnibase.protocol.protocol_validate
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: a79401fb-e7c9-4265-b352-dcb2e7c29717
# version: 1.0.0
# === /OmniNode:Metadata ===


from typing import TYPE_CHECKING, Optional, Protocol

if TYPE_CHECKING:
    from omnibase_core.core.core_structured_logging import ProtocolLogger
    from omnibase_core.models.configuration.model_metadata_config import (
        ModelMetadataConfig,
    )
    from omnibase_core.models.core.model_node_metadata import NodeMetadataBlock
    from omnibase_core.models.core.model_result_cli import CLIArgsModel

from omnibase_core.models.core.model_onex_message_result import OnexResultModel
from omnibase_core.models.validation.model_validate_error import (
    ValidateMessageModel,
    ValidateResultModel,
)
from omnibase_core.protocol.protocol_cli import ProtocolCLI


class ProtocolValidate(ProtocolCLI, Protocol):
    """
    Protocol for validators that check ONEX node metadata conformance.

    Example:
        class MyValidator(ProtocolValidate):
            def validate(self, path: str, config: Optional[ModelMetadataConfig] = None) -> ValidateResultModel:
                ...
            def get_validation_errors(self) -> List[ValidateMessageModel]:
                ...
    """

    logger: "ProtocolLogger"  # Protocol-pure logger interface

    def validate_main(self, args: "CLIArgsModel") -> OnexResultModel: ...

    def validate(
        self,
        target: str,
        config: Optional["ModelMetadataConfig"] = None,
    ) -> ValidateResultModel: ...

    def get_name(self) -> str: ...

    def get_validation_errors(self) -> list[ValidateMessageModel]:
        """Get detailed validation errors from the last validation."""
        ...

    def discover_plugins(self) -> list["NodeMetadataBlock"]:
        """
        Returns a list of plugin metadata blocks supported by this validator.
        Enables dynamic test/validator scaffolding and runtime plugin contract enforcement.
        Compliant with ONEX execution model and Cursor Rule.
        See ONEX protocol spec and Cursor Rule for required fields and extension policy.
        """
        ...

    def validate_node(self, node: "NodeMetadataBlock") -> bool: ...
