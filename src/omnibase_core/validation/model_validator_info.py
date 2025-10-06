from typing import Callable, Dict, TypedDict

"""
ValidatorInfo TypedDict

TypedDict definition for validator information used in the validation CLI.

This TypedDict defines the structure for validator metadata including
the function to call, description, and expected arguments.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules
- omnibase_core.validation.* (no circular dependencies)
"""

from typing import Any, Callable, TypedDict

from .validation_utils import ValidationResult


class ValidatorInfo(TypedDict):
    """Type definition for validator information."""

    func: Callable[..., ValidationResult]
    description: str
    args: list[str]
