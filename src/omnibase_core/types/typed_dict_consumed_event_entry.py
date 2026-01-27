"""TypedDict for consumed event entry intermediate format.

Used by ModelContractBase field validator to provide strong typing
for the normalized dict format before Pydantic validates into model type.
"""

from __future__ import annotations

from typing import Required, TypedDict


class TypedDictConsumedEventEntry(TypedDict, total=False):
    """Intermediate dict format for consumed event entries.

    Matches ModelConsumedEventEntry structure for validator return typing.
    Used by normalize_consumed_events validator in ModelContractBase.

    Fields:
        event_type: Event type name or pattern (required)
        handler_function: Handler function name (optional)
    """

    event_type: Required[str]
    handler_function: str | None


__all__ = ["TypedDictConsumedEventEntry"]
