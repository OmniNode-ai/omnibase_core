"""
Custom parameters models.

Provides typed models for custom action parameters,
replacing dict[str, Any] patterns in action payload models.
"""

from pydantic import BaseModel, Field


class ModelCustomParameters(BaseModel):
    """
    Typed model for custom action parameters.

    Replaces dict[str, Any] custom_parameters field in ModelCustomActionPayload.
    """

    # Common string parameters
    string_params: dict[str, str] = Field(
        default_factory=dict,
        description="String parameters",
    )
    # Integer parameters
    int_params: dict[str, int] = Field(
        default_factory=dict,
        description="Integer parameters",
    )
    # Float parameters
    float_params: dict[str, float] = Field(
        default_factory=dict,
        description="Float parameters",
    )
    # Boolean parameters
    bool_params: dict[str, bool] = Field(
        default_factory=dict,
        description="Boolean parameters",
    )
    # List parameters
    list_params: dict[str, list[str]] = Field(
        default_factory=dict,
        description="List string parameters",
    )

    def get_string(self, key: str, default: str = "") -> str:
        """Get a string parameter."""
        return self.string_params.get(key, default)

    def get_int(self, key: str, default: int = 0) -> int:
        """Get an integer parameter."""
        return self.int_params.get(key, default)

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get a float parameter."""
        return self.float_params.get(key, default)

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean parameter."""
        return self.bool_params.get(key, default)

    def get_list(self, key: str) -> list[str]:
        """Get a list parameter."""
        return self.list_params.get(key, [])

    def set_string(self, key: str, value: str) -> None:
        """Set a string parameter."""
        self.string_params[key] = value

    def set_int(self, key: str, value: int) -> None:
        """Set an integer parameter."""
        self.int_params[key] = value

    def set_float(self, key: str, value: float) -> None:
        """Set a float parameter."""
        self.float_params[key] = value

    def set_bool(self, key: str, value: bool) -> None:
        """Set a boolean parameter."""
        self.bool_params[key] = value

    def set_list(self, key: str, value: list[str]) -> None:
        """Set a list parameter."""
        self.list_params[key] = value


__all__ = ["ModelCustomParameters"]
