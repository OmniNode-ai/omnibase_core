"""Effect Policy Specification Model for defining replay policies.

Specifies how non-deterministic effects should be handled during replay.
Part of the effect boundary system for OMN-1147.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_effect_category import EnumEffectCategory
from omnibase_core.enums.enum_effect_policy_level import EnumEffectPolicyLevel

__all__ = ["ModelEffectPolicySpec"]


class ModelEffectPolicySpec(BaseModel):
    """Specification for handling non-deterministic effects during replay.

    Defines granular policies for which effect categories are allowed, blocked,
    or require mocking. Also supports allowlisting/denylisting specific effect
    IDs for fine-grained control.

    This model is immutable after creation for thread safety.

    Category Combination Rules:
        - allowed + blocked: Invalid (raises ValueError)
        - blocked + require_mocks: Invalid (raises ValueError) - blocked categories
          are rejected before mock lookup occurs
        - allowed + require_mocks: Valid - means "allow this category but require
          a mock during replay" (useful for categories you want to permit but
          still need deterministic behavior)
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    policy_level: EnumEffectPolicyLevel = Field(
        description="Base policy level for effect handling",
    )
    allowed_categories: tuple[EnumEffectCategory, ...] = Field(
        default_factory=tuple,
        description="Effect categories explicitly allowed regardless of policy level",
    )
    blocked_categories: tuple[EnumEffectCategory, ...] = Field(
        default_factory=tuple,
        description="Effect categories explicitly blocked regardless of policy level",
    )
    require_mocks_for_categories: tuple[EnumEffectCategory, ...] = Field(
        default_factory=tuple,
        description="Effect categories that must be mocked during replay",
    )
    allowlist_effect_ids: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Specific effect IDs that are allowed regardless of category",
    )
    denylist_effect_ids: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Specific effect IDs that are blocked regardless of category",
    )

    @model_validator(mode="after")
    def _validate_no_conflicts(self) -> Self:
        """Validate that there are no conflicting policy configurations.

        Raises:
            ValueError: If a category is in both allowed and blocked lists,
                or if an effect ID is in both allowlist and denylist.
        """
        # Check for categories in both allowed and blocked
        allowed_set = set(self.allowed_categories)
        blocked_set = set(self.blocked_categories)
        category_conflicts = allowed_set & blocked_set
        if category_conflicts:
            conflict_names = sorted(c.value for c in category_conflicts)
            raise ValueError(
                f"Categories cannot be both allowed and blocked: {conflict_names}"
            )

        # Check for effect IDs in both allowlist and denylist
        allowlist_set = set(self.allowlist_effect_ids)
        denylist_set = set(self.denylist_effect_ids)
        id_conflicts = allowlist_set & denylist_set
        if id_conflicts:
            raise ValueError(
                f"Effect IDs cannot be both allowlisted and denylisted: "
                f"{sorted(id_conflicts)}"
            )

        # Check for blocked categories also in require_mocks
        blocked_mocked = blocked_set & set(self.require_mocks_for_categories)
        if blocked_mocked:
            conflict_names = sorted(c.value for c in blocked_mocked)
            raise ValueError(
                f"Categories cannot be both blocked and require mocking: {conflict_names}. "
                f"Blocked categories are rejected before mock lookup occurs."
            )

        return self

    def is_category_allowed(self, category: EnumEffectCategory) -> bool:
        """Check if an effect category is allowed under this policy.

        A category is allowed if:
        - It is explicitly in allowed_categories, OR
        - The policy level is not STRICT and the category is not in blocked_categories
        """
        if category in self.blocked_categories:
            return False
        if category in self.allowed_categories:
            return True
        return self.policy_level != EnumEffectPolicyLevel.STRICT

    def requires_mock(self, category: EnumEffectCategory) -> bool:
        """Check if an effect category requires mocking.

        A category requires mocking if:
        - It is explicitly in require_mocks_for_categories, OR
        - The policy level is MOCKED
        """
        if category in self.require_mocks_for_categories:
            return True
        return self.policy_level == EnumEffectPolicyLevel.MOCKED

    def is_effect_allowed(
        self,
        effect_id: str,  # string-id-ok: human-readable identifier, not UUID
        category: EnumEffectCategory,
    ) -> bool:
        """Check if a specific effect is allowed under this policy.

        Checks effect ID allowlist/denylist first, then falls back to category rules.
        """
        if effect_id in self.denylist_effect_ids:
            return False
        if effect_id in self.allowlist_effect_ids:
            return True
        return self.is_category_allowed(category)

    def get_effective_policy_for_effect(
        self,
        effect_id: str,  # string-id-ok: human-readable identifier, not UUID
        category: EnumEffectCategory,
    ) -> EnumEffectPolicyLevel:
        """Get the effective policy level for a specific effect.

        Returns the policy level that would apply considering allowlists,
        denylists, and category-specific rules.

        Args:
            effect_id: The effect identifier to check.
            category: The effect category.

        Returns:
            The effective policy level for this effect.
        """
        if effect_id in self.denylist_effect_ids:
            return EnumEffectPolicyLevel.STRICT
        if effect_id in self.allowlist_effect_ids:
            return EnumEffectPolicyLevel.PERMISSIVE
        if category in self.blocked_categories:
            return EnumEffectPolicyLevel.STRICT
        if self.requires_mock(category):
            return EnumEffectPolicyLevel.MOCKED
        return self.policy_level
