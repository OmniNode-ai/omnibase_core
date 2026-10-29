# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)


def check(text: str) -> ModelValidationReport:
    raise NotImplementedError(text)
