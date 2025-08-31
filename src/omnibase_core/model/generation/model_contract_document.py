"""
Contract document model for node generation.

Provides strongly typed representation of contract.yaml files with YAML serialization.
Replaces raw dict usage throughout the contract-to-model pipeline.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator

from omnibase_core.model.core.model_schema import ModelSchema
from omnibase_core.model.core.model_semver import ModelSemVer

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

        # If it's a string, parse it
        if isinstance(v, str):
            return ModelSemVer.parse(v)

        # If it's a dict with major/minor/patch, create ModelSemVer
        if isinstance(v, dict) and all(key in v for key in ["major", "minor", "patch"]):
            return ModelSemVer(major=v["major"], minor=v["minor"], patch=v["patch"])

        msg = f"Invalid version format: {v}. Expected string, dict with major/minor/patch, or ModelSemVer"
        raise ValueError(
            msg,
        )

    def to_yaml(self) -> str:
        """Serialize to YAML format."""
        data = self.model_dump(exclude_none=True)
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "ModelContractDocument":
        """Create from YAML content."""
        data = yaml.safe_load(yaml_content)
        return cls.from_dict(data)

    @classmethod
    def from_file(cls, file_path: Path) -> "ModelContractDocument":
        """Load from contract.yaml file."""
        if not file_path.exists():
            msg = f"Contract file not found: {file_path}"
            raise FileNotFoundError(msg)

        with open(file_path) as f:
            content = f.read()

        return cls.from_yaml(content)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelContractDocument":
        """Create from dictionary data."""
        # Convert nested dictionaries to models
        input_state = ModelSchema.from_dict(data.get("input_state"))
        output_state = ModelSchema.from_dict(data.get("output_state"))
        cli_interface = ModelCliInterface.from_dict(data.get("cli_interface"))
        dependencies = ModelContractDependencies.from_dict(data.get("dependencies"))

        # Convert definitions to ModelSchema objects
        definitions = None
        if data.get("definitions"):
            definitions = {}
            for name, def_data in data["definitions"].items():
                schema_def = ModelSchema.from_dict(def_data)
                if schema_def:
                    definitions[name] = schema_def

        # Handle version fields with ModelSemVer conversion
        contract_version = data.get("contract_version", "1.0.0")
        node_version = data.get("node_version", "1.0.0")

        return cls(
            contract_version=contract_version,  # Validator will convert to ModelSemVer
            node_name=data["node_name"],
            node_version=node_version,  # Validator will convert to ModelSemVer
            input_state=input_state,
            output_state=output_state,
            definitions=definitions,
            associated_documents=data.get("associated_documents"),
            cli_interface=cli_interface,
            dependencies=dependencies,
            execution_capabilities=data.get("execution_capabilities"),
        )

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
