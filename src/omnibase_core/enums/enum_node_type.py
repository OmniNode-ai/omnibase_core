#!/usr/bin/env python3
"""
Node Type Classification Enum - ONEX Standards Compliant.

Defines the 4 node types for the RSD architecture:
- COMPUTE: Pure computation nodes
- EFFECT: Side-effect nodes with I/O operations
- REDUCER: Data aggregation and reduction nodes
- ORCHESTRATOR: Workflow coordination nodes
"""

from enum import Enum


class EnumNodeType(str, Enum):
    """
    Node type classification for 4-node RSD architecture.

    Defines the specialized node types with their functional characteristics:
    - COMPUTE: Pure computation without side effects
    - EFFECT: Side effects, I/O operations, external interactions
    - REDUCER: Data aggregation, streaming, conflict resolution
    - ORCHESTRATOR: Workflow coordination, thunk emission, event management
    """

    COMPUTE = "COMPUTE"
    EFFECT = "EFFECT"
    REDUCER = "REDUCER"
    ORCHESTRATOR = "ORCHESTRATOR"
