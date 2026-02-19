# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
State Management Models - Abstract bases for canonical state storage.

Provides abstract base classes for version-controlled state management
in pure reducer architectures.
"""

from .model_canonical_state_base import ModelCanonicalStateBase

__all__ = [
    "ModelCanonicalStateBase",
]
