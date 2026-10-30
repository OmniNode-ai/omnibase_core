# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""HandlerDependencyDirection -- cross-repository dependency direction.

A repository may depend only on repositories at a strictly lower layer of the
declared order (``contracts/repo_layers.yaml``). This pure handler
takes the scanned repository's name, the layer map, explicit
``(path, source)`` pairs and the repository's baseline, and returns the
canonical ``ModelValidationReport``:

* FAIL -- a reference to a repository at the same or a higher layer that the
  baseline does not record.
* WARN -- a recorded (baselined) violation that still exists, and, on a
  full-tree scan, a baseline entry no file produces any more (remove it).
* ERROR -- the scanned repository is not declared in the layer map.

Pure: no filesystem, no clock, no global state. Ticket: OMN-19998.
"""

from __future__ import annotations

from typing import Final, Literal

from omnibase_core.models.dependency_direction.model_dependency_direction_check_input import (
    ModelDependencyDirectionCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_dependency_direction_check_effect.matcher_dependency_direction import (
    VALIDATOR_ID,
    extract_references,
)

__all__ = ["HandlerDependencyDirection"]

_PROFILE: Final[Literal["strict", "default", "advisory"]] = "default"


class HandlerDependencyDirection:
    """COMPUTE handler that flags upward and same-layer cross-repo dependencies."""

    def handle(
        self, request: ModelDependencyDirectionCheckInput
    ) -> ModelValidationReport:
        """Definition-B canonical entry-point: typed request in, typed report out."""
        rules = request.rules
        own = request.layer_map.get(request.repo)
        if own is None:
            return ModelValidationReport.from_runtime_errors(
                VALIDATOR_ID,
                (rules.undeclared_repo_message.format(repo=request.repo),),
            )

        layers = {entry.repo: entry.layer for entry in request.layer_map.repos}
        baseline = {entry.key(): entry for entry in request.baseline}
        seen_keys: set[tuple[str, str, str]] = set()
        findings: list[ModelValidationFindingEmbed] = []

        for file in sorted(request.files, key=lambda f: f.path):
            for channel, target, line, evidence in extract_references(
                file.path, file.source, request.layer_map, request.repo, rules
            ):
                target_layer = layers[target]
                if target_layer < own.layer:
                    continue
                key = (file.path, channel.value, target)
                direction = (
                    rules.direction_same
                    if target_layer == own.layer
                    else rules.direction_above
                )
                message = rules.violation_message.format(
                    path=file.path,
                    line=line,
                    repo=request.repo,
                    own_layer=own.layer,
                    target=target,
                    target_layer=target_layer,
                    direction=direction,
                    channel=channel.value,
                    evidence=evidence,
                )
                recorded = baseline.get(key)
                if recorded is not None:
                    if key in seen_keys:
                        continue
                    findings.append(
                        ModelValidationFindingEmbed(
                            validator_id=VALIDATOR_ID,
                            severity="WARN",
                            location=f"{file.path}:{line}",
                            message=rules.baselined_message.format(
                                ticket=recorded.ticket, message=message
                            ),
                            remediation=rules.remediation,
                        )
                    )
                else:
                    findings.append(
                        ModelValidationFindingEmbed(
                            validator_id=VALIDATOR_ID,
                            severity="FAIL",
                            location=f"{file.path}:{line}",
                            message=message,
                            remediation=rules.remediation,
                        )
                    )
                seen_keys.add(key)

        if request.report_stale_baseline:
            for key, entry in sorted(baseline.items()):
                if key in seen_keys:
                    continue
                findings.append(
                    ModelValidationFindingEmbed(
                        validator_id=VALIDATOR_ID,
                        severity="WARN",
                        location=entry.path,
                        message=rules.stale_message.format(
                            ticket=entry.ticket,
                            path=entry.path,
                            target=entry.target,
                            channel=entry.channel.value,
                        ),
                        remediation=None,
                    )
                )

        return ModelValidationReport.from_findings(
            findings=tuple(findings),
            request=ModelValidationRequestRef(profile=_PROFILE),
            validators_run=(VALIDATOR_ID,),
        )
