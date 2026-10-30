# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Planted: a handler core that takes the event envelope type."""

from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope


class HandlerEnveloped:
    def handle(self, request: ModelEventEnvelope) -> None:
        return None
