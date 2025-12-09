"""
Effect Input Schema Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

Optional input schema for pre-execution validation.
RESERVED FOR v1.1: Minimal implementation in v1.0 (structure only, no validation).

Implements: OMN-524
"""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelEffectInputSchema"]


class ModelEffectInputSchema(BaseModel):
    """
    Optional input schema for pre-execution validation.

    RESERVED FOR v1.1: Minimal implementation in v1.0 (structure only, no validation).

    When fully implemented:
    - Effect inputs are validated against this schema before execution
    - Required fields must be present in ModelEffectInput.operation_data
    - Optional fields may be present or absent

    This enables:
    - Early failure on malformed inputs
    - Contract introspection for code generation
    - IDE autocompletion for input fields
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    required_fields: list[str] = Field(
        default_factory=list,
        description="Field names that must be present in input. Format: 'field_name' or 'nested.field'",
    )
    optional_fields: list[str] = Field(
        default_factory=list, description="Field names that may be present in input"
    )
