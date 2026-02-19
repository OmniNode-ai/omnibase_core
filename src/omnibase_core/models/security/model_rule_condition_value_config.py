# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Configuration for ModelRuleConditionValue."""

from pydantic import ConfigDict


class ModelRuleConditionValueConfig:
    """Configuration for ModelRuleConditionValue."""

    model_config = ConfigDict(populate_by_name=True)
