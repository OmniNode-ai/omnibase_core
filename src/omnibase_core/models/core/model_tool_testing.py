"""
Tool Testing Model.

Testing requirements and configuration for tools.
"""

from pydantic import BaseModel, Field

from omnibase_core.types.typed_dict_tool_testing_config_summary import (
    TypedDictToolTestingConfigSummary,
)
from omnibase_core.types.typed_dict_tool_testing_summary import (
    TypedDictToolTestingSummary,
)


class ModelToolTesting(BaseModel):
    """Testing requirements and configuration."""

    required_ci_tiers: list[str] = Field(
        default_factory=lambda: ["unit", "integration"],
        description="Required CI testing tiers",
    )
    minimum_coverage_percentage: float = Field(
        default=85.0,
        description="Minimum test coverage percentage required",
    )
    canonical_test_case_ids: list[str] = Field(
        default_factory=list,
        description="Canonical test case identifiers",
    )
    performance_test_required: bool = Field(
        default=False,
        description="Whether performance testing is required",
    )
    security_test_required: bool = Field(
        default=True,
        description="Whether security testing is required",
    )

    def requires_unit_tests(self) -> bool:
        """Check if unit tests are required."""
        return "unit" in self.required_ci_tiers

    def requires_integration_tests(self) -> bool:
        """Check if integration tests are required."""
        return "integration" in self.required_ci_tiers

    def requires_e2e_tests(self) -> bool:
        """Check if end-to-end tests are required."""
        return "e2e" in self.required_ci_tiers

    def get_ci_tier_count(self) -> int:
        """Get number of required CI tiers."""
        return len(self.required_ci_tiers)

    def has_canonical_tests(self) -> bool:
        """Check if tool has canonical test cases."""
        return len(self.canonical_test_case_ids) > 0

    def get_test_requirement_summary(self) -> TypedDictToolTestingSummary:
        """Get test requirement summary."""
        return TypedDictToolTestingSummary(
            requires_unit=self.requires_unit_tests(),
            requires_integration=self.requires_integration_tests(),
            requires_e2e=self.requires_e2e_tests(),
            requires_performance=self.performance_test_required,
            requires_security=self.security_test_required,
            ci_tier_count=self.get_ci_tier_count(),
            has_canonical_tests=self.has_canonical_tests(),
            canonical_test_count=len(self.canonical_test_case_ids),
            minimum_coverage=self.minimum_coverage_percentage,
        )

    def meets_coverage_requirement(self, actual_coverage: float) -> bool:
        """Check if actual coverage meets requirement."""
        return actual_coverage >= self.minimum_coverage_percentage

    def get_coverage_gap(self, actual_coverage: float) -> float:
        """Get coverage gap (negative if exceeding requirement)."""
        return self.minimum_coverage_percentage - actual_coverage

    def get_summary(self) -> TypedDictToolTestingConfigSummary:
        """Get testing configuration summary."""
        return TypedDictToolTestingConfigSummary(
            required_ci_tiers=self.required_ci_tiers,
            minimum_coverage_percentage=self.minimum_coverage_percentage,
            canonical_test_case_ids=self.canonical_test_case_ids,
            performance_test_required=self.performance_test_required,
            security_test_required=self.security_test_required,
            test_requirements=self.get_test_requirement_summary(),
        )
