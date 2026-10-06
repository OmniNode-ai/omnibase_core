# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure exposed identifier gate over inline sources and a hash-only denylist."""

from omnibase_core.models.nodes.exposed_identifiers_check.model_exposed_identifiers_check_input import (
    ModelExposedIdentifiersCheckInput,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_exposed_identifiers_check_compute.denylist_failure import (
    DenylistError,
)
from omnibase_core.nodes.node_exposed_identifiers_check_compute.matcher_exposed_identifiers import (
    ANNOTATION_RE,
    VALIDATOR_ID,
    Denylist,
    is_scannable_source,
)


class NodeExposedIdentifiersCheckCompute:
    """Validate identifiers without filesystem, Git or runtime dependencies."""

    def handle(
        self, request: ModelExposedIdentifiersCheckInput
    ) -> ModelValidationReport:
        """Return one FAIL per oracle hit, or ERROR for malformed configuration."""
        try:
            denylist = Denylist.from_json(request.denylist_json)
        except DenylistError as exc:
            return ModelValidationReport.from_runtime_errors(VALIDATOR_ID, (str(exc),))
        findings: list[ModelValidationFinding] = []
        for file in request.files:
            if not is_scannable_source(file.path, file.source):
                continue
            # Lossless runtime transport preserves the binary prefix; the oracle
            # replaces invalid UTF-8 before matching the decoded lines.
            source = file.source.encode("utf-8", errors="surrogateescape").decode(
                "utf-8", errors="replace"
            )
            for lineno, line in enumerate(source.splitlines(), start=1):
                hits = denylist.scan_line(line)
                if ANNOTATION_RE.search(line):
                    continue
                for col, length, entry in hits:
                    findings.append(
                        ModelValidationFinding(
                            validator_id=VALIDATOR_ID,
                            severity="FAIL",
                            rule_id="exposed-identifier",
                            location=f"{file.path}:{lineno}:{col + 1}",
                            message=f"denylisted {entry.kind} (entry={entry.label} ticket={entry.ticket} match_len={length}) -- value withheld by design",
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
