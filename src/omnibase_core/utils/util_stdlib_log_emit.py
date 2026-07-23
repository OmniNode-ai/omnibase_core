# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Stdlib-only log emission for callers that must not depend on ``omnibase_core.logging``.

OMN-14960: severs the ``omnibase_core.models -> omnibase_core.logging`` edges
required by the ``core-models-no-upward`` import-linter contract
(``.importlinter``). Models are data and must not import the behavioral
structured-logging package (``omnibase_core.logging.logging_structured``);
this helper reproduces ``emit_log_event_sync``'s level mapping using only
Python's standard-library ``logging`` module, which every layer -- including
``omnibase_core.models`` -- is free to depend on (``utils`` is not a
forbidden module for ``models`` under ``core-models-no-upward``).

Message-shape change vs. ``emit_log_event_sync`` (recorded in the OMN-14960
PR body, per the "no behavior contract changes; message-shape changes are
recorded" acceptance rule): the original emits a single JSON-encoded blob
(``json.dumps({"timestamp":..., "level":..., "message":..., "context":...})``)
via ``logger.log(level, blob)``. This helper instead emits the plain
``message`` with ``context`` attached as ``extra={"onex_context": context}``,
so log level, message text, and contextual data are all preserved -- only the
wire/text shape of the emitted record differs (no JSON envelope, no
timestamp field -- the stdlib ``LogRecord`` already carries a timestamp).
"""

from __future__ import annotations

import logging
from typing import Any

_LOGGER_NAME = "omnibase"

_LEVEL_TO_STDLIB: dict[str, int] = {
    "trace": logging.DEBUG,
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
    "fatal": logging.CRITICAL,
    "success": logging.INFO,
    "unknown": logging.INFO,
}


def emit_log_event_stdlib(level: Any, message: str, context: Any = None) -> None:
    """Emit a log record via stdlib ``logging`` only (no ``omnibase_core.logging`` import).

    Args:
        level: An ``EnumLogLevel`` member (or any object exposing ``.value``
            as a lowercase level string matching ``_LEVEL_TO_STDLIB``; falls
            back to ``INFO`` for unrecognized values).
        message: Log message.
        context: Optional structured context, attached as
            ``extra={"onex_context": context}`` rather than inlined into a
            JSON-encoded message body.
    """
    level_value = getattr(level, "value", level)
    python_level = _LEVEL_TO_STDLIB.get(str(level_value).lower(), logging.INFO)
    logging.getLogger(_LOGGER_NAME).log(
        python_level, message, extra={"onex_context": context}
    )
