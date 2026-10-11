# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""SlackSink — posts rendered log messages to a Slack webhook.

Features:
- Block Kit formatted payload with structured fields from LogEvent.metrics
  and a trace link.
- ``quiet_hours`` window: events are suppressed during quiet hours.
- Token-bucket rate limiter (``max_per_minute``).
- 5-minute deduplication window keyed on ``event_name + attrs hash``.

Failures are caught and logged internally; they never propagate to the caller.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import urllib.request
from datetime import UTC, datetime
from typing import Any  # any-ok: external API boundary

from omniclaude.nodes.node_personality_logging_effect.models.model_logging_config import (
    ModelLoggingConfig,
)
from omniclaude.nodes.node_personality_logging_effect.models.model_rendered_log import (
    ModelRenderedLog,
)

logger = logging.getLogger(__name__)

_DEDUP_WINDOW_SECONDS = 300  # 5 minutes


class _TokenBucket:
    """Simple token-bucket rate limiter (thread-safe for single-threaded async use)."""

    def __init__(self, max_per_minute: int) -> None:
        self._capacity = max_per_minute
        self._tokens = float(max_per_minute)
        self._last_refill = time.monotonic()
        self._refill_rate = max_per_minute / 60.0  # tokens per second

    def consume(self) -> bool:
        """Attempt to consume one token.

        Returns:
            True if a token was available (event can proceed), False if throttled.
        """
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._refill_rate)
        self._last_refill = now
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return True
        return False


class SlackSink:
    """Posts rendered log messages to a Slack webhook using Block Kit.

    Args:
        config: Active logging configuration.
    """

    def __init__(self, config: ModelLoggingConfig) -> None:
        self._config = config
        self._bucket = _TokenBucket(config.throttle.max_per_minute)
        self._dedup_cache: dict[str, float] = {}  # dedup_key → expiry timestamp

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def emit(self, rendered: ModelRenderedLog) -> None:
        """Post the rendered log event to Slack.

        Suppresses silently when:
        - No webhook URL configured
        - Quiet hours active
        - Rate limit reached
        - Deduplication hit (same event_name + attrs within 5 min)

        Sink failures (network errors, etc.) are caught and logged internally.

        Args:
            rendered: The rendered log to emit.
        """
        try:
            if not self._config.slack_webhook_url:
                return
            if self._is_quiet_hours():
                return
            if not self._bucket.consume():
                logger.debug("SlackSink: rate limit hit, suppressing event")
                return
            dedup_key = self._dedup_key(rendered)
            if self._is_duplicate(dedup_key):
                logger.debug("SlackSink: dedup hit for %s", dedup_key)
                return
            payload = self._build_payload(rendered)
            if self._post(payload):
                # Only record dedup after a successful delivery
                self._record_dedup(dedup_key)
        except Exception:
            logger.exception("SlackSink.emit failed")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _is_quiet_hours(self) -> bool:
        """Return True if current UTC hour falls within quiet-hours window."""
        qh = self._config.quiet_hours
        hour = datetime.now(UTC).hour
        if qh.start <= qh.end:
            # Simple range: e.g. 09–17
            return qh.start <= hour < qh.end
        else:
            # Wraps midnight: e.g. 22–08
            return hour >= qh.start or hour < qh.end

    @staticmethod
    def _dedup_key(rendered: ModelRenderedLog) -> str:
        """Compute deduplication key: event_name + stable attrs hash."""
        event = rendered.original_event
        attrs_bytes = json.dumps(event.attrs, sort_keys=True).encode()
        attrs_hash = hashlib.sha256(attrs_bytes).hexdigest()[:16]
        return f"{event.event_name}:{attrs_hash}"

    def _is_duplicate(self, key: str) -> bool:
        now = time.monotonic()
        expiry = self._dedup_cache.get(key)
        return expiry is not None and now < expiry

    def _record_dedup(self, key: str) -> None:
        now = time.monotonic()
        # Prune expired entries to avoid unbounded growth
        self._dedup_cache = {k: v for k, v in self._dedup_cache.items() if now < v}
        self._dedup_cache[key] = now + _DEDUP_WINDOW_SECONDS

    def _build_payload(
        self, rendered: ModelRenderedLog
    ) -> dict[str, Any]:  # ONEX_EXCLUDE: dict_str_any - external/untyped API boundary
        """Build a Slack Block Kit payload for the rendered event."""
        event = rendered.original_event
        trace = event.trace
        metrics = event.metrics

        header_text = f"*[{event.severity.upper()}]* {event.event_name}"
        body_text = rendered.rendered_message

        blocks: list[
            dict[str, Any]  # ONEX_EXCLUDE: dict_str_any - external/untyped API boundary
        ] = [  # ONEX_EXCLUDE: dict_str_any - external/untyped API boundary
            {
                "type": "header",
                "text": {"type": "plain_text", "text": header_text, "emoji": False},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": body_text},
            },
        ]

        # Metrics fields
        if metrics is not None:
            fields: list[dict[str, str]] = []
            if metrics.cpu is not None:
                fields.append({"type": "mrkdwn", "text": f"*CPU:* {metrics.cpu:.1%}"})
            if metrics.mem is not None:
                fields.append({"type": "mrkdwn", "text": f"*Mem:* {metrics.mem:.1%}"})
            if metrics.queue_depth is not None:
                fields.append(
                    {"type": "mrkdwn", "text": f"*Queue:* {metrics.queue_depth}"}
                )
            if metrics.latency_p95 is not None:
                fields.append(
                    {
                        "type": "mrkdwn",
                        "text": f"*p95 latency:* {metrics.latency_p95:.1f}ms",
                    }
                )
            if fields:
                blocks.append({"type": "section", "fields": fields})

        # Trace context
        trace_parts: list[str] = []
        if trace.correlation_id is not None:
            trace_parts.append(f"correlation_id: `{trace.correlation_id}`")
        if trace.span_id is not None:
            trace_parts.append(f"span_id: `{trace.span_id}`")
        if trace_parts:
            blocks.append(
                {
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": " | ".join(trace_parts)}],
                }
            )

        return {"blocks": blocks}

    def _post(
        self,
        payload: dict[  # any-ok: pre-existing
            str, Any
        ],  # ONEX_EXCLUDE: dict_str_any - external/untyped API boundary
    ) -> bool:  # ONEX_EXCLUDE: dict_str_any - external/untyped API boundary
        """POST the payload to the configured Slack webhook URL.

        Returns:
            True if the delivery succeeded (HTTP 200/204), False otherwise.
        """
        secret = self._config.slack_webhook_url
        if not secret:
            return False
        url = secret.get_secret_value()
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(  # noqa: S310  # nosec B310
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310  # nosec B310
            if resp.status not in (200, 204):
                logger.warning(
                    "SlackSink: unexpected HTTP %s from webhook", resp.status
                )
                return False
        return True


__all__ = ["SlackSink"]
