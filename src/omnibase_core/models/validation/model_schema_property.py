"""
SchemaProperty model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from omnibase_core.types.type_json import JsonType, PrimitiveValue

if TYPE_CHECKING:
    from omnibase_core.models.validation.model_required_fields_model import (
        ModelRequiredFieldsModel,
    )
    from omnibase_core.models.validation.model_schema_properties_model import (
        ModelSchemaPropertiesModel,
    )


class ModelSchemaProperty(BaseModel):
    """
    Strongly typed model for a single property in a JSON schema.
    Includes common JSON Schema fields and is extensible for M1+.
    """

    type: str | None = None
    title: str | None = None
    description: str | None = None
    default: JsonType = None
    enum: list[PrimitiveValue] | None = None
    format: str | None = None
    items: ModelSchemaProperty | None = None
    properties: ModelSchemaPropertiesModel | None = None
    required: ModelRequiredFieldsModel | None = None
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")


# Forward Reference Resolution
# ============================
# This module uses TYPE_CHECKING imports to break circular dependencies with
# ModelSchemaPropertiesModel and ModelRequiredFieldsModel. Forward references
# are resolved by calling model_rebuild() at module import time.


def _rebuild_model() -> None:
    """
    Rebuild the model to resolve TYPE_CHECKING forward references.

    This function resolves forward references used by ModelSchemaProperty
    (ModelSchemaPropertiesModel, ModelRequiredFieldsModel). These are defined
    under TYPE_CHECKING to avoid circular import errors during module initialization.

    Pattern:
        - Called automatically at module import (see below)
        - Safe to call multiple times (Pydantic handles idempotently)
        - Fails gracefully if referenced modules not yet loaded

    Why This Exists:
        ModelSchemaProperty references ModelSchemaPropertiesModel and
        ModelRequiredFieldsModel, creating a circular dependency. TYPE_CHECKING
        imports break the cycle, but require explicit resolution via model_rebuild().
    """
    try:
        # Imports inject types into namespace for model_rebuild() forward reference resolution
        from .model_required_fields_model import (  # noqa: F401
            ModelRequiredFieldsModel,
        )
        from .model_schema_properties_model import (  # noqa: F401
            ModelSchemaPropertiesModel,
        )

        ModelSchemaProperty.model_rebuild()
    except ImportError:
        # Forward references will be resolved when the modules are imported
        pass


# Automatically resolve forward references on module import.
# This is the recommended pattern for self-contained modules.
_rebuild_model()
