# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Contract Diff Entry Model.

Represents a single difference between contract versions.

.. versionadded:: 0.6.0
    Added as part of Contract CLI Tooling (OMN-1129)
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.type_json import JsonType


class ModelDiffEntry(BaseModel):
    """Represents a single difference between contract versions.

    Attributes:
        change_type: Type of change (added, removed, changed).
        path: Dot-separated path to the changed field.
        old_value: The value in the old contract (None for added).
        new_value: The value in the new contract (None for removed).
        severity: Severity level of the change (high, medium, low).
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    change_type: Literal["added", "removed", "changed"] = Field(
        ...,
        description="Type of change (added, removed, changed)",
    )
    path: str = Field(
        ...,
        description="Dot-separated path to the changed field",
    )
    old_value: JsonType = Field(
        default=None,
        description="The value in the old contract (None for added)",
    )
    new_value: JsonType = Field(
        default=None,
        description="The value in the new contract (None for removed)",
    )
    severity: str = Field(
        default="low",
        description="Severity level of the change (high, medium, low)",
    )

    def to_dict(self) -> dict[str, JsonType]:
        """Convert to dictionary for JSON serialization.

        Uses concise key names for output:
        - change_type -> type
        - old_value -> old (if not None)
        - new_value -> new (if not None)
        """
        result: dict[str, JsonType] = {
            "type": self.change_type,
            "path": self.path,
            "severity": self.severity,
        }
        if self.old_value is not None:
            result["old"] = self.old_value
        if self.new_value is not None:
            result["new"] = self.new_value
        return result
