# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""NodePersonalityLoggingEffect — ONEX Effect Node for personality-aware logging.

Consumes ``ModelLogEvent`` objects from an asyncio queue (internal) or from
the Kafka topic ``onex.evt.logging.event-emitted.v1``, applies routing rules
and personality rendering, dispatches to configured sinks, and emits rendered
events to ``onex.evt.logging.event-rendered.v1``.

Design invariants:
- Sink failures NEVER propagate to callers.
- ``privacy_mode: strict`` applies redaction before any rendering.
- Personality rendering never mutates ``LogEvent`` fields.
- Config live-reload supported via ``LiveConfigLoader``.

Capability: personality_logging.effect
"""

from __future__ import annotations

import asyncio
import fnmatch
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from omniclaude.nodes.node_personality_logging_effect.config_loader import (
    LiveConfigLoader,
    build_adapter_from_config,
    load_config_from_yaml,
)
from omniclaude.nodes.node_personality_logging_effect.models.model_log_event import (
    ModelLogEvent,
)
from omniclaude.nodes.node_personality_logging_effect.models.model_logging_config import (
    ModelLoggingConfig,
)
from omniclaude.nodes.node_personality_logging_effect.models.model_rendered_log import (
    ModelRenderedLog,
)
from omniclaude.nodes.node_personality_logging_effect.personality_adapter import (
    PersonalityAdapter,
    apply_redaction,
)
from omniclaude.nodes.node_personality_logging_effect.sinks.sink_json import JsonSink
from omniclaude.nodes.node_personality_logging_effect.sinks.sink_slack import SlackSink
from omniclaude.nodes.node_personality_logging_effect.sinks.sink_stdout import (
    StdoutSink,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class NodePersonalityLoggingEffect:
    """ONEX Effect Node: personality-aware structured logging.

    Accepts ``ModelLogEvent`` objects, applies routing rules,
    renders with the configured personality profile, and dispatches
    to configured sinks.

    Args:
        config: Active ``ModelLoggingConfig``. When ``config_path`` is provided
            this is ignored and the config is loaded from disk with live-reload.
        config_path: Optional path to a YAML config file. When provided,
            the node uses ``LiveConfigLoader`` to reload on file change.
    """

    def __init__(
        self,
        config: ModelLoggingConfig | None = None,
        config_path: Path | None = None,
    ) -> None:
        self._config_path = config_path
        self._loader: LiveConfigLoader | None = None
        self._queue: asyncio.Queue[ModelLogEvent] = asyncio.Queue()

        if config_path is not None:
            # Will be initialised properly in start()
            self._config = load_config_from_yaml(config_path)
        elif config is not None:
            self._config = config
        else:
            self._config = ModelLoggingConfig()

        self._adapter = build_adapter_from_config(self._config)
        self._sinks = self._build_sinks(self._config)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the node: initialise live config loader if configured."""
        if self._config_path is not None:
            self._loader = LiveConfigLoader(
                path=self._config_path,
                on_reload=self._on_config_reload,
            )
            await self._loader.start()
            self._config = self._loader.config
            self._adapter = self._loader.adapter
            self._sinks = self._build_sinks(self._config)

        logger.info(
            "NodePersonalityLoggingEffect: started (profile=%s)",
            self._config.personality_profile,
        )

    async def stop(self) -> None:
        """Stop the node: cancel live config watcher."""
        if self._loader is not None:
            await self._loader.stop()
        logger.info("NodePersonalityLoggingEffect: stopped")

    # ------------------------------------------------------------------
    # Event ingestion
    # ------------------------------------------------------------------

    async def enqueue(self, event: ModelLogEvent) -> None:
        """Enqueue a ``ModelLogEvent`` for processing.

        Args:
            event: The log event to process.
        """
        await self._queue.put(event)

    async def process_one(self, event: ModelLogEvent) -> ModelRenderedLog | None:
        """Process a single ``ModelLogEvent`` synchronously (no queue).

        This is the primary processing method. It:
        1. Applies redaction if ``privacy_mode: strict``.
        2. Resolves routing rules to determine which sinks receive the event.
        3. Renders the event via the active personality profile.
        4. Dispatches to each matched sink.

        Args:
            event: The log event to process.

        Returns:
            The ``ModelRenderedLog`` produced, or ``None`` if no sinks matched.
        """
        # Step 1: Apply redaction if strict
        if self._config.privacy_mode == "strict":
            event = apply_redaction(event)

        # Step 2: Resolve routing rules
        sink_names = self._resolve_sinks(event)
        if not sink_names:
            logger.debug(
                "NodePersonalityLoggingEffect: no sinks matched for event %s",
                event.event_name,
            )
            return None

        # Step 3: Render
        try:
            rendered = self._adapter.render(event, self._config.personality_profile)
        except KeyError:
            logger.exception(
                "NodePersonalityLoggingEffect: unknown personality profile %r, "
                "falling back to default",
                self._config.personality_profile,
            )
            rendered = self._adapter.render(event, "default")

        # Step 4: Dispatch to matched sinks
        for sink_name in sink_names:
            sink = self._sinks.get(sink_name)
            if sink is None:
                logger.warning(
                    "NodePersonalityLoggingEffect: sink %r not found", sink_name
                )
                continue
            try:
                sink.emit(rendered)
            except Exception:
                logger.exception(
                    "NodePersonalityLoggingEffect: sink %r raised unexpectedly",
                    sink_name,
                )

        return rendered

    async def drain_queue(self) -> list[ModelRenderedLog]:
        """Process all events currently in the queue.

        Returns:
            List of rendered logs for all processed events.
        """
        results: list[ModelRenderedLog] = []
        while not self._queue.empty():
            event = await self._queue.get()
            rendered = await self.process_one(event)
            if rendered is not None:
                results.append(rendered)
        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_sinks(self, event: ModelLogEvent) -> list[str]:
        """Resolve routing rules to a list of sink names for the event.

        Rules are evaluated in order; the first matching rule wins.
        If no rules are configured, the default set of sinks (stdout) is used.

        Args:
            event: The event being routed.

        Returns:
            List of sink names to dispatch to.
        """
        # Check destination_allowlist on event policy first
        allowlist = event.policy.destination_allowlist
        for rule in self._config.routing_rules:
            if fnmatch.fnmatch(event.event_name, rule.pattern):
                sinks = rule.sinks
                if allowlist:
                    sinks = [s for s in sinks if s in allowlist]
                return sinks
        # No rules matched — fall back to stdout
        default = ["stdout"]
        if allowlist:
            default = [s for s in default if s in allowlist]
        return default

    def _build_sinks(
        self,
        config: ModelLoggingConfig,
    ) -> dict[str, JsonSink | StdoutSink | SlackSink]:
        """Build sink instances from the active config."""
        sinks: dict[str, JsonSink | StdoutSink | SlackSink] = {
            "stdout": StdoutSink(),
            "json": JsonSink(path=config.json_output_path),
        }
        if config.slack_webhook_url:
            sinks["slack"] = SlackSink(config=config)
        return sinks

    def _on_config_reload(
        self,
        config: ModelLoggingConfig,
        adapter: PersonalityAdapter,
    ) -> None:
        """Callback fired by LiveConfigLoader after each successful reload."""
        self._config = config
        self._adapter = adapter
        self._sinks = self._build_sinks(config)
        logger.info(
            "NodePersonalityLoggingEffect: config reloaded (profile=%s)",
            config.personality_profile,
        )

    @property
    def config(self) -> ModelLoggingConfig:
        """Current active configuration."""
        return self._config

    @property
    def adapter(self) -> PersonalityAdapter:
        """Current active PersonalityAdapter."""
        return self._adapter


__all__ = ["NodePersonalityLoggingEffect"]
