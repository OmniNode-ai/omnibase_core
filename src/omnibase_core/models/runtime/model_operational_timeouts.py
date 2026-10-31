# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Wall-clock budgets of omnibase_core's operational probes, subprocess calls and lock waits (OMN-21623).

The numbers live in ``operational_timeouts.yaml`` beside this module. Every field is required
and the model refuses an unknown key, so a budget missing from the contract fails the load
instead of silently falling back to a literal in code. Call sites read the budgets through
``packaged_timeouts()``.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model

_PACKAGED_CONTRACT = Path(__file__).with_name("operational_timeouts.yaml")


class ModelOperationalTimeouts(BaseModel):
    """Per-operation time budgets, in seconds, declared by the packaged contract."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    merge_queue_enqueue_seconds: float = Field(
        gt=0,
        description="Budget for each call that enqueues a pull request in the merge queue.",
    )
    merge_strategy_api_seconds: float = Field(
        gt=0,
        description="Budget for the call that detects a repository merge strategy.",
    )
    rebase_run_seconds: float = Field(
        gt=0, description="Budget for the rebase of a pull request branch."
    )
    rebase_fetch_seconds: float = Field(
        gt=0, description="Budget for the git fetch that precedes a rebase."
    )
    rebase_abort_seconds: float = Field(
        gt=0, description="Budget for aborting a rebase that failed."
    )
    work_ledger_lock_seconds: float = Field(
        gt=0, description="Budget for waiting on the work-ledger render lock."
    )
    occ_git_read_seconds: float = Field(
        gt=0,
        description="Budget for a git read made by the merge-eligibility validator.",
    )
    occ_formatter_version_seconds: float = Field(
        gt=0,
        description="Budget for the formatter version probe of the merge-eligibility validator.",
    )
    occ_formatter_lint_seconds: float = Field(
        gt=0,
        description="Budget for the formatter lint run of the merge-eligibility validator.",
    )
    receipt_reprobe_reexec_seconds: float = Field(
        gt=0,
        description="Wall-clock cap per receipt probe re-execution; a slower probe is hung and fails closed.",
    )
    contracts_validation_seconds: float = Field(
        gt=0, description="Budget for one contracts validation run."
    )
    consumer_graph_lock_seconds: float = Field(
        gt=0, description="Budget for waiting on the consumer-graph cache lock."
    )
    shared_token_policy_response_seconds: float = Field(
        gt=0, description="Budget for the shared-token policy reply over the bus."
    )
    introspection_discovery_seconds: float = Field(
        gt=0, description="Default wait of a discovery introspection request."
    )
    introspection_mcp_discovery_seconds: float = Field(
        gt=0, description="Default wait of an MCP server discovery request."
    )
    introspection_health_check_seconds: float = Field(
        gt=0, description="Default wait of a health-monitoring introspection request."
    )
    tool_invocation_mcp_seconds: float = Field(
        gt=0, description="Default wait of an MCP tool invocation."
    )
    tool_invocation_cli_seconds: float = Field(
        gt=0, description="Default wait of a CLI tool invocation."
    )

    @classmethod
    def packaged(cls) -> ModelOperationalTimeouts:
        """The budgets declared by the packaged ``operational_timeouts.yaml``."""
        return packaged_timeouts()


@cache
def packaged_timeouts() -> ModelOperationalTimeouts:
    """The packaged budgets, read once; the short name keeps call sites on one line."""
    return load_and_validate_yaml_model(_PACKAGED_CONTRACT, ModelOperationalTimeouts)
