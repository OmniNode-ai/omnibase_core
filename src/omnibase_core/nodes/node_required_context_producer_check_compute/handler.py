# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Required-context COMPUTE: immutable sources in, canonical report out."""

from typing import Literal

import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.required_context_producer_check.model_required_context_producer_check_input import (
    ModelRequiredContextProducerCheckInput,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_required_context_producer_check_compute.required_context_producer_rules import (
    VALIDATOR_ID,
    applies_to_base,
    manifest_rows,
    producer,
    retains_context,
    workflow_jobs,
)


class NodeRequiredContextProducerCheckCompute:
    """Refuse missing producers and unsanctioned retirement of base contexts."""

    def handle(
        self, request: ModelRequiredContextProducerCheckInput
    ) -> ModelValidationReport:
        """Compare both manifests with the head's workflow and job producers."""
        if request.runtime_errors:
            return ModelValidationReport.from_runtime_errors(
                VALIDATOR_ID, request.runtime_errors
            )
        findings: list[ModelValidationFinding] = []
        head_rows: tuple[dict[str, object], ...] = ()
        try:
            head_rows = manifest_rows(request.head_manifest_text)
        except (yaml.YAMLError, ValueError, ModelOnexError) as exc:
            findings.append(
                self._finding(
                    "ERROR",
                    "unparseable_manifest",
                    request.manifest_path,
                    f"ERROR: {request.manifest_path}: {exc}",
                )
            )
        base_rows: tuple[dict[str, object], ...] = ()
        if request.base_manifest_text is not None:
            try:
                base_rows = manifest_rows(request.base_manifest_text)
            except (yaml.YAMLError, ValueError, ModelOnexError) as exc:
                label = f"base {request.base_ref}:{request.manifest_path}"
                findings.append(
                    self._finding(
                        "ERROR",
                        "unparseable_manifest",
                        request.manifest_path,
                        f"ERROR: {label}: {exc}",
                    )
                )
        workflows: dict[str, frozenset[str]] = {}
        head_paths = {file.path for file in request.head_workflows}
        if not head_paths:
            findings.append(
                self._finding(
                    "ERROR",
                    "unparseable_manifest",
                    ".github/workflows",
                    "ERROR: zero workflow files supplied: ERROR, never PASS",
                )
            )
        for file in request.head_workflows:
            try:
                workflows[file.path] = workflow_jobs(file.source)
            except (yaml.YAMLError, ValueError, ModelOnexError) as exc:
                findings.append(
                    self._finding(
                        "ERROR",
                        "unparseable_manifest",
                        file.path,
                        f"ERROR: {file.path}: {exc}",
                    )
                )
        for row in head_rows:
            if row["mode"] != "REQUIRED":
                continue
            path, job = producer(row)
            if path not in head_paths:
                missing = f"workflow {path} is absent from the PR head (job {job!r})"
            elif path in workflows and job not in workflows[path]:
                missing = f"job {job!r} is absent from {path}"
            else:
                continue
            findings.append(
                self._finding(
                    "FAIL",
                    "producer_missing",
                    path,
                    f"FAIL: required context {row['name']!r} has no producer: {missing} (OMN-19037)",
                )
            )
        for row in base_rows:
            if row["mode"] != "REQUIRED" or not applies_to_base(row, request.base_ref):
                continue
            if any(
                head["name"] == row["name"] and retains_context(head)
                for head in head_rows
            ):
                continue
            path, job = producer(row)
            missing = (
                f" Base producer workflow {path} (job {job!r}) is also absent from the PR head."
                if path not in head_paths
                else ""
            )
            message = (
                f"FAIL: required context {row['name']!r} was dropped or downgraded; "
                "removal needs a RETIRED row citing the OMN ticket that flipped branch protection."
                f"{missing} (OMN-19037)"
            )
            findings.append(
                self._finding(
                    "FAIL", "required_context_dropped", request.manifest_path, message
                )
            )
        return ModelValidationReport.from_findings(
            findings=tuple(
                ModelValidationFindingEmbed(**finding.model_dump(mode="json"))
                for finding in findings
            ),
            request=ModelValidationRequestRef(profile="default"),
            validators_run=(VALIDATOR_ID,),
        )

    @staticmethod
    def _finding(
        severity: Literal["FAIL", "ERROR"], rule: str, path: str, message: str
    ) -> ModelValidationFinding:
        return ModelValidationFinding(
            validator_id=VALIDATOR_ID,
            severity=severity,
            rule_id=rule,
            location=f"{path}:1",
            message=f"{message} [{rule}]",
        )
