"""
Connection parse result models.

This module now imports from separated model files for better organization
and compliance with one-model-per-file naming conventions.
"""

from .model_latency_profile import ModelLatencyProfile

# Import separated models
from .model_parsed_connection_info import ModelParsedConnectionInfo
from .model_pool_recommendations import ModelPoolRecommendations

# Compatibility aliases
ParsedConnectionInfo = ModelParsedConnectionInfo
PoolRecommendations = ModelPoolRecommendations
LatencyProfile = ModelLatencyProfile

# Re-export
__all__ = [
    "ModelLatencyProfile",
    "ModelParsedConnectionInfo",
    "ModelPoolRecommendations",
]
