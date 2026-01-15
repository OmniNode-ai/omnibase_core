"""TypedDict for validator information.

Type definition for validator metadata used in validation CLI.
"""

# Import ValidationResult without circular dependency (runtime import in cli.py)
from collections.abc import Callable
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from omnibase_core.validation.validator_utils import ModelValidationResult


class TypedDictValidatorInfo(TypedDict):
    """Type definition for validator information.

    Contains validator metadata including function, description, and arguments.
    """

    func: Callable[..., "ModelValidationResult[None]"]
    description: str
    args: list[str]


__all__ = ["TypedDictValidatorInfo"]
