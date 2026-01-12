# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Dependency cycle exception."""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.pipeline.exceptions.pipeline_exception import PipelineError


class DependencyCycleError(PipelineError):
    """Raised when hook dependencies form a cycle."""

    def __init__(self, cycle: list[str]) -> None:
        super().__init__(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Dependency cycle detected: {' -> '.join(cycle)}",
            context={"cycle": cycle, "validation_kind": "dependency_cycle"},
        )


__all__ = ["DependencyCycleError"]
