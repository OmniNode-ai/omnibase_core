# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Effect template context model for dynamic template resolution.

This module provides ModelEffectTemplateContext, an explicitly dynamic model for
effect operation template resolution. Unlike ModelEffectInputData (which is strict),
this model accepts arbitrary key-value pairs for use in template placeholders.

Design Rationale:
    There are two distinct concepts in effect processing:
    1. Effect input contract (ModelEffectInputData) - stable, validated, audited
    2. Template context (ModelEffectTemplateContext) - ad hoc, derived, can include anything

    Modeling them separately preserves type safety for contracts while enabling
    flexible template resolution.

Thread Safety:
    ModelEffectTemplateContext instances are frozen (frozen=True) after creation,
    meaning the `data` attribute cannot be reassigned. However, the underlying dict
    is mutable - if external code retains a reference to the input dict, it could
    mutate the contents. The `from_dict()` factory method deep-copies input to
    prevent this issue. For thread safety, prefer using `from_dict()` over direct
    construction, or ensure no external references to the input dict are retained.

Note:
    This is different from ModelTemplateContext in models/core/, which is for
    Jinja-style template rendering in node generation.

See Also:
    - ModelEffectInputData: Strict contract model for effect inputs
    - MixinEffectExecution: Uses this for template resolution
"""

import copy
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.decorators.allow_dict_any import allow_dict_any

__all__ = ["ModelEffectTemplateContext"]


@allow_dict_any(
    reason="Template context intentionally accepts arbitrary key-value pairs for "
    "dynamic template placeholder resolution (${input.field}). This is the explicit "
    "'grab bag' pattern for template contexts, separate from strict contracts."
)
class ModelEffectTemplateContext(BaseModel):
    """Dynamic context for effect template resolution.

    This model explicitly accepts arbitrary key-value pairs for template
    placeholder substitution. Use this when you need flexible, untyped
    data for template resolution (e.g., ${input.user_id}, ${input.filename}).

    For strict, validated effect input contracts, use ModelEffectInputData.

    Attributes:
        data: Arbitrary key-value pairs for template resolution.
            Keys are accessed via dot notation in templates (e.g., ${input.user_id}).

    Example:
        Template resolution context::

            context = ModelEffectTemplateContext(
                data={
                    "user_id": "123",
                    "filename": "output.json",
                    "operations": [...],
                }
            )

        Accessing in templates::

            # Template: "https://api.example.com/users/${input.user_id}"
            # Resolves to: "https://api.example.com/users/123"

    See Also:
        - ModelEffectInputData: Strict contract model
        - MixinEffectExecution._resolve_io_config: Template resolution
    """

    model_config = ConfigDict(frozen=True, from_attributes=True)

    data: dict[str, Any] = Field(  # ONEX_EXCLUDE: dict_str_any - intentional grab bag
        default_factory=dict,
        description="Arbitrary key-value pairs for template resolution",
    )

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the context data.

        Args:
            key: Key to look up in the data dict.
            default: Default value if key not found.

        Returns:
            The value for the key, or default if not found.
        """
        return self.data.get(key, default)

    def __getitem__(self, key: str) -> Any:
        """Get a value from the context data using bracket notation.

        Args:
            key: Key to look up in the data dict.

        Returns:
            The value for the key.

        Raises:
            KeyError: If key not found.
        """
        return self.data[key]

    def __contains__(self, key: str) -> bool:
        """Check if key exists in context data.

        Args:
            key: Key to check.

        Returns:
            True if key exists in data.
        """
        return key in self.data

    @classmethod
    @allow_dict_any(
        reason="Factory method accepting arbitrary dict for template context"
    )
    def from_dict(cls, data: dict[str, Any]) -> "ModelEffectTemplateContext":
        """Create a ModelEffectTemplateContext from a dictionary.

        The input dictionary is deep-copied to prevent external mutations
        from affecting the context after creation.

        Args:
            data: Dictionary to wrap as template context.

        Returns:
            ModelEffectTemplateContext wrapping a deep copy of the data.
        """
        return cls(data=copy.deepcopy(data))

    @allow_dict_any(reason="Serialization method returning template context data")
    def to_dict(self) -> dict[str, Any]:
        """Get the underlying data dictionary.

        Returns:
            The data dictionary.
        """
        return self.data
