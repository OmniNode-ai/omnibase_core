# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Adapter bridging ONEX handlers to the in-memory event bus."""

from __future__ import annotations

__all__ = ["HandlerBusAdapter"]

import asyncio
import json
import logging
import time
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

logger = logging.getLogger(__name__)


class HandlerBusAdapter:
    """Wraps an ONEX handler with event bus serialization/deserialization.

    Handlers are invoked with **model.model_dump() as kwargs.
    Results are serialized to JSON and published to the output topic.
    Correlation IDs are preserved across input -> output.

    On handler error: logs the exception, sets the workflow terminal event
    to FAILED, and does NOT publish output.
    """

    def __init__(
        self,
        handler: Any,
        handler_name: str,
        input_model_cls: type,
        output_topic: str | None,
        bus: Any,  # EventBusInmemory
        on_error: Callable[[], None] | None = None,
    ) -> None:
        self.handler = handler
        self.handler_name = handler_name
        self.input_model_cls = input_model_cls
        self.output_topic = output_topic
        self.bus = bus
        self.on_error = on_error

    async def on_message(self, msg: Any) -> None:
        """Receive bus message, invoke handler, publish result."""
        # 1. Deserialize
        correlation_id: str | None = None
        try:
            payload_dict = json.loads(msg.value) if isinstance(msg.value, bytes) else {}
            correlation_id = payload_dict.get("correlation_id")
            input_model = self.input_model_cls(**payload_dict)
        except (
            Exception
        ):  # fallback-ok: bus adapter must not crash consumer on bad messages
            logger.exception(
                "HandlerBusAdapter: deserialization failed for %s (correlation_id=%s)",
                self.handler_name,
                correlation_id,
            )
            if self.on_error:
                self.on_error()
            return

        # 2. Invoke handler
        logger.info(
            "HandlerBusAdapter: invoking %s (correlation_id=%s)",
            self.handler_name,
            correlation_id,
        )
        start = time.monotonic()
        try:
            handle_method = self.handler.handle
            if asyncio.iscoroutinefunction(handle_method):
                result = await handle_method(**input_model.model_dump())
            else:
                result = handle_method(**input_model.model_dump())
        except (
            Exception
        ):  # fallback-ok: bus adapter must not crash consumer on handler errors
            elapsed = time.monotonic() - start
            logger.exception(
                "HandlerBusAdapter: %s raised after %.2fs (correlation_id=%s)",
                self.handler_name,
                elapsed,
                correlation_id,
            )
            if self.on_error:
                self.on_error()
            return

        elapsed = time.monotonic() - start
        logger.info(
            "HandlerBusAdapter: %s completed in %.2fs (correlation_id=%s)",
            self.handler_name,
            elapsed,
            correlation_id,
        )

        # 3. Publish output
        if result is None:
            return
        if not self.output_topic:
            return
        try:
            if isinstance(result, BaseModel):
                output_bytes = result.model_dump_json().encode("utf-8")
            elif isinstance(result, dict):
                output_bytes = json.dumps(result).encode("utf-8")
            else:
                raise ModelOnexError(
                    message=(
                        f"HandlerBusAdapter: handler {self.handler.__class__.__name__!r}"
                        f" returned unsupported type {type(result).__name__!r};"
                        " expected BaseModel, dict, or None"
                    ),
                    error_code=EnumCoreErrorCode.HANDLER_EXECUTION_ERROR,
                )
            await self.bus.publish(self.output_topic, None, output_bytes)
            logger.info(
                "HandlerBusAdapter: published to %s (correlation_id=%s)",
                self.output_topic,
                correlation_id,
            )
        except Exception:
            logger.exception(
                "HandlerBusAdapter: publish failed for %s -> %s (correlation_id=%s)",
                self.handler_name,
                self.output_topic,
                correlation_id,
            )
            if self.on_error:
                self.on_error()
