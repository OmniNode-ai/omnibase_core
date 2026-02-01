"""TypedDict for published event entry intermediate format.

Used by ModelContractBase field validator to provide strong typing
for the normalized dict format before Pydantic validates into model type.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictPublishedEventEntry(TypedDict):
    """Intermediate dict format for published event entries.

    Matches ModelPublishedEventEntry structure for validator return typing.
    Used by normalize_published_events validator in ModelContractBase.

    Fields:
        topic: Topic pattern for event publishing (required)
        event_type: Event type name (required)
    """

    topic: str
    event_type: str


__all__ = ["TypedDictPublishedEventEntry"]
