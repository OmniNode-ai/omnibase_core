"""
Action Category Model.

Defines the categories of node actions as a proper Pydantic model.
"""

from typing import ClassVar

from pydantic import BaseModel, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class ModelActionCategory(BaseModel):
    """
    Action category model with validation and metadata.

    Replaces simple string enum with structured category definitions.
    """

    name: str = Field(default=..., description="Category name identifier")
    display_name: str = Field(default=..., description="Human-readable category name")
    description: str = Field(
        default=...,
        description="Description of what this category represents",
    )

    # Class-level registry for predefined categories
    _registry: ClassVar[dict[str, "ModelActionCategory"]] = {}

    @field_validator("name")
    @classmethod
    def validate_name_format(cls, v: str) -> str:
        """Validate category name follows naming conventions."""
        if not v.islower():
            msg = "Category name must be lowercase"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        if not v.replace("_", "").isalnum():
            msg = "Category name must contain only letters, numbers, and underscores"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    def __str__(self) -> str:
        """String representation returns the category name."""
        return self.name

    def __eq__(self, other: object) -> bool:
        """Equality based on category name."""
        if isinstance(other, ModelActionCategory):
            return self.name == other.name
        if isinstance(other, str):
            return self.name == other
        return False

    def __hash__(self) -> int:
        """Return hash value for use in sets and as dict keys.

        Returns:
            int: Hash computed from the category name.
        """
        return hash(self.name)

    @classmethod
    def register(cls, category: "ModelActionCategory") -> None:
        """Register a category in the global registry."""
        cls._registry[category.name] = category

    @classmethod
    def get_by_name(cls, name: str) -> "ModelActionCategory":
        """Get category by name from registry."""
        category = cls._registry.get(name)
        if not category:
            msg = f"Unknown category: {name}"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return category

    @classmethod
    def get_all_registered(cls) -> list["ModelActionCategory"]:
        """Get all registered categories."""
        return list(cls._registry.values())


try:
    ModelActionCategory.model_rebuild()
except Exception:  # catch-all-ok: circular import protection during model rebuild
    pass
