# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from omnibase_core.validation.validator_base import ValidatorBase

INFRA_ALLOWLIST = frozenset({"A", "B"})


class ValidatorX(ValidatorBase):
    validator_id = "x"
