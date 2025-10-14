"""
Reference Info Model for ONEX Contract Generation.

Structured data for reference resolution in JSON Schema $ref references.
"""

from dataclasses import dataclass


@dataclass
class ModelRefInfo:
    """Structured data for reference resolution."""

    file_path: str
    type_name: str
    is_internal: bool = False
    is_subcontract: bool = False
