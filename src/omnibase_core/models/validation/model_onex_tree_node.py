"""
OnexTreeNode model.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field, field_validator

from omnibase_core.core.errors.core_errors import CoreErrorCode
from omnibase_core.enums.enum_onex_tree_node_type import EnumOnexTreeNodeType
from omnibase_core.exceptions import OnexError

if TYPE_CHECKING:
    from collections.abc import Generator


class ModelOnexTreeNode(BaseModel):
    """
    A node in the .onextree structure.

    Represents either a file or directory with optional children.
    The 'namespace' field is present for file nodes and is a canonical string generated via Namespace.from_path(path).
    """

    name: str = Field(..., description="Name of the file or directory")
    type: EnumOnexTreeNodeType = Field(..., description="Type of the node")
    namespace: str | None = Field(
        default=None,
        description="Canonical namespace for file nodes",
    )
    children: list["ModelOnexTreeNode"] | None = Field(
        default=None,
        description="Child nodes (only for directories)",
    )

    @field_validator("children")
    @classmethod
    def validate_children(
        cls,
        v: list["ModelOnexTreeNode"] | None,
        info: Any,
    ) -> list["ModelOnexTreeNode"] | None:
        """Validate that only directories can have children."""
        if info.data:
            node_type = info.data.get("type")
            if node_type == EnumOnexTreeNodeType.FILE and v is not None:
                msg = "Files cannot have children"
                raise OnexError(
                    msg,
                    CoreErrorCode.INVALID_PARAMETER,
                )
            if node_type == EnumOnexTreeNodeType.DIRECTORY and v is None:
                return []
        return v

    def is_file(self) -> bool:
        """Check if this node is a file."""
        return self.type == EnumOnexTreeNodeType.FILE

    def is_directory(self) -> bool:
        """Check if this node is a directory."""
        return self.type == EnumOnexTreeNodeType.DIRECTORY

    def find_child(self, name: str) -> Optional["ModelOnexTreeNode"]:
        """Find a direct child by name."""
        if not self.children:
            return None
        return next((child for child in self.children if child.name == name), None)

    def find_file(self, filename: str) -> Optional["ModelOnexTreeNode"]:
        """Find a file in direct children."""
        if not self.children:
            return None
        return next(
            (
                child
                for child in self.children
                if child.is_file() and child.name == filename
            ),
            None,
        )

    def find_directory(self, dirname: str) -> Optional["ModelOnexTreeNode"]:
        """Find a directory in direct children."""
        if not self.children:
            return None
        return next(
            (
                child
                for child in self.children
                if child.is_directory() and child.name == dirname
            ),
            None,
        )

    def get_path(self, root_path: Path | None = None) -> Path:
        """Get the full path of this node."""
        if root_path:
            return root_path / self.name
        return Path(self.name)

    def walk(
        self,
        path_prefix: Path | None = None,
    ) -> "Generator[tuple[Path, ModelOnexTreeNode], None, None]":
        """
        Walk the tree yielding (path, node) tuples.

        Args:
            path_prefix: Prefix to add to paths

        Yields:
            Tuple of (full_path, node)
        """
        current_path = path_prefix / self.name if path_prefix else Path(self.name)
        yield (current_path, self)
        if self.children:
            for child in self.children:
                yield from child.walk(current_path)

    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)
        if data.get("type") == EnumOnexTreeNodeType.FILE.value and "children" in data:
            data.pop("children")
        if data.get("type") == EnumOnexTreeNodeType.DIRECTORY.value:
            data["children"] = data.get("children") or []
        return data


# Compatibility aliases
OnexTreeNode = ModelOnexTreeNode
OnexTreeNodeTypeEnum = EnumOnexTreeNodeType  # For current standards
