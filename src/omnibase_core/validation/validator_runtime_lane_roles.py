# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorRuntimeLaneRoles -- a contract's runtime_lane_roles name known roles.

OMN-19746, plan task LO1 of knowledge-base-internal
``beta/plans/2026-09-26-runtime-lane-overlays-plan.md``.

A node contract that needs a kind of lane declares ``runtime_lane_roles`` at the
top level; the runtime attaches it only on a lane whose ``runtime.lane``
overlay document grants every role listed. A contract never names a lane.

One rule, ``runtime_lane_role_unknown``: the value must be a non-empty list of
roles from :class:`EnumRuntimeLaneRole`. A role outside the vocabulary, a lane
id written where a role belongs, or an empty list would scope the node to a
role no deployment can hold, which silently detaches it everywhere.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import ClassVar

import yaml
from pydantic import ValidationError

from omnibase_core.enums.enum_runtime_lane_role import EnumRuntimeLaneRole
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_runtime_lane_role_requirement import (
    ModelRuntimeLaneRoleRequirement,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.validator_base import ValidatorBase

RULE_RUNTIME_LANE_ROLE_UNKNOWN = "runtime_lane_role_unknown"

_CONTRACT_FILE_NAMES: frozenset[str] = frozenset(
    {"contract.yaml", "handler_contract.yaml"}
)


class ValidatorRuntimeLaneRoles(ValidatorBase):
    """Reject contracts whose runtime_lane_roles is not a list of known roles."""

    validator_id: ClassVar[str] = "runtime_lane_roles"

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        if path.name not in _CONTRACT_FILE_NAMES:
            return ()
        try:
            raw = load_yaml_mapping_no_duplicates(
                path.read_text(encoding="utf-8"), source=str(path)
            )
        except (OSError, ValueError, yaml.YAMLError):
            return ()
        if "runtime_lane_roles" not in raw:
            return ()
        try:
            ModelRuntimeLaneRoleRequirement.model_validate(
                {"roles": raw["runtime_lane_roles"]}
            )
        except ValidationError as exc:
            enabled, severity = self._get_rule_config(
                RULE_RUNTIME_LANE_ROLE_UNKNOWN, contract
            )
            if not enabled:
                return ()
            reasons = "; ".join(error["msg"] for error in exc.errors())
            known = ", ".join(role.value for role in EnumRuntimeLaneRole)
            message = (
                f"runtime_lane_roles on contract {raw.get('name')!r} is invalid "
                f"({reasons}). Name one or more runtime lane roles, never a lane: "
                f"{known}."
            )
            return (
                ModelValidationIssue(
                    severity=severity,
                    message=message,
                    code=RULE_RUNTIME_LANE_ROLE_UNKNOWN,
                    file_path=path,
                    line_number=1,
                    rule_name=RULE_RUNTIME_LANE_ROLE_UNKNOWN,
                ),
            )
        return ()


if __name__ == "__main__":
    sys.exit(ValidatorRuntimeLaneRoles.main())
