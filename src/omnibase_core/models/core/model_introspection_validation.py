from pydantic import Field

"""
Model for validation information in introspection metadata.
"""

from pydantic import BaseModel

from omnibase_core.models.core.model_introspection_validation_config import (
    ModelIntrospectionValidationConfig,
)


class ModelIntrospectionValidation(BaseModel):
    """Validation information for introspection metadata."""

    is_modern: bool = Field(description="Whether tool follows modern patterns")
    has_modern_patterns: bool = Field(default=True, description="Has modern patterns")
    cli_discoverable: bool = Field(default=True, description="Is CLI discoverable")
    passes_standards: bool = Field(description="Passes standards compliance")
