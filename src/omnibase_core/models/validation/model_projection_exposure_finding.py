# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Finding model for the projection exposure⇄column drift validator (OMN-13663).

The validator reconciles every projection node ``contract.yaml``'s
``projection_api.exposures`` against the materialized columns of the table/view
each exposure reads from (extracted from the node's migration DDL). Two finding
kinds are produced:

* ``MISSING_COLUMN`` (``ERROR``) — an exposure lists a column that does not
  exist among the materialized columns of its table/view. Blocking: a phantom
  column makes the projection query fail at runtime.
* ``OMITTED_COLUMN`` (``WARN``) — a materialized column matching an
  identity/tier/cost keyword is not surfaced by ANY exposure of its table. This
  is exactly the class of bug that dropped ``delegation_events.cost_tier_name``
  at the projection boundary (OMN-13649). Warn-only + annotated allowlist.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from omnibase_core.enums.enum_projection_exposure_drift import (
    EnumProjectionDriftKind,
    EnumProjectionDriftSeverity,
)


@dataclass(frozen=True, slots=True)
class ModelProjectionExposureFinding:
    """A single projection exposure⇄column drift finding."""

    severity: EnumProjectionDriftSeverity
    kind: EnumProjectionDriftKind
    node: str
    contract_path: Path
    table: str
    column: str
    exposure_topic: str | None
    detail: str

    def format(self) -> str:
        topic = f" topic={self.exposure_topic}" if self.exposure_topic else ""
        return (
            f"{self.contract_path}: [{self.severity.value}] {self.node} "
            f"table={self.table} column={self.column}{topic}: {self.detail}"
        )
