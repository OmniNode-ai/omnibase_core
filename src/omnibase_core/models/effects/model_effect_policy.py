"""Effect Policy Specification Model for defining replay policies.

Specifies how non-deterministic effects should be handled during replay.
Part of the effect boundary system for OMN-1147.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_effect_category import EnumEffectCategory
from omnibase_core.enums.enum_effect_policy_level import EnumEffectPolicyLevel

__all__ = ["ModelEffectPolicySpec"]


class ModelEffectPolicySpec(BaseModel):
    """Specification for handling non-deterministic effects during replay.

    Defines granular policies for which effect categories are allowed, blocked,
    or require mocking. Also supports allowlisting/denylisting specific effect
    IDs for fine-grained control.

    This model is immutable after creation for thread safety.
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
