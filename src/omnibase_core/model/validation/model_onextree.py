"""
Pydantic models for .onextree file structure.

This module provides typed models for parsing and validating .onextree files,
replacing the previous Dict[str, Any] approach with proper type safety.
"""

from pathlib import Path
from typing import TYPE_CHECKING, cast

from pydantic import BaseModel, Field, field_validator

from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.enums.enum_onex_tree_node_type import EnumOnexTreeNodeType
from omnibase_core.exceptions import OnexError

from .model_artifact_counts import ModelArtifactCounts
from .model_onex_tree_node import ModelOnexTreeNode

if TYPE_CHECKING:
    from collections.abc import Generator

# Backward compatibility aliases
OnexTreeNode = ModelOnexTreeNode
OnexTreeNodeTypeEnum = EnumOnexTreeNodeType  # For backward compatibility
ArtifactCountsModel = ModelArtifactCounts


class ModelOnextreeRoot(BaseModel):
    """
    Root model for .onextree files.

    This represents the complete .onextree structure starting from the root directory.
    """

    name: str = Field(..., description="Name of the root directory")
    type: EnumOnexTreeNodeType = Field(
        default=EnumOnexTreeNodeType.DIRECTORY,
        description="Type of the root (should always be directory)",
    )
    children: list[ModelOnexTreeNode] = Field(
        default_factory=list,
        description="Child nodes of the root directory",
    )

    @field_validator("type")
    @classmethod
    def validate_root_type(cls, v: EnumOnexTreeNodeType) -> EnumOnexTreeNodeType:
        """Validate that root is always a directory."""
        if v != EnumOnexTreeNodeType.DIRECTORY:
            msg = "Root node must be a directory"
            raise OnexError(
                msg,
                CoreErrorCode.INVALID_PARAMETER,
            )
        return v

    def is_file(self) -> bool:
        """Check if this node is a file."""
        return self.type == EnumOnexTreeNodeType.FILE

    def is_directory(self) -> bool:
        """Check if this node is a directory."""
        return self.type == EnumOnexTreeNodeType.DIRECTORY

    def find_artifact_directories(self) -> list[tuple[Path, ModelOnexTreeNode]]:
        """
        Find all artifact directories (nodes, cli_tools, etc.) in the tree.

        Returns:
            List of (path, node) tuples for artifact directories
        """
        artifact_dirs = []
        artifact_types = {
            "nodes",
            "cli_tools",
            "runtimes",
            "adapters",
            "contracts",
            "packages",
        }

        for path, node in self.walk():
            if node.is_directory() and node.name in artifact_types:
                artifact_dirs.append((path, node))

        return artifact_dirs

    def find_versioned_artifacts(self) -> list[tuple[str, str, str, ModelOnexTreeNode]]:
        """
        Find all versioned artifacts in the tree.

        Returns:
            List of (artifact_type, artifact_name, version, node) tuples
        """
        artifacts = []

        for path, node in self.walk():
            parts = path.parts

            # Look for patterns like: omnibase/nodes/node_name/v1_0_0
            if len(parts) >= 4:
                for i in range(len(parts) - 2):
                    type_part = parts[i]

                    if type_part in {
                        "nodes",
                        "cli_tools",
                        "runtimes",
                        "adapters",
                        "contracts",
                        "packages",
                    } and i + 2 < len(parts):
                        name_part = parts[i + 1]
                        version_part = parts[i + 2]

                        if version_part.startswith("v") and node.is_directory():
                            artifacts.append(
                                (type_part, name_part, version_part, node),
                            )

        return artifacts

    def find_metadata_files(self) -> list[tuple[Path, ModelOnexTreeNode]]:
        """
        Find all metadata files (node.onex.yaml, cli_tool.yaml, etc.) in the tree.

        Returns:
            List of (path, node) tuples for metadata files
        """
        metadata_files = []
        metadata_patterns = {
            "node.onex.yaml",
            "cli_tool.yaml",
            "runtime.yaml",
            "adapter.yaml",
            "contract.yaml",
            "package.yaml",
        }

        for path, node in self.walk():
            if node.is_file() and node.name in metadata_patterns:
                metadata_files.append((path, node))

        return metadata_files

    def walk(self) -> "Generator[tuple[Path, ModelOnexTreeNode], None, None]":
        """
        Walk the entire tree yielding (path, node) tuples.

        Yields:
            Tuple of (full_path, node)
        """
        yield Path(self.name), cast("ModelOnexTreeNode", self)

        for child in self.children:
            yield from child.walk(Path(self.name))

    @classmethod
    def from_dict(cls, data: dict) -> "ModelOnextreeRoot":
        """
        Create an OnextreeRoot from a dictionary (e.g., from YAML).

        Args:
            data: Dictionary representation of the .onextree

        Returns:
            OnextreeRoot instance
        """
        return cls.model_validate(data)

    @classmethod
    def from_yaml_file(cls, file_path: str | Path) -> "ModelOnextreeRoot":
        """
        Load an OnextreeRoot from a YAML file.

        Args:
            file_path: Path to the .onextree file

        Returns:
            OnextreeRoot instance
        """
        from omnibase_core.model.core.model_generic_yaml import ModelGenericYaml
        from omnibase_core.utils.safe_yaml_loader import load_and_validate_yaml_model

        # Load and validate YAML using Pydantic model
        yaml_model = load_and_validate_yaml_model(file_path, ModelGenericYaml)
        data = yaml_model.model_dump()

        return cls.from_dict(data)


# Backward compatibility alias
OnextreeRoot = ModelOnextreeRoot
