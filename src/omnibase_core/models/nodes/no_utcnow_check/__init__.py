# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""no_utcnow_check COMPUTE node models (OMN-14656).

The report/finding shapes are NOT node-local — this node returns the
canonical OMN-2362 generic validator report
(:mod:`omnibase_core.models.validation.model_validation_report`), not a
per-node fork. Import ``ModelValidationReport`` /
``ModelValidationFindingEmbed`` from there.
"""

from omnibase_core.models.nodes.no_utcnow_check.model_no_utcnow_check_input import (
    ModelNoUtcnowCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)

__all__ = [
    "ModelNoUtcnowCheckInput",
    "ModelSourceFile",
]
