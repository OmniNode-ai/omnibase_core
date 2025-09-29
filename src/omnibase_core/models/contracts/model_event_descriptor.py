"""
Event Descriptor Model - ONEX Standards Compliant.

Defines event structure, schema references, and metadata
for published events in the Event Registry system.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.models.metadata.model_semver import ModelSemVer


class ModelEventDescriptor(BaseModel):
    """
    Event descriptor models with schema references.

    Defines event structure, schema references, and metadata
    for published events in the Event Registry system.
    """

    event_name: str = Field(
        ...,
        description="Unique event name identifier",
        min_length=1,
    )

    event_type: str = Field(..., description="Event type classification", min_length=1)

    schema_reference: str = Field(
        ...,
        description="Reference to event schema definition",
        min_length=1,
    )

    description: str = Field(
        ...,
        description="Human-readable event description",
        min_length=1,
    )

    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Event schema version",
    )

    payload_structure: dict[str, str] = Field(
        default_factory=dict,
        description="Event payload field definitions",
    )

    metadata_fields: list[str] = Field(
        default_factory=list,
        description="Required metadata fields",
    )

    criticality_level: str = Field(
        default="normal",
        description="Event criticality level (low, normal, high, critical)",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
