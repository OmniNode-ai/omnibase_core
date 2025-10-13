"""Configuration for ModelRuleConditionValue."""

from pydantic import ConfigDict


class ModelRuleConditionValueConfig:
    """Configuration for ModelRuleConditionValue."""

    model_config = ConfigDict(populate_by_name=True)
