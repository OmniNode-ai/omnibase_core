#!/usr/bin/env python3
"""
Error JSON schema model for ONEX core.
"""

from typing import Dict, List

from pydantic import BaseModel, Field


class ModelErrorJsonSchema(BaseModel):
    """Strong typing for JSON schema data."""

    schema_type: str = Field(default="object", description="Schema type")
    properties: Dict[str, Dict[str, str]] = Field(
        default_factory=dict, description="Schema properties"
    )
    required_fields: List[str] = Field(
        default_factory=list, description="Required fields"
    )
    definitions: Dict[str, Dict[str, str]] = Field(
        default_factory=dict, description="Schema definitions"
    )
