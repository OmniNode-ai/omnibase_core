"""TypedDict for validator information.

Type definition for validator metadata used in validation CLI.
"""

# Import ValidationResult without circular dependency (runtime import in cli.py)
from typing import TYPE_CHECKING, Callable, TypedDict

if TYPE_CHECKING:
    from omnibase_core.validation.validation_utils import ValidationResult


class TypedDictValidatorInfo(TypedDict):
    """Type definition for validator information.

    Contains validator metadata including function, description, and arguments.
    """

    func: Callable[..., "ValidationResult"]
    description: str
    args: list[str]


__all__ = ["TypedDictValidatorInfo"]
