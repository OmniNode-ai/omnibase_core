"""
Numeric Computation Output Model.

Numeric computation output data with precision tracking and error handling.
"""

from pydantic import Field

from omnibase_core.enums.enum_computation_type import EnumComputationType
from omnibase_core.models.operations.model_computation_output_base import (
    ModelComputationOutputBase,
)
from omnibase_core.types.typed_dict_numeric_precision_summary import (
    TypedDictNumericPrecisionSummary,
)


class ModelNumericComputationOutput(ModelComputationOutputBase):
    """Numeric computation output data."""

    computation_type: EnumComputationType = Field(
        default=EnumComputationType.NUMERIC,
        description="Numeric computation type",
    )
    numeric_results: dict[str, float] = Field(
        default_factory=dict,
        description="Numeric computation results",
    )
    precision_achieved: int = Field(default=2, description="Actual precision achieved")
    calculation_errors: list[str] = Field(
        default_factory=list,
        description="Any calculation errors encountered",
    )
    convergence_info: dict[str, float] = Field(
        default_factory=dict,
        description="Convergence information for iterative calculations",
    )

    def add_numeric_result(
        self, key: str, value: float
    ) -> "ModelNumericComputationOutput":
        """Add a numeric result."""
        new_results = {**self.numeric_results, key: value}
        return self.model_copy(update={"numeric_results": new_results})

    def get_numeric_result(self, key: str) -> float | None:
        """Get a numeric result by key."""
        return self.numeric_results.get(key)

    def add_calculation_error(self, error: str) -> "ModelNumericComputationOutput":
        """Add a calculation error."""
        new_errors = [*self.calculation_errors, error]
        return self.model_copy(update={"calculation_errors": new_errors})

    def has_calculation_errors(self) -> bool:
        """Check if there are any calculation errors."""
        return len(self.calculation_errors) > 0

    def add_convergence_info(
        self, key: str, value: float
    ) -> "ModelNumericComputationOutput":
        """Add convergence information."""
        new_info = {**self.convergence_info, key: value}
        return self.model_copy(update={"convergence_info": new_info})

    def get_convergence_value(self, key: str) -> float | None:
        """Get convergence information by key."""
        return self.convergence_info.get(key)

    def is_converged(self, tolerance: float = 1e-6) -> bool:
        """Check if computation has converged based on convergence info."""
        convergence_value = self.convergence_info.get("converged")
        if convergence_value is not None:
            return abs(convergence_value) < tolerance
        return False

    def get_precision_summary(self) -> TypedDictNumericPrecisionSummary:
        """Get precision-related summary."""
        return TypedDictNumericPrecisionSummary(
            precision_achieved=self.precision_achieved,
            result_count=len(self.numeric_results),
            has_errors=self.has_calculation_errors(),
            convergence_status=self.is_converged(),
        )
