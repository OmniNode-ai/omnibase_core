# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""No-op completion event bus stub for NodeComplianceEvidenceEffect.

Replaces the previous ``event_bus: Any = None`` + None-guard pattern in
``handler.py`` (silent DI bypass, flagged by ``check_no_fallbacks.py``).
Callers that genuinely have no bus to inject now get an explicit, typed
stub instead of an implicit ``None`` — the publish call always executes,
it just has nowhere durable to land.

Ticket: OMN-14634
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["NoOpCompletionEventBus"]


class NoOpCompletionEventBus:
    """Stateless no-op stub used when no real event bus is injected.

    Stateless and side-effect-free, so a single module-level instance in
    ``handler.py`` is safe to share across callers.
    """

    # ONEX_EXCLUDE: dict_str_any — payload is a pre-serialized completion
    # event dict; matches the duck-typed publish(topic, payload) surface
    # every real event-bus implementation in this codebase already exposes.
    def publish(self, topic: str, payload: dict[str, Any]) -> None:
        logger.info("No event bus configured — completion event logged only: %s", topic)
