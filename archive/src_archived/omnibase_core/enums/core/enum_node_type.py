"""
Enum: Node Type
Domain: Core
"""

from enum import Enum


class EnumNodeType(Enum):
    """
    Enumeration for ONEX node types.

    Follows ONEX naming convention: Enum{Category}
    File naming: enum_{category}.py
    """

    COMPUTE = "COMPUTE"
    EFFECT = "EFFECT"
    REDUCER = "REDUCER"
    ORCHESTRATOR = "ORCHESTRATOR"
