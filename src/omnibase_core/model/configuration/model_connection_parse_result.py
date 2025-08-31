"""
Connection parse result models.

This module now imports from separated model files for better organization
and compliance with one-model-per-file naming conventions.
"""

from .model_latency_profile import ModelLatencyProfile

# Import separated models
from .model_parsed_connection_info import ModelParsedConnectionInfo
from .model_pool_recommendations import ModelPoolRecommendations

# Backward compatibility aliases
ParsedConnectionInfo = ModelParsedConnectionInfo
PoolRecommendations = ModelPoolRecommendations
LatencyProfile = ModelLatencyProfile

# Re-export for backward compatibility
__all__ = [
    "LatencyProfile",
    "ModelLatencyProfile",
    "ModelParsedConnectionInfo",
    "ModelPoolRecommendations",
    # Backward compatibility
    "ParsedConnectionInfo",
    "PoolRecommendations",
]
