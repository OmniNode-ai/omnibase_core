"""
RSD Agent Request Type Enumeration - ONEX Standards Compliant.

Defines agent request types for RSD (Rapid Service Development) system.
"""

from enum import Enum


class EnumRSDAgentRequestType(str, Enum):
    """Enumeration of RSD agent request types."""

    ANALYZE = "analyze"
    IMPLEMENT = "implement"
    TEST = "test"
    REVIEW = "review"
    DEPLOY = "deploy"
    VALIDATE = "validate"
    REFACTOR = "refactor"
    DOCUMENT = "document"
