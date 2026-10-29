# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)

_REMEDIATION = "Move the default into the rules file."


def main() -> int:
    return 0 if NodeValidationReportWriteEffect is not None else 1
