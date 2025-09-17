"""
Action model.

Main action model that provides the concrete implementation for all action types.
Inherits from ModelActionBase to get UUID correlation tracking, trust scores,
and service metadata required for MCP/GraphQL integration.
"""

from .model_action_base import ModelActionBase


class ModelAction(ModelActionBase):
    """
    Main action model for ONEX action execution.

    Inherits from ModelActionBase to provide:
    - UUID correlation tracking
    - Trust level validation
    - Service metadata for tool-as-a-service architecture
    - MCP/GraphQL compatibility

    This serves as the concrete implementation for action execution
    while maintaining compatibility with existing usage patterns.
    """

    pass
