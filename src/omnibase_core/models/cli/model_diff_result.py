# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Contract Diff Result Model.

Complete diff result between two contracts.

.. versionadded:: 0.6.0
    Added as part of Contract CLI Tooling (OMN-1129)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, computed_field

from omnibase_core.models.cli.model_diff_entry import ModelDiffEntry
from omnibase_core.types.type_json import JsonType


class ModelDiffResult(BaseModel):
    """Complete diff result between two contracts.

    Attributes:
        old_path: Path to the old contract file.
        new_path: Path to the new contract file.
        behavioral_changes: Changes to behavioral fields.
        added: Fields added in the new contract.
        removed: Fields removed from the old contract.
        changed: Fields with changed values.
    """

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
    )

    old_path: str = Field(
        default="",
        description="Path to the old contract file",
    )
    new_path: str = Field(
        default="",
        description="Path to the new contract file",
    )
    behavioral_changes: list[ModelDiffEntry] = Field(
        default_factory=list,
        description="Changes to behavioral fields",
    )
    added: list[ModelDiffEntry] = Field(
        default_factory=list,
        description="Fields added in the new contract",
    )
    removed: list[ModelDiffEntry] = Field(
        default_factory=list,
        description="Fields removed from the old contract",
    )
    changed: list[ModelDiffEntry] = Field(
        default_factory=list,
        description="Fields with changed values",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_changes(self) -> bool:
        """Check if any differences were detected."""
        return bool(
            self.behavioral_changes or self.added or self.removed or self.changed
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_changes(self) -> int:
        """Get total number of changes."""
        return (
            len(self.behavioral_changes)
            + len(self.added)
            + len(self.removed)
            + len(self.changed)
        )

    def to_dict(self) -> dict[str, JsonType]:
        """Convert to dictionary for JSON serialization.

        Uses custom serialization via ModelDiffEntry.to_dict() for entries.
        """
        return {
            "old_path": self.old_path,
            "new_path": self.new_path,
            "has_changes": self.has_changes,
            "total_changes": self.total_changes,
            "behavioral_changes": [e.to_dict() for e in self.behavioral_changes],
            "added": [e.to_dict() for e in self.added],
            "removed": [e.to_dict() for e in self.removed],
            "changed": [e.to_dict() for e in self.changed],
        }
