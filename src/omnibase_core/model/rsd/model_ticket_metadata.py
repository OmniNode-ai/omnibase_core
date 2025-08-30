#!/usr/bin/env python3
"""
RSD Ticket Metadata Model - ONEX Standards Compliant.

Strongly-typed metadata model for ticket nodes, replacing Union types.
Generated from contract: rsd_metadata_types_contract.yaml
"""


from pydantic import BaseModel, Field


class ModelTicketMetadata(BaseModel):
    """
    Strongly-typed metadata for ticket nodes.

    Replaces Dict[str, Union[str, int, float, bool]] with specific typed fields.
    This model provides type safety and validation for ticket node metadata.
    """

    text_data: str | None = Field(None, description="Text-based metadata value")

    numeric_data: float | None = Field(None, description="Numeric metadata value")

    boolean_data: bool | None = Field(None, description="Boolean metadata value")

    integer_data: int | None = Field(None, description="Integer metadata value")

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        validate_assignment = True
