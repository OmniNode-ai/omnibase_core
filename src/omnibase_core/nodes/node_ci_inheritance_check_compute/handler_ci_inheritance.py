# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""HandlerCiInheritance — shared CI is inherited from the host only.

RULING 2026-10-14T20:01:09Z (OMN-17427): "all CI should be in core and
everything should essentially inherit from that." A repository inherits CI
through ``uses: <org>/<repo>/...`` lines: a reusable workflow call at job
level, or a composite action at step level. This node refuses a change that
ADDS such a reference to an organization repository other than the host, so
the CI that lives outside core can only shrink. References the base already
carries are reported as WARN: moving them into core is later work of the plan,
and this check never lists them as allowed.

Architecture: pure COMPUTE handler — deterministic, no I/O. Workflow text
arrives as explicit (path, source) pairs for the base and the head, with the
rule data (reference pattern, finding messages) read from
``contracts/ci_inheritance.validation.yaml`` and carried on the request; the
filesystem read happens at the CLI boundary
(:mod:`omnibase_core.nodes.node_ci_inheritance_check_compute.runtime_ci_inheritance_check`)
through ``node_source_file_gather_effect``. It lives in omnibase_core, the CI
host the ruling names. The scan is line based, not a YAML parse, so a comment
line is never read as a reference.
"""

from __future__ import annotations

import re
from typing import Final, Literal

from omnibase_core.models.nodes.ci_inheritance_check.model_ci_inheritance_reference_input import (
    ModelCiInheritanceReferenceInput,
)
from omnibase_core.models.nodes.ci_inheritance_check.model_ci_org_reference import (
    ModelCiOrgReference,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)

__all__ = [
    "VALIDATOR_ID",
    "HandlerCiInheritance",
    "extract_org_references",
]

VALIDATOR_ID: Final[str] = "ci_inheritance_check"

_PROFILE: Final[Literal["strict", "default", "advisory"]] = "default"


def extract_org_references(
    source: str, organization: str, uses_pattern: str
) -> list[ModelCiOrgReference]:
    """Return every non-comment `uses:` reference to ``organization``'s repositories."""
    uses_re = re.compile(uses_pattern)
    org_cf = organization.casefold()
    refs: list[ModelCiOrgReference] = []
    for number, line in enumerate(source.splitlines(), start=1):
        if line.lstrip().startswith("#"):
            continue
        match = uses_re.match(line)
        if match is None:
            continue
        target = match.group("value").split("@", 1)[0]
        parts = target.split("/")
        if len(parts) < 2 or parts[0].casefold() != org_cf:
            continue
        refs.append(
            ModelCiOrgReference(line=number, repository=parts[1], target=target)
        )
    return refs


class HandlerCiInheritance:
    """Refuse new CI references to a repository other than the host."""

    def handle(
        self, request: ModelCiInheritanceReferenceInput
    ) -> ModelValidationReport:
        """Definition-B canonical entry-point (OMN-14355). Pure, no I/O, no clock."""
        check = request.check
        rules = request.rules
        host_cf = check.host_repository.casefold()

        base_targets: set[str] = set()
        for file in check.base_files:
            for ref in extract_org_references(
                file.source, check.organization, rules.uses_pattern
            ):
                if ref.repository.casefold() != host_cf:
                    base_targets.add(ref.target.casefold())

        findings: list[ModelValidationFinding] = []
        for file in sorted(check.head_files, key=lambda f: f.path):
            for ref in extract_org_references(
                file.source, check.organization, rules.uses_pattern
            ):
                if ref.repository.casefold() == host_cf:
                    continue
                location = f"{file.path}:{ref.line}"
                if ref.target.casefold() in base_targets:
                    findings.append(
                        ModelValidationFinding(
                            validator_id=VALIDATOR_ID,
                            severity="WARN",
                            location=location,
                            message=rules.existing_reference_message.format(
                                location=location,
                                target=ref.target,
                                host=check.host_repository,
                            ),
                            remediation=None,
                        )
                    )
                    continue
                findings.append(
                    ModelValidationFinding(
                        validator_id=VALIDATOR_ID,
                        severity="FAIL",
                        location=location,
                        message=rules.new_reference_message.format(
                            location=location,
                            target=ref.target,
                            host=check.host_repository,
                        ),
                        remediation=rules.new_reference_remediation.format(
                            organization=check.organization,
                            host=check.host_repository,
                        ),
                    )
                )

        embedded = tuple(
            ModelValidationFindingEmbed(**finding.model_dump(mode="json"))
            for finding in findings
        )
        return ModelValidationReport.from_findings(
            findings=embedded,
            request=ModelValidationRequestRef(profile=_PROFILE),
            validators_run=(VALIDATOR_ID,),
        )
