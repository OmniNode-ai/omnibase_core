"""
DuplicationInfo

Information about protocol duplications.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

from dataclasses import dataclass

from .model_protocol_info import ModelProtocolInfo


@dataclass
class ModelDuplicationInfo:
    """Information about protocol duplications."""

    signature_hash: str
    protocols: list[ModelProtocolInfo]
    duplication_type: str  # "exact", "name_conflict", "signature_match"
    recommendation: str
