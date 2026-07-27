# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""no_raw_sqlite3_check COMPUTE node models (OMN-14659).

The report/finding shapes are NOT node-local — this node returns the
canonical OMN-2362 generic validator report
(:mod:`omnibase_core.models.validation.model_validation_report`), not a
per-node fork. Import ``ModelValidationReport`` /
``ModelValidationFindingEmbed`` from there. The per-file input shape
(:class:`~omnibase_core.models.nodes.no_utcnow_check.model_source_file.ModelSourceFile`)
is the shared (path, source) DTO — also not forked here.
"""

from omnibase_core.models.nodes.no_raw_sqlite3_check.model_no_raw_sqlite3_check_input import (
    ModelNoRawSqlite3CheckInput,
)

__all__ = [
    "ModelNoRawSqlite3CheckInput",
]
