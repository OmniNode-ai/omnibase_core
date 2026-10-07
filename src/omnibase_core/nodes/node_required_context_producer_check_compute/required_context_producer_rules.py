# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure manifest parsing and producer coordinate resolution."""

import re
from typing import Final

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.required_context_producer_check.model_required_context_producer_manifest_fields import (
    ModelRequiredContextProducerManifestFields,
)
from omnibase_core.models.nodes.required_context_producer_check.model_required_context_producer_workflow_fields import (
    ModelRequiredContextProducerWorkflowFields,
)

VALIDATOR_ID: Final[str] = "required-context-producer"


def manifest_rows(text: str | None) -> tuple[dict[str, object], ...]:
    """Require a gates list and named, explicitly classified rows."""
    document = ModelRequiredContextProducerManifestFields.from_yaml(text)
    rows: list[dict[str, object]] = []
    for row in document.gates:
        if (
            not isinstance(row.get("name"), str)
            or not row["name"]
            or not isinstance(row.get("mode"), str)
        ):
            raise ModelOnexError(
                "each gate must have a context name and mode",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        if row["mode"] == "REQUIRED":
            producer(row)
        rows.append(row)
    return tuple(rows)


def producer(row: dict[str, object]) -> tuple[str, str]:
    """Resolve local callers, including the first segment of reusable job paths."""
    workflow = row.get("caller_workflow")
    job = row.get("caller_job")
    if workflow is None or job is None:
        workflow = row.get("workflow")
        job_path = row.get("job_path")
        job = job_path[0] if isinstance(job_path, list) and job_path else None
    if (
        not isinstance(workflow, str)
        or not workflow
        or not isinstance(job, str)
        or not job
    ):
        raise ModelOnexError(
            f"required context {row['name']!r} has invalid producer coordinates",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
    path = (
        workflow
        if workflow.startswith(".github/workflows/")
        else f".github/workflows/{workflow}"
    )
    return path, job


def workflow_jobs(text: str) -> frozenset[str]:
    """Parse workflow YAML and require a top-level jobs mapping."""
    return frozenset(ModelRequiredContextProducerWorkflowFields.from_yaml(text).jobs)


def applies_to_base(row: dict[str, object], base_ref: str | None) -> bool:
    """A ref without a branch segment protects every branch's required rows."""
    branch = base_ref.rsplit("/", 1)[1] if base_ref and "/" in base_ref else None
    return branch is None or row.get("branch") in (None, branch)


def retains_context(row: dict[str, object]) -> bool:
    """Accept REQUIRED or retirement citing the branch-protection change ticket."""
    rationale = row.get("rationale")
    return row["mode"] == "REQUIRED" or (
        row["mode"] == "RETIRED"
        and isinstance(rationale, str)
        and re.search(r"\bOMN-\d+\b", rationale) is not None
    )
