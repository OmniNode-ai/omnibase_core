"""
TypedDict for node rule structure.

Strongly-typed representation for node subcontract rules.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from typing import TypedDict


class TypedDictNodeRuleStructure(TypedDict):
    """Strongly-typed structure for node subcontract rules."""

    forbidden: list[str]
    forbidden_messages: dict[str, str]
    forbidden_suggestions: dict[str, str]


__all__ = ["TypedDictNodeRuleStructure"]
