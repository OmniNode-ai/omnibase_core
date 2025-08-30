# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T12:36:25.721376'
# description: Stamped by ToolPython
# entrypoint: python://model_state_contract
# hash: 85c7b313c8471771c2f9e8393ce353a391ee62b074680b91b15befcd9cb63ba3
# last_modified_at: '2025-05-29T14:13:58.941561+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_state_contract.py
# namespace: python://omnibase.model.model_state_contract
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: 09d6280a-827e-4838-a874-d52e17c69c17
# version: 1.0.0
# === /OmniNode:Metadata ===


"""
Pydantic model for ONEX state contracts.

This module defines the canonical structure for state contract files (contract.yaml)
that define the input/output interface for ONEX nodes. All contract files should
follow this structure for consistency and validation.

Schema Version: 1.0.0
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator

from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.exceptions import OnexError
from omnibase_core.model.core.model_examples import ModelExamples

from .model_error_state import ModelErrorState
from .model_generic_metadata import ModelGenericMetadata
from .model_state_schema import ModelStateSchema

# Backward compatibility aliases
StateSchemaModel = ModelStateSchema
ErrorModelState = ModelErrorState

# Current schema version for state contracts
STATE_CONTRACT_SCHEMA_VERSION = "1.0.0"


class ModelStateContract(BaseModel):
    """
    Canonical Pydantic model for ONEX state contracts.

    This model defines the structure that all contract.yaml files should follow.
    It provides validation, type safety, and consistency across the ONEX ecosystem.

    Schema Version: 1.0.0

    Fields:
        contract_version: Version of the contract schema
        node_name: Name of the node this contract belongs to
        node_version: Version of the node
        contract_name: Optional name for the contract
        contract_description: Human-readable description of the contract
        input_state: Definition of the input state structure
        output_state: Definition of the output state structure
        error_state: Optional definition of error state structure
        examples: Optional examples of valid input/output
        metadata: Optional additional metadata
    """

    # Core contract metadata
    contract_version: str = Field(
        default=STATE_CONTRACT_SCHEMA_VERSION,
        description="Version of the contract schema",
        json_schema_extra={"example": "1.0.0"},
    )

    node_name: str = Field(
        ...,
        description="Name of the node this contract belongs to",
        json_schema_extra={"example": "cli_node"},
    )

    node_version: str = Field(
        default="1.0.0",
        description="Version of the node",
        json_schema_extra={"example": "1.0.0"},
    )

    contract_name: Optional[str] = Field(
        default=None,
        description="Optional name for the contract",
        json_schema_extra={"example": "cli_node_contract"},
    )

    contract_description: str = Field(
        ...,
        description="Human-readable description of the contract",
        json_schema_extra={"example": "State contract for CLI node command routing"},
    )

    # State definitions
    input_state: ModelStateSchema = Field(
        ..., description="Definition of the input state structure"
    )

    output_state: ModelStateSchema = Field(
        ..., description="Definition of the output state structure"
    )

    error_state: Optional[ModelErrorState] = Field(
        default=None, description="Optional definition of error state structure"
    )

    # Examples and metadata
    examples: Optional[ModelExamples] = Field(
        default=None,
        description="Optional examples of valid input/output",
        json_schema_extra={
            "example": {
                "valid_input": {"version": "1.0.0", "command": "version"},
                "valid_output": {
                    "version": "1.0.0",
                    "status": "success",
                    "message": "Version 1.0.0",
                },
            }
        },
    )

    metadata: Optional[ModelGenericMetadata] = Field(
        default=None, description="Optional additional metadata"
    )

    # Optional provenance/audit fields (for stamped contract.yaml files)
    hash: Optional[str] = Field(
        default=None,
        description="Optional hash of the contract file for provenance/audit",
        json_schema_extra={
            "example": "406d07a5a0377549a710ae4855b7f98fd009f866d701575e4b825ed5f282aae9"
        },
    )
    last_modified_at: Optional[str] = Field(
        default=None,
        description="Optional last modified timestamp for the contract file",
        json_schema_extra={"example": "2025-05-30T13:04:27.518784Z"},
    )

    @field_validator("contract_version")
    @classmethod
    def validate_contract_version(cls, v: str) -> str:
        """Validate that contract version follows semantic versioning."""
        import re

        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise OnexError(
                CoreErrorCode.VALIDATION_ERROR,
                f"Contract version must follow semantic versioning (x.y.z), got: {v}",
            )
        return v

    @field_validator("node_version")
    @classmethod
    def validate_node_version(cls, v: str) -> str:
        """Validate that node version follows semantic versioning."""
        import re

        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise OnexError(
                CoreErrorCode.VALIDATION_ERROR,
                f"Node version must follow semantic versioning (x.y.z), got: {v}",
            )
        return v

    @field_validator("node_name")
    @classmethod
    def validate_node_name(cls, v: str) -> str:
        """Validate that node name follows naming conventions."""
        if not v or not v.strip():
            raise OnexError(CoreErrorCode.VALIDATION_ERROR, "Node name cannot be empty")

        # Check for valid node name pattern (lowercase, underscores)
        import re

        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise OnexError(
                CoreErrorCode.VALIDATION_ERROR,
                f"Node name must follow pattern: lowercase, underscores. Got: {v}",
            )
        return v

    def to_yaml_dict(self) -> Dict[str, Any]:
        """
        Convert the model to a dictionary suitable for YAML serialization.

        This method ensures that the output follows the expected contract.yaml
        structure and excludes None values for cleaner output.

        Returns:
            Dictionary representation suitable for YAML serialization
        """
        data = self.model_dump(exclude_none=True)

        # Ensure contract_version is at the top
        ordered_data = {"contract_version": data.pop("contract_version")}
        ordered_data.update(data)

        return ordered_data

    @classmethod
    def from_yaml_dict(cls, data: Dict[str, Any]) -> "ModelStateContract":
        """
        Create a ModelStateContract from a dictionary loaded from YAML.

        This method handles various legacy formats and normalizes them
        to the canonical structure.

        Args:
            data: Dictionary loaded from YAML

        Returns:
            ModelStateContract instance

        Raises:
            OnexError: If the data cannot be parsed or validated
        """
        try:
            # Handle legacy field names
            if "contract_schema_version" in data:
                data["contract_version"] = data.pop("contract_schema_version")

            # Ensure required fields have defaults if missing
            if "contract_version" not in data:
                data["contract_version"] = STATE_CONTRACT_SCHEMA_VERSION

            if "node_version" not in data:
                data["node_version"] = "1.0.0"

            return cls(**data)

        except Exception as e:
            raise OnexError(
                CoreErrorCode.VALIDATION_ERROR, f"Failed to parse state contract: {e}"
            ) from e


# Convenience function for loading contracts from files
def load_state_contract_from_file(file_path: str) -> ModelStateContract:
    """
    Load and validate a state contract from a YAML file.

    Args:
        file_path: Path to the contract.yaml file

    Returns:
        ModelStateContract instance

    Raises:
        OnexError: If the file cannot be loaded or validated
    """
    from pathlib import Path

    import yaml

    try:
        path = Path(file_path)
        if not path.exists():
            raise OnexError(
                CoreErrorCode.FILE_NOT_FOUND, f"Contract file not found: {file_path}"
            )

        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not data:
            raise OnexError(
                CoreErrorCode.VALIDATION_ERROR, f"Contract file is empty: {file_path}"
            )

        return ModelStateContract.from_yaml_dict(data)

    except yaml.YAMLError as e:
        raise OnexError(
            CoreErrorCode.VALIDATION_ERROR, f"Failed to parse YAML in {file_path}: {e}"
        ) from e
    except Exception as e:
        raise OnexError(
            CoreErrorCode.VALIDATION_ERROR,
            f"Failed to load contract from {file_path}: {e}",
        ) from e
