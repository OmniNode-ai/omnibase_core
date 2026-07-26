# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Per-role dispatch report contracts (OMN-15161).

Fleet-generic port of steel_onslaught PR #213's golden-chain agent dispatch
report contracts (originally ``steel_onslaught.contracts.dispatch_report``),
lifted into ``omnibase_core`` as the fleet-wide wire type per
``docs/plans/2026-07-26-steel-node-dispatch-integration-plan.md`` §3 P1 and
epic OMN-15154. Extends/supersedes OMN-9091 (SubagentStop json-report schema
validation); OMN-9063 (shape-only prior art) is proven insufficient by the
2026-07-25 literal-``"test"``-passed-validation incident this contract
exists to close.

Four dispatch roles are modeled here: ``implementer`` (builds/fixes code and
opens or updates a PR), ``verifier`` (independently re-checks an
implementer's claim against live evidence), ``lander`` (merges/finalizes a
PR), and ``scout`` (investigates/discovers, no PR required). Each role's
model is closed (``extra="forbid"``) and discriminated on its own ``role``
Literal.

Field-name-suffix convention (load-bearing for
``omnibase_core.validation.validator_dispatch_report_anchors``): any field
ending ``_sha`` is a git-commit content anchor; any field ending ``_paths``
is a list-of-artifact-paths content anchor.

This is a NEW model family, not a variant of
``omnibase_core.models.dispatch.model_skill_result.ModelSkillResult`` --
``ModelSkillResult[T]`` remains the CLI-receipt-envelope layer and is reused,
not duplicated, by whatever consumes these report models (one-canonical-
model-per-shape).
"""

from __future__ import annotations

from omnibase_core.enums.enum_dispatch_report_role import EnumDispatchReportRole
from omnibase_core.enums.enum_dispatch_report_verdict import (
    EnumDispatchReportImplementerVerdict,
    EnumDispatchReportLanderVerdict,
    EnumDispatchReportScoutVerdict,
    EnumDispatchReportVerifierVerdict,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_implementer import (
    ModelDispatchReportImplementer,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_lander import (
    ModelDispatchReportLander,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_registry import (
    ROLE_TO_MODEL,
    DispatchReport,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_scout import (
    ModelDispatchReportScout,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_types import (
    GitSha,
    ModelDispatchReportBase,
    PrNumber,
)
from omnibase_core.models.dispatch.report.model_dispatch_report_verifier import (
    ModelDispatchReportVerifier,
)

__all__ = [
    "ROLE_TO_MODEL",
    "DispatchReport",
    "EnumDispatchReportImplementerVerdict",
    "EnumDispatchReportLanderVerdict",
    "EnumDispatchReportRole",
    "EnumDispatchReportScoutVerdict",
    "EnumDispatchReportVerifierVerdict",
    "GitSha",
    "ModelDispatchReportBase",
    "ModelDispatchReportImplementer",
    "ModelDispatchReportLander",
    "ModelDispatchReportScout",
    "ModelDispatchReportVerifier",
    "PrNumber",
]
