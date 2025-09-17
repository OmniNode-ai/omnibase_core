"""
Contract document model for node generation.

Provides strongly typed representation of contract.yaml files with YAML serialization.
Replaces raw dict usage throughout the contract-to-model pipeline.
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from omnibase_core.models.core.model_generic_yaml import ModelGenericYaml
from omnibase_core.models.core.model_schema import ModelSchema
from omnibase_core.models.core.model_semver import ModelSemVer
from omnibase_core.utils.safe_yaml_loader import load_yaml_content_as_model

from .model_cli_interface import ModelCliInterface
from .model_contract_dependencies import ModelContractDependencies


class ModelContractDocument(BaseModel):
    """
    Top-level contract document representation.

    Provides Pydantic validation and YAML serialization for contract.yaml files.
    Replaces raw dict usage in contract processing pipeline.
    """

    # Contract metadata
    contract_version: ModelSemVer = Field(..., description="Contract schema version")
    node_name: str = Field(..., description="Node identifier")
    node_version: ModelSemVer = Field(..., description="Node implementation version")

    # State schemas
    input_state: ModelSchema | None = Field(
        None,
        description="Input state schema definition",
    )
    output_state: ModelSchema | None = Field(
        None,
        description="Output state schema definition",
    )

    # Schema definitions for $ref resolution
    definitions: dict[str, ModelSchema] | None = Field(
        None,
        description="Reusable schema definitions",
    )

    # Optional components
    associated_documents: dict[str, Any] | None = Field(
        None,
        description="Associated configuration documents",
    )
    cli_interface: ModelCliInterface | None = Field(
        None,
        description="CLI interface definition",
    )

    # NEW: Dependency injection specification
    dependencies: ModelContractDependencies | None = Field(
        None,
        description="Dependency injection specification",
    )

    # Additional contract properties
    execution_capabilities: dict[str, Any] | None = Field(
        None,
        description="Node execution capabilities",
    )

    @field_validator("node_name")
    @classmethod
    def validate_node_name(cls, v):
        """Validate node name format."""
        if not v or not isinstance(v, str):
            msg = "node_name must be a non-empty string"
            raise ValueError(msg)
        if not v.replace("_", "").replace("-", "").isalnum():
            msg = "node_name must contain only alphanumeric characters, hyphens, and underscores"
            raise ValueError(
                msg,
            )
        return v

    @field_validator("node_version", "contract_version", mode="before")
    @classmethod
    def validate_version_fields(cls, v):
        """Validate and convert version fields to ModelSemVer."""
        if v is None:
            msg = "Version field cannot be None"
            raise ValueError(msg)

        # If it's already a ModelSemVer, return as-is
        if isinstance(v, ModelSemVer):
            return v

        # If it's a string, parse it using ONEX-compliant function
        if isinstance(v, str):
            from omnibase_core.models.core.model_semver import parse_semver_from_string

            return parse_semver_from_string(v)

        # If it's a dict with major/minor/patch, create ModelSemVer
        if isinstance(v, dict) and all(key in v for key in ["major", "minor", "patch"]):
            return ModelSemVer(major=v["major"], minor=v["minor"], patch=v["patch"])

        msg = f"Invalid version format: {v}. Expected string, dict with major/minor/patch, or ModelSemVer"
        raise ValueError(
            msg,
        )

    def to_yaml(self) -> str:
        """Serialize to YAML format."""
        from omnibase_core.utils.safe_yaml_loader import (
            serialize_pydantic_model_to_yaml,
        )

        return serialize_pydantic_model_to_yaml(
            self,
            exclude_none=True,
            default_flow_style=False,
            sort_keys=False,
        )

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "ModelContractDocument":
        """
        Create contract model from YAML content with proper enum handling.

        Args:
            yaml_content: YAML string representation

        Returns:
            ModelContractDocument: Validated contract model instance
        """
        import yaml
        from pydantic import ValidationError

        try:
            # Parse YAML directly without recursion
            yaml_data = yaml.safe_load(yaml_content)
            if yaml_data is None:
                yaml_data = {}

            # Validate with Pydantic model directly - avoids from_yaml recursion
            return cls.model_validate(yaml_data)

        except ValidationError as e:
            raise ValueError(f"Contract validation failed: {e}") from e
        except yaml.YAMLError as e:
            raise ValueError(f"YAML parsing error: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to load contract YAML: {e}") from e

    @classmethod
    def from_file(cls, file_path: Path) -> "ModelContractDocument":
        """Load from contract.yaml file."""
        if not file_path.exists():
            msg = f"Contract file not found: {file_path}"
            raise FileNotFoundError(msg)

        with open(file_path) as f:
            content = f.read()

        return cls.from_yaml(content)

    # ONEX COMPLIANCE: Removed from_dict() factory method anti-pattern
    # Use model_validate() for deserialization with proper Pydantic validation

    def save_to_file(self, file_path: Path) -> None:
        """Save to contract.yaml file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            f.write(self.to_yaml())

    def has_unresolved_refs(self) -> bool:
        """Check if contract contains unresolved $ref references."""
        # Check input state
        if self.input_state and not self.input_state.is_resolved():
            return True

        # Check output state
        if self.output_state and not self.output_state.is_resolved():
            return True

        # Check definitions
        if self.definitions:
            for definition in self.definitions.values():
                if not definition.is_resolved():
                    return True

        return False

    def get_node_class_name(self) -> str:
        """Get PascalCase class name from node_name."""
        return "".join(
            word.capitalize() for word in self.node_name.replace("-", "_").split("_")
        )

    def get_node_id(self) -> str:
        """Get snake_case node ID from node_name."""
        return self.node_name.replace("-", "_").lower()

    def get_node_id_upper(self) -> str:
        """Get UPPER_CASE node ID from node_name."""
        return self.get_node_id().upper()
