# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Hook-writes check models (OMN-21498)."""

from omnibase_core.models.hook_writes.model_hook_writes_document import (
    ModelHookWritesDocument,
)
from omnibase_core.models.hook_writes.model_hook_writes_hook import ModelHookWritesHook

__all__ = ["ModelHookWritesDocument", "ModelHookWritesHook"]
