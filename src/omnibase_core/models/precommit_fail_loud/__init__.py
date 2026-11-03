# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Models for the pre-commit fail-loud meta check (OMN-22357)."""

from __future__ import annotations

from omnibase_core.models.precommit_fail_loud.model_fail_loud_document import (
    ModelFailLoudDocument,
)
from omnibase_core.models.precommit_fail_loud.model_fail_loud_hook import (
    ModelFailLoudHook,
)

__all__ = ["ModelFailLoudDocument", "ModelFailLoudHook"]
