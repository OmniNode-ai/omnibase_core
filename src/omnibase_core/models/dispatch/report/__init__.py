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

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "EnumDispatchReportRole": (
        "omnibase_core.enums.enum_dispatch_report_role",
        "EnumDispatchReportRole",
    ),
    "EnumDispatchReportImplementerVerdict": (
        "omnibase_core.enums.enum_dispatch_report_verdict",
        "EnumDispatchReportImplementerVerdict",
    ),
    "EnumDispatchReportLanderVerdict": (
        "omnibase_core.enums.enum_dispatch_report_verdict",
        "EnumDispatchReportLanderVerdict",
    ),
    "EnumDispatchReportScoutVerdict": (
        "omnibase_core.enums.enum_dispatch_report_verdict",
        "EnumDispatchReportScoutVerdict",
    ),
    "EnumDispatchReportVerifierVerdict": (
        "omnibase_core.enums.enum_dispatch_report_verdict",
        "EnumDispatchReportVerifierVerdict",
    ),
    "ModelDispatchReportImplementer": (
        "omnibase_core.models.dispatch.report.model_dispatch_report_implementer",
        "ModelDispatchReportImplementer",
    ),
    "ModelDispatchReportLander": (
        "omnibase_core.models.dispatch.report.model_dispatch_report_lander",
        "ModelDispatchReportLander",
    ),
    "ROLE_TO_MODEL": (
        "omnibase_core.models.dispatch.report.model_dispatch_report_registry",
        "ROLE_TO_MODEL",
    ),
    "DispatchReport": (
        "omnibase_core.models.dispatch.report.model_dispatch_report_registry",
        "DispatchReport",
    ),
    "ModelDispatchReportScout": (
        "omnibase_core.models.dispatch.report.model_dispatch_report_scout",
        "ModelDispatchReportScout",
    ),
    "GitSha": (
        "omnibase_core.models.dispatch.report.model_dispatch_report_types",
        "GitSha",
    ),
    "ModelDispatchReportBase": (
        "omnibase_core.models.dispatch.report.model_dispatch_report_types",
        "ModelDispatchReportBase",
    ),
    "PrNumber": (
        "omnibase_core.models.dispatch.report.model_dispatch_report_types",
        "PrNumber",
    ),
    "ModelDispatchReportVerifier": (
        "omnibase_core.models.dispatch.report.model_dispatch_report_verifier",
        "ModelDispatchReportVerifier",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
