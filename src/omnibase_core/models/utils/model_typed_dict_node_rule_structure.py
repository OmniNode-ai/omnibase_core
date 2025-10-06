"""TypedDict Node Rule Structure.

Structure for node subcontract rules.
"""

from typing import TypedDict


class TypedDictNodeRuleStructure(TypedDict):
    """Structure for node subcontract rules."""

    forbidden: list[str]
    forbidden_messages: dict[str, str]
    forbidden_suggestions: dict[str, str]
