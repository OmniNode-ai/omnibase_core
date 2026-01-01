# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Backward compatibility module for ModelHandlerBehaviorDescriptor.

This module was renamed to model_handler_behavior.py and the class
was renamed to ModelHandlerBehavior. This stub provides backward
compatibility for existing imports.

.. deprecated:: 0.4.0
    Use ``from omnibase_core.models.runtime.model_handler_behavior import ModelHandlerBehavior``
    instead.
"""

from omnibase_core.models.runtime.model_handler_behavior import (
    ModelHandlerBehavior,
    ModelHandlerBehaviorDescriptor,
)

__all__ = [
    "ModelHandlerBehavior",
    "ModelHandlerBehaviorDescriptor",
]
