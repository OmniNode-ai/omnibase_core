"""
Contract Diff Entry Model.

Represents a single difference between two contract versions. Each entry
captures the change type (added, removed, or changed), the field path,
the old and new values, and the severity level of the change.

This model is immutable (frozen) to ensure consistency when entries are
shared across different parts of the diff processing pipeline.

Example Usage::

    from omnibase_core.models.cli.model_diff_entry import ModelDiffEntry

    # Create an entry for a changed field
    entry = ModelDiffEntry(
        change_type="changed",
        path="descriptor.timeout_ms",
        old_value=1000,
        new_value=2000,
        severity="high",
    )

    # Serialize for output
    data = entry.to_dict()
    # {"type": "changed", "path": "descriptor.timeout_ms",
    #  "severity": "high", "old": 1000, "new": 2000}

.. versionadded:: 0.6.0
    Added as part of Contract CLI Tooling (OMN-1129)
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types.type_json import JsonType


class ModelDiffEntry(BaseModel):
    """Represents a single difference between contract versions.

    Each diff entry captures one atomic change detected during contract
    comparison. Entries are immutable to ensure they can be safely shared
    and categorized without modification.

    Attributes:
        change_type: Type of change detected:

            - ``"added"``: Field exists in new but not in old
            - ``"removed"``: Field exists in old but not in new
            - ``"changed"``: Field exists in both with different values

        path: Dot-separated path to the changed field. For array elements,
            uses bracket notation (e.g., ``handlers[0].name`` or
            ``handlers[name=my_handler].timeout``).

        old_value: The value in the old contract. Will be ``None`` for
            ``added`` entries since the field didn't exist before.

        new_value: The value in the new contract. Will be ``None`` for
            ``removed`` entries since the field no longer exists.

        severity: Severity level indicating the impact of this change:

            - ``"high"``: Behavioral field change that may affect runtime
            - ``"medium"``: Version change or field removal
            - ``"low"``: Other modifications (documentation, etc.)

    Examples:
        >>> entry = ModelDiffEntry(
        ...     change_type="changed",
        ...     path="descriptor.timeout_ms",
        ...     old_value=1000,
        ...     new_value=2000,
        ...     severity="high",
        ... )
        >>> entry.path
        'descriptor.timeout_ms'
        >>> entry.to_dict()["type"]
        'changed'
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
    severity: Literal["high", "medium", "low"] = Field(
        default="low",
        description="Severity level of the change (high, medium, low)",
    )

    def to_dict(self) -> dict[str, JsonType]:
        """Convert to dictionary for JSON serialization.

        Produces a compact dictionary representation suitable for JSON or
        YAML output. Uses abbreviated key names for conciseness:

        - ``change_type`` -> ``type``
        - ``old_value`` -> ``old`` (only if not None)
        - ``new_value`` -> ``new`` (only if not None)

        Returns:
            Dictionary with keys: type, path, severity, and optionally
            old and new.

        Examples:
            >>> entry = ModelDiffEntry(
            ...     change_type="added",
            ...     path="name",
            ...     new_value="my_contract",
            ... )
            >>> entry.to_dict()
            {'type': 'added', 'path': 'name', 'severity': 'low', 'new': 'my_contract'}
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
