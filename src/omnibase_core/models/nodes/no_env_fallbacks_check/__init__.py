# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""no_env_fallbacks_check COMPUTE node models (OMN-14659).

The report/finding shapes are NOT node-local — this node returns the
canonical OMN-2362 generic validator report
(:mod:`omnibase_core.models.validation.model_validation_report`), not a
per-node fork. Import ``ModelValidationReport`` /
``ModelValidationFindingEmbed`` from there. The per-file input shape
(:class:`~omnibase_core.models.nodes.no_utcnow_check.model_source_file.ModelSourceFile`)
is the shared (path, source) DTO — also not forked here.
"""

from omnibase_core.models.nodes.no_env_fallbacks_check.model_no_env_fallbacks_check_input import (
    ModelNoEnvFallbacksCheckInput,
)

__all__ = [
    "ModelNoEnvFallbacksCheckInput",
]
