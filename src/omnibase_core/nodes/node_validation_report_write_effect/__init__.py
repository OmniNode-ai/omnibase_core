# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""validation_report_write EFFECT node package (OMN-20565).

Exposes :class:`NodeValidationReportWriteEffect` — persists the canonical
OMN-2362 validation report as JSON, the one filesystem write every converted
check runtime shares behind its ``--report-json`` flag.
"""

from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)

__all__ = ["NodeValidationReportWriteEffect"]
