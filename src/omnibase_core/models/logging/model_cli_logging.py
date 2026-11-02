# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Logging configuration whose lifetime is one synchronous CLI invocation."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager


@contextmanager
def cli_logging(level: int) -> Iterator[None]:
    """Use message-only stderr output, then restore the caller's logging.

    Unlike ``basicConfig(force=True)``, this leaves the caller's handlers open.
    The temporary handler must not outlive the current stderr stream when a
    runtime is called again in the same process.
    """
    root = logging.getLogger()
    previous_handlers = root.handlers[:]
    previous_level = root.level
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    for previous in previous_handlers:
        root.removeHandler(previous)
    root.addHandler(handler)
    root.setLevel(level)
    try:
        yield
    finally:
        root.removeHandler(handler)
        handler.close()
        for previous in previous_handlers:
            root.addHandler(previous)
        root.setLevel(previous_level)
