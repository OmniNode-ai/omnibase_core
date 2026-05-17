# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Projection Models - Bases for read-optimized state projections.

Provides abstract base classes and concrete models for projection management
in CQRS architectures with eventual consistency.

Version: 1.0.0
"""

from omnibase_core.enums.enum_degraded_behavior import EnumDegradedBehavior

from .model_cursor_contract import ModelCursorContract
from .model_projection_base import ModelProjectionBase
from .model_projection_contract import ModelProjectionContract
from .model_watermark import ModelProjectionWatermark

__all__ = [
    "EnumDegradedBehavior",
    "ModelCursorContract",
    "ModelProjectionBase",
    "ModelProjectionContract",
    "ModelProjectionWatermark",
]
