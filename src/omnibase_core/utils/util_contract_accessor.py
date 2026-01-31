"""Contract data accessor utilities.

Provides type-safe access to contract data attributes, supporting both
Pydantic model instances and raw dict contracts from YAML parsing.
"""

from __future__ import annotations

from typing import Any


def get_contract_attr(obj: object, name: str, default: Any = None) -> Any:
    """
    Get attribute from contract data, supporting both Pydantic models and dicts.

    Args:
        obj: The contract data object (Pydantic model or dict).
        name: The attribute/key name to retrieve.
        default: Default value if attribute not found.

    Returns:
        The attribute value or default if not found.

    Example:
        >>> get_contract_attr(contract_data, "handler_routing")
        >>> get_contract_attr(contract_data, "protocol_dependencies", [])
    """
    # Check dict first to avoid triggering __getattr__ on dict-like objects
    if isinstance(obj, dict):
        return obj.get(name, default)
    # Fall back to attribute access for Pydantic models and other objects
    if hasattr(obj, name):
        return getattr(obj, name, default)
    return default


def has_contract_attr(obj: object, name: str) -> bool:
    """
    Check if contract data has an attribute.

    Args:
        obj: The contract data object (Pydantic model or dict).
        name: The attribute/key name to check.

    Returns:
        True if attribute exists (and is not None for dicts).
    """
    # Check dict first to avoid triggering __getattr__ on dict-like objects
    if isinstance(obj, dict):
        return name in obj and obj[name] is not None
    # Fall back to attribute access for Pydantic models and other objects
    if hasattr(obj, name):
        return getattr(obj, name, None) is not None
    return False


__all__ = ["get_contract_attr", "has_contract_attr"]
