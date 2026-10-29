# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Enum member casing check COMPUTE handler over the pure validation-layer checker."""

from __future__ import annotations

from omnibase_core.models.nodes.enum_member_casing_check.model_enum_member_casing_check_input import (
    ModelEnumMemberCasingCheckInput,
)
from omnibase_core.models.nodes.enum_member_casing_check.model_enum_member_casing_check_output import (
    ModelEnumMemberCasingCheckOutput,
)
from omnibase_core.validation.checker_enum_member_casing import validate_source


class NodeEnumMemberCasingCheckCompute:
    """Enum member casing check COMPUTE handler over the pure validation-layer checker.

    Pure and deterministic: all input arrives through the typed request, so the
    handler performs no filesystem access.
    """

    def handle(
        self, request: ModelEnumMemberCasingCheckInput
    ) -> ModelEnumMemberCasingCheckOutput:
        """Run the check over the supplied request and return the result."""
        issues: list[str] = []
        for source_file in request.files:
            issues.extend(validate_source(source_file.source, source_file.path))
        return ModelEnumMemberCasingCheckOutput(issues=tuple(issues))
