# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Container-bound console entry for invariant analysis (OMN-21565)."""

from omnibase_core.nodes.node_validation_report_write_effect import (
    runtime_validator_run,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    build_validator_container,
)
from omnibase_core.validation.validator_invariant_analysis import (
    ValidatorInvariantAnalysis,
)

__all__ = ["main"]


def main() -> int:
    """Run the global validator through the canonical report-writing runtime."""
    return runtime_validator_run.main(
        ValidatorInvariantAnalysis, None, build_validator_container
    )
