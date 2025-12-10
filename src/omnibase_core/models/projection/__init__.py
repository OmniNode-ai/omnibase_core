"""
Projection Models - Bases for read-optimized state projections.

Provides abstract base classes and concrete models for projection management
in CQRS architectures with eventual consistency.

Version: 1.0.0
"""

from .model_projection_base import ModelProjectionBase
from .model_watermark import ModelProjectionWatermark

__all__ = [
    "ModelProjectionBase",
    "ModelProjectionWatermark",
]
