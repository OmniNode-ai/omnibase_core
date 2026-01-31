"""Static rule registry for cross-repo validation.

Rule IDs are fixed in core. Rule behavior is fixed in core.
Contracts can only supply parameters, not redefine semantics.
This prevents "same rule ID means different things in different repos".
"""

from __future__ import annotations

from typing import ClassVar

from omnibase_core.models.validation.model_rule_configs import (
    ModelRuleConfigBase,
    ModelRuleContractSchemaConfig,
    ModelRuleErrorTaxonomyConfig,
    ModelRuleForbiddenImportsConfig,
    ModelRuleRepoBoundariesConfig,
    ModelRuleTopicNamingConfig,
)


class RuleRegistry:
    """Static registry of validation rules.

    This registry maps rule IDs to their configuration models.
    Adding new rules requires updating core; repos cannot add rules.
    """

    # Phase 0 rules
    RULE_REPO_BOUNDARIES: ClassVar[str] = "repo_boundaries"
    RULE_FORBIDDEN_IMPORTS: ClassVar[str] = "forbidden_imports"

    # Phase 1 rules
    RULE_TOPIC_NAMING: ClassVar[str] = "topic_naming"
    RULE_ERROR_TAXONOMY: ClassVar[str] = "error_taxonomy"
    RULE_CONTRACT_SCHEMA: ClassVar[str] = "contract_schema_valid"

    # The registry itself - maps rule_id to config model type
    _REGISTRY: ClassVar[dict[str, type[ModelRuleConfigBase]]] = {
        "repo_boundaries": ModelRuleRepoBoundariesConfig,
        "forbidden_imports": ModelRuleForbiddenImportsConfig,
        "topic_naming": ModelRuleTopicNamingConfig,
        "error_taxonomy": ModelRuleErrorTaxonomyConfig,
        "contract_schema_valid": ModelRuleContractSchemaConfig,
    }

    @classmethod
    def get_config_type(
        cls,
        rule_id: str,  # string-id-ok: rule registry key
    ) -> type[ModelRuleConfigBase]:
        """Get the configuration model type for a rule ID.

        Args:
            rule_id: The rule identifier.

        Returns:
            The Pydantic model type for the rule's configuration.

        Raises:
            ValueError: If rule_id is not registered.
        """
        if rule_id not in cls._REGISTRY:
            valid_rules = ", ".join(sorted(cls._REGISTRY.keys()))
            # error-ok: ValueError for invalid input at API boundary
            raise ValueError(
                f"Unknown rule ID: {rule_id!r}. Valid rules: {valid_rules}"
            )
        return cls._REGISTRY[rule_id]

    @classmethod
    def is_registered(cls, rule_id: str) -> bool:  # string-id-ok: rule registry key
        """Check if a rule ID is registered.

        Args:
            rule_id: The rule identifier to check.

        Returns:
            True if the rule is registered, False otherwise.
        """
        return rule_id in cls._REGISTRY

    @classmethod
    def list_rules(cls) -> list[str]:
        """List all registered rule IDs.

        Returns:
            Sorted list of registered rule IDs.
        """
        return sorted(cls._REGISTRY.keys())

    @classmethod
    def get_phase_0_rules(cls) -> list[str]:
        """Get rule IDs for Phase 0 (minimal but lethal).

        Returns:
            List of Phase 0 rule IDs.
        """
        return [cls.RULE_REPO_BOUNDARIES, cls.RULE_FORBIDDEN_IMPORTS]

    @classmethod
    def get_phase_1_rules(cls) -> list[str]:
        """Get rule IDs for Phase 1 (stop the 2am incidents).

        Returns:
            List of Phase 1 rule IDs.
        """
        return [
            cls.RULE_ERROR_TAXONOMY,
            cls.RULE_CONTRACT_SCHEMA,
            cls.RULE_TOPIC_NAMING,
        ]


def get_rule_config_type(
    rule_id: str,  # string-id-ok: rule registry key
) -> type[ModelRuleConfigBase]:
    """Get the config model type for a rule ID.

    Convenience function wrapping RuleRegistry.get_config_type().

    Args:
        rule_id: The rule identifier.

    Returns:
        The Pydantic model type for the rule's configuration.

    Raises:
        ValueError: If rule_id is not registered.
    """
    return RuleRegistry.get_config_type(rule_id)
