# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pydantic import ConfigDict

from omnibase_core.models.events.model_content_updated_event import ModelContentPayload
from omnibase_core.models.events.model_runtime_event_base import ModelRuntimeEventBase

__all__ = ["ModelContentUpdatedEvent"]


class ModelContentUpdatedEvent(ModelRuntimeEventBase):
    model_config = ConfigDict(frozen=True, extra="forbid", validate_assignment=False)
    payload: ModelContentPayload
