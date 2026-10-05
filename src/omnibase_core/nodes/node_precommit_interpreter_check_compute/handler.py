# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure validation of inline pre-commit config and shell sources."""

from __future__ import annotations

import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.precommit_interpreter_check.model_precommit_interpreter_check_input import (
    ModelPrecommitInterpreterCheckInput,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_precommit_interpreter_check_compute.matcher_precommit_interpreter import (
    VALIDATOR_ID,
    eligible_entries,
    referenced_scripts,
    scan_entry,
    scan_script,
)


class NodePrecommitInterpreterCheckCompute:
    """Preserve the infra script's findings and ten-hook non-vacuity floor."""

    def handle(
        self, request: ModelPrecommitInterpreterCheckInput
    ) -> ModelValidationReport:
        """Validate provided text without I/O or mutable node state."""
        findings: list[ModelValidationFinding] = []
        try:
            entries = eligible_entries(request.config.source)
        except (yaml.YAMLError, ModelOnexError) as exc:
            findings.append(
                ModelValidationFinding(
                    validator_id=VALIDATOR_ID,
                    severity="ERROR",
                    rule_id="invalid-config",
                    location=f"{request.config.path}:1",
                    message=f"ERROR: {request.config.path}: {exc}",
                )
            )
            entries = []
        if not findings and len(entries) < 10:
            findings.append(
                ModelValidationFinding(
                    validator_id=VALIDATOR_ID,
                    severity="ERROR",
                    rule_id="non-vacuity",
                    location=f"{request.config.path}:1",
                    message=f"ERROR: interpreter gate scanned only {len(entries)} local hooks "
                    "-- refusing to report a vacuous pass",
                )
            )
        if not findings:
            scripts = {file.path: file.source for file in request.scripts}
            seen_scripts: set[str] = set()
            for hook, entry, line in entries:
                for message in scan_entry(hook, entry):
                    findings.append(
                        ModelValidationFinding(
                            validator_id=VALIDATOR_ID,
                            severity="ERROR"
                            if "entry is not shell-parsable:" in message
                            else "FAIL",
                            rule_id="entry-interpreter",
                            location=f"{request.config.path}:{line}",
                            message=message,
                        )
                    )
                for path in referenced_scripts(entry, request.repository_root):
                    if path in seen_scripts or path not in scripts:
                        continue
                    seen_scripts.add(path)
                    for line_number, message in scan_script(path, scripts[path]):
                        findings.append(
                            ModelValidationFinding(
                                validator_id=VALIDATOR_ID,
                                severity="FAIL",
                                rule_id="script-interpreter",
                                location=f"{path}:{line_number}",
                                message=message,
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
