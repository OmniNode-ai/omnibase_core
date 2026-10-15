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

from omnibase_core.handlers.handler_dependency_direction_rules import (
    VALIDATOR_ID,
    extract_references,
)
from omnibase_core.models.dependency_direction.model_dependency_direction_check_input import (
    ModelDependencyDirectionCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)

__all__ = ["HandlerDependencyDirection"]

_PROFILE: Final[Literal["strict", "default", "advisory"]] = "default"
_REMEDIATION: Final[str] = (
    "A repository may depend only on repositories at a strictly lower layer "
    "(omnibase_core contracts/repo_layers.yaml). Remove the dependency or move the code "
    "to the lower repository; never add it to the baseline."
)


class HandlerDependencyDirection:
    """COMPUTE handler that flags upward and same-layer cross-repo dependencies."""

    def handle(
        self, request: ModelDependencyDirectionCheckInput
    ) -> ModelValidationReport:
        """Definition-B canonical entry-point: typed request in, typed report out."""
        own = request.layer_map.get(request.repo)
        if own is None:
            return ModelValidationReport.from_runtime_errors(
                VALIDATOR_ID,
                (
                    f"repository {request.repo!r} is not declared in the layer map; "
                    "declare its layer in contracts/repo_layers.yaml",
                ),
            )

        layers = {entry.repo: entry.layer for entry in request.layer_map.repos}
        baseline = {entry.key(): entry for entry in request.baseline}
        seen_keys: set[tuple[str, str, str]] = set()
        findings: list[ModelValidationFindingEmbed] = []

        for file in sorted(request.files, key=lambda f: f.path):
            for channel, target, line, evidence in extract_references(
                file.path, file.source, request.layer_map, request.repo
            ):
                target_layer = layers[target]
                if target_layer < own.layer:
                    continue
                key = (file.path, channel.value, target)
                direction = "same layer as" if target_layer == own.layer else "above"
                message = (
                    f"{file.path}:{line}: {request.repo} (layer {own.layer}) depends on "
                    f"{target} (layer {target_layer}, {direction} it) via {channel.value}: "
                    f"{evidence}"
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
                            message=f"baselined ({recorded.ticket}): {message}",
                            remediation=_REMEDIATION,
                        )
                    )
                else:
                    findings.append(
                        ModelValidationFindingEmbed(
                            validator_id=VALIDATOR_ID,
                            severity="FAIL",
                            location=f"{file.path}:{line}",
                            message=message,
                            remediation=_REMEDIATION,
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
                        message=(
                            f"stale baseline entry ({entry.ticket}): {entry.path} no longer "
                            f"depends on {entry.target} via {entry.channel.value}; "
                            "remove it from the baseline"
                        ),
                        remediation=None,
                    )
                )

        return ModelValidationReport.from_findings(
            findings=tuple(findings),
            request=ModelValidationRequestRef(profile=_PROFILE),
            validators_run=(VALIDATOR_ID,),
        )
