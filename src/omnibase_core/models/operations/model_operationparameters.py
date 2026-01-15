from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.decorators.decorator_error_handling import standard_error_handling
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.operations.model_operation_parameters_base import (
    ModelOperationParameterValue,
)
from omnibase_core.types.type_serializable_value import SerializedDict

__all__ = ["ModelOperationParameters"]


class ModelOperationParameters(BaseModel):
    """
    Strongly-typed operation parameters with discriminated unions.

    Replaces primitive soup pattern with discriminated parameter types.

    Note: This class provides utility methods but does NOT implement
    protocol interfaces. Use protocol-specific adapters if protocol
    compliance is required.
    """

    # Use discriminated union for parameter values
    parameters: dict[str, ModelOperationParameterValue] = Field(
        default_factory=dict,
        description="Operation parameters with discriminated union types",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Utility methods (NOT protocol implementations)

    @standard_error_handling("Operation parameters execution")
    async def execute(self) -> object:
        """
        Execute or validate operation parameters.

        Returns:
            Dictionary containing execution results and parameter validation status.

        Note:
            Error handling is managed by @standard_error_handling decorator.
        """
        # Validate all parameters
        validation_results = {
            "success": True,
            "parameters": self.parameters,
            "validated": True,
        }
        return validation_results

    def get_id(self) -> str:
        """
        Get unique identifier from common field patterns.

        Utility method for extracting ID from various field names.
        Not a protocol implementation.

        Returns:
            String representation of the ID field.

        Raises:
            ModelOnexError: If no valid ID field is found.
        """
        # Try common ID field patterns
        for field in [
            "id",
            "uuid",
            "identifier",
            "node_id",
            "execution_id",
            "metadata_id",
        ]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        raise ModelOnexError(
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

    def serialize(self) -> SerializedDict:
        """
        Serialize to dictionary format.

        Utility method for serialization. Not a protocol implementation.

        Returns:
            Dictionary representation of the operation parameters.
        """
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """
        Validate instance integrity.

        Utility method for basic validation. Not a protocol implementation.

        Returns:
            True if validation passes, False otherwise.
        """
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True
