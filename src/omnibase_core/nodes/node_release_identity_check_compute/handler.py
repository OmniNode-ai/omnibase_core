# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Release-identity COMPUTE: typed facts in, canonical ValidationReport out."""

from typing import Literal

from packaging.version import Version

from omnibase_core.models.nodes.release_identity_check.model_release_identity_check_input import (
    ModelReleaseIdentityCheckInput,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_release_identity_check_compute.release_identity_rules import (
    VALIDATOR_ID,
    latest_published_version,
    packaged_source_changed,
    version_error,
)


class NodeReleaseIdentityCheckCompute:
    """Pure release-version comparison matching the core script."""

    def handle(self, request: ModelReleaseIdentityCheckInput) -> ModelValidationReport:
        """Preserve configuration, exemption and bump decision order."""
        findings: list[ModelValidationFinding] = []
        error = version_error(request)
        if error is not None:
            rule = (
                "no_pyproject_version"
                if not request.pyproject_version_raw
                else "malformed_pyproject_version"
            )
            findings.append(self._finding(request, "ERROR", rule, error))
        else:
            version = Version(str(request.pyproject_version_raw))
            latest = latest_published_version(request.published_tags)
            if (
                latest is not None
                and packaged_source_changed(request.changed_files)
                and version <= latest
            ):
                message = (
                    "FAIL: packaged source changed but pyproject version "
                    f"{version} is NOT ahead of the latest published version "
                    f"{latest} (OMN-13411 release-identity gate)."
                )
                remediation = (
                    "Merging code consumers import onto an already-published version aliases "
                    "two code states under one wheel version. Bump project.version in "
                    f"pyproject.toml past {latest} (e.g. "
                    f"{Version(f'{latest.major}.{latest.minor}.{latest.micro + 1}')})."
                )
                findings.append(
                    self._finding(
                        request, "FAIL", "version_not_ahead", message, remediation
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
        request: ModelReleaseIdentityCheckInput,
        severity: Literal["FAIL", "ERROR"],
        rule: str,
        message: str,
        remediation: str | None = None,
    ) -> ModelValidationFinding:
        return ModelValidationFinding(
            validator_id=VALIDATOR_ID,
            severity=severity,
            rule_id=rule,
            location=f"{request.pyproject_path}:1",
            message=message,
            remediation=remediation,
        )
