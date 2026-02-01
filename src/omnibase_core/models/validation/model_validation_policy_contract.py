"""Validation policy contract for cross-repo conformance validation.

Defines the schema that repositories use to declare their validation policies.
The validation engine interprets this contract; repos supply the policy.

Related ticket: OMN-1771
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_rule_configs import ModelRuleConfigBase
from .model_validation_discovery_config import ModelValidationDiscoveryConfig
from .model_violation_waiver import ModelViolationWaiver


class ModelValidationPolicyContract(BaseModel):
    """Repo-level validation policy contract.

    Defines what validation rules to run and how for a specific repository.
    The engine (in core) interprets this contract; repos supply the policy.

    Example:
        >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
        >>> policy = ModelValidationPolicyContract(
        ...     policy_id="omnibase_infra_policy",
        ...     policy_version=ModelSemVer(major=1, minor=0, patch=0),
        ...     repo_id="omnibase_infra",
        ...     discovery=ModelValidationDiscoveryConfig(
        ...         include_globs=("src/**/*.py",),
        ...         exclude_globs=("**/test_*.py",),
        ...     ),
        ... )
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # Identity (string IDs are human-readable policy identifiers, not database UUIDs)
    policy_id: str = Field(  # string-id-ok: human-readable policy identifier
        description="Unique identifier for this policy"
    )

    policy_version: ModelSemVer = Field(
        description="Semantic version of this policy",
    )

    repo_id: str = Field(  # string-id-ok: human-readable repository identifier
        description="Repository this policy applies to"
    )

    # Inheritance (Phase 0.5+)
    extends: str | None = Field(
        default=None,
        description="Base policy ID to inherit from (for org/team defaults)",
    )

    # Discovery configuration
    discovery: ModelValidationDiscoveryConfig = Field(
        description="What files to scan",
    )

    # Rule configurations (rule_id -> typed config)
    rules: dict[str, ModelRuleConfigBase] = Field(
        default_factory=dict,
        description="Rule ID to configuration mapping",
    )

    # Baseline waivers for known violations
    baselines: tuple[ModelViolationWaiver, ...] = Field(
        default=(),
        description="Temporary waivers for known violations",
    )


__all__ = ["ModelValidationPolicyContract"]
