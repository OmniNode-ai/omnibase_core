# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Backcompat check models (OMN-21433)."""

from omnibase_core.models.backward_compat.model_backward_compat_check_input import (
    ModelBackwardCompatCheckInput,
)
from omnibase_core.models.backward_compat.model_backward_compat_rules import (
    ModelBackwardCompatRules,
)

__all__ = ["ModelBackwardCompatCheckInput", "ModelBackwardCompatRules"]
