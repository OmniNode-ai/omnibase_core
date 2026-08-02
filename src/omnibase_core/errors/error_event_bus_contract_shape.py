# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Event Bus Contract Shape Error.

Typed exception raised when an event_bus contract block uses an unknown shape
or omits required fields for a recognized shape. Distinct from generic
ValueError so callers can branch on parser-shape errors without false positives
from downstream validation failures.
"""


class EventBusContractShapeError(ValueError):
    """Raised when an event_bus contract block uses an unrecognized shape.

    The parser supports two shapes:

    1. Classic: ``event_bus.subscribe_topics`` is a ``list[str]``.
    2. Nested: ``event_bus.subscribe`` is a ``list[dict]`` where each dict has
       a required ``topic`` field.

    Any other shape (a recognized shape missing required fields, or the removed
    ``consumer_group`` key — see OMN-15639) raises this error so the contract author
    sees a loud failure instead of a silent skip.
    """


__all__ = ["EventBusContractShapeError"]
