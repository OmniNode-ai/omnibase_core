#!/usr/bin/env python3
"""
RSD Ticket Metadata Model - ONEX Standards Compliant.

Strongly-typed metadata model for ticket nodes, replacing Union types.
Generated from contract: rsd_metadata_types_contract.yaml
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelTicketMetadata(BaseModel):
    """
    Strongly-typed metadata for ticket nodes.

    Replaces Dict[str, Union[str, int, float, bool]] with specific typed fields.
    This model provides type safety and validation for ticket node metadata.
    """

    text_data: Optional[str] = Field(None, description="Text-based metadata value")

    numeric_data: Optional[float] = Field(None, description="Numeric metadata value")

    boolean_data: Optional[bool] = Field(None, description="Boolean metadata value")

    integer_data: Optional[int] = Field(None, description="Integer metadata value")

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        validate_assignment = True
