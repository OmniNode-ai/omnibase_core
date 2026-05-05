# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Per-file contract validator with mode selection (OMN-9768, parent OMN-9757).

Phase 3 — central seam tying corpus classification + per-family
normalization to strict Pydantic validation. Replaces ad-hoc per-call
validation paths so both the strict CI gate and the migration_audit
batch sweep funnel through one entry point.

Two modes (:class:`omnibase_core.enums.enum_validator_mode.EnumValidatorMode`):

- ``STRICT`` — no normalization; node-root contracts validate against
  the canonical typed contract model (``extra="forbid"``). Fails
  immediately on legacy shapes. Used by CI for new/edited contracts.
- ``MIGRATION_AUDIT`` — runs :func:`compose_normalization_pipeline`
  first, then validates; ``normalized=True`` on the report. Used for
  batch sweeps over the legacy corpus to inventory substantive
  validation failures separate from pre-existing schema debt.

Non-node-root buckets (handler / package / integration / etc.) skip
validation entirely and return a passed report with the bucket
recorded for downstream aggregation. Unknown ``node_type`` returns a
failed report.

Strict-mode pre-check: this validator asserts presence of
``algorithm`` (COMPUTE) / ``io_operations`` (EFFECT, non-empty list)
*before* calling ``model_validate``. Today the canonical models
already require those fields, so the pre-check is redundant. After
Task 13 (OMN-9770) makes them optional in the model, this pre-check
preserves the strict-mode invariant that those fields are mandatory
for new/edited contracts. The pre-check is intentionally NOT applied
in ``MIGRATION_AUDIT`` mode — that mode is for inventorying corpus
debt, not enforcing schema rules.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_validator_mode import EnumValidatorMode
from omnibase_core.models.contracts.model_corpus_validation_report import (
    ModelCorpusValidationReport,
)
from omnibase_core.normalization.contract_normalizer import (
    compose_normalization_pipeline,
)
from omnibase_core.normalization.corpus_classifier import classify_contract_path

# Lazy-loaded mapping of canonical node_type values → canonical contract
# model class. Built once on first call to keep the module import-light
# and to avoid forcing the full contract model graph at module load time
# (the contract models pull in a non-trivial dependency closure).
_NODE_TYPE_TO_MODEL_CACHE: dict[str, type[BaseModel]] = {}


def _get_model_registry() -> dict[str, type[BaseModel]]:
    if not _NODE_TYPE_TO_MODEL_CACHE:
        from omnibase_core.models.contracts.model_contract_compute import (
            ModelContractCompute,
        )
        from omnibase_core.models.contracts.model_contract_effect import (
            ModelContractEffect,
        )
        from omnibase_core.models.contracts.model_contract_orchestrator import (
            ModelContractOrchestrator,
        )
        from omnibase_core.models.contracts.model_contract_reducer import (
            ModelContractReducer,
        )

        _NODE_TYPE_TO_MODEL_CACHE.update(
            {
                "EFFECT_GENERIC": ModelContractEffect,
                "COMPUTE_GENERIC": ModelContractCompute,
                "REDUCER_GENERIC": ModelContractReducer,
                "ORCHESTRATOR_GENERIC": ModelContractOrchestrator,
            }
        )
    return _NODE_TYPE_TO_MODEL_CACHE


# Short aliases written by older tooling resolved to canonical
# EnumNodeType wire values. Resolution is one-way (alias → canonical)
# and does not mutate the caller's dict.
_NODE_TYPE_ALIASES: dict[str, str] = {
    "EFFECT": "EFFECT_GENERIC",
    "COMPUTE": "COMPUTE_GENERIC",
    "REDUCER": "REDUCER_GENERIC",
    "ORCHESTRATOR": "ORCHESTRATOR_GENERIC",
}


def _strict_field_precheck_errors(
    canonical_node_type: str, raw: dict[str, object]
) -> list[str]:
    """Return strict-mode pre-check errors for ``algorithm`` / ``io_operations``.

    Empty list means the pre-check passed. Only invoked in STRICT mode.
    """
    errors: list[str] = []
    if canonical_node_type == "COMPUTE_GENERIC":
        if "algorithm" not in raw:
            errors.append(
                "strict-mode pre-check: COMPUTE_GENERIC contract is missing required "
                "'algorithm' field"
            )
    elif canonical_node_type == "EFFECT_GENERIC":
        io_ops = raw.get("io_operations")
        if "io_operations" not in raw:
            errors.append(
                "strict-mode pre-check: EFFECT_GENERIC contract is missing required "
                "'io_operations' field"
            )
        elif not isinstance(io_ops, list) or len(io_ops) == 0:
            errors.append(
                "strict-mode pre-check: EFFECT_GENERIC contract requires non-empty "
                "'io_operations' list"
            )
    return errors


def validate_contract_file(
    path: Path,
    mode: EnumValidatorMode = EnumValidatorMode.STRICT,
) -> ModelCorpusValidationReport:
    """Validate a single contract YAML file under the chosen mode.

    Args:
        path: Filesystem path to the contract YAML. Must exist and be readable.
        mode: ``STRICT`` (default) or ``MIGRATION_AUDIT``. See module docstring
            for the contract of each mode.

    Returns:
        :class:`ModelCorpusValidationReport` recording the bucket, mode, pass /
        fail outcome, error strings, and whether normalization was applied.

    The report is the unit of evidence the batch validator (Task 12) and the
    Track 2 ``runtime_contract_config_loader`` (OMN-9747) collect into
    aggregate sweeps; this function is the single entry point so both paths
    apply identical classification / normalization / validation logic.
    """
    raw_text = path.read_text()
    loaded = yaml.safe_load(raw_text)
    raw: dict[str, object] = loaded if isinstance(loaded, dict) else {}

    classification = classify_contract_path(path, raw=raw)

    # Non-node-root buckets are out of scope for typed model validation.
    # Record the bucket and pass through; aggregators downstream still need
    # the row so they can count files-by-bucket.
    if not classification.requires_validation:
        return ModelCorpusValidationReport(
            path=path,
            bucket=classification.bucket,
            mode=mode,
            passed=True,
            errors=[],
            normalized=False,
        )

    normalized = False
    if mode is EnumValidatorMode.MIGRATION_AUDIT:
        raw = compose_normalization_pipeline(raw)
        normalized = True

    raw_node_type = raw.get("node_type", "")
    raw_node_type_str = raw_node_type if isinstance(raw_node_type, str) else ""
    canonical_node_type = _NODE_TYPE_ALIASES.get(raw_node_type_str, raw_node_type_str)
    model_cls = _get_model_registry().get(canonical_node_type)

    if model_cls is None:
        return ModelCorpusValidationReport(
            path=path,
            bucket=classification.bucket,
            mode=mode,
            passed=False,
            errors=[
                f"Unknown or unmapped node_type: {raw_node_type_str!r}"
                if raw_node_type_str
                else "Missing required 'node_type' field"
            ],
            normalized=normalized,
        )

    # Strict-mode pre-check enforces algorithm / io_operations even after
    # Task 13 makes them optional in the model. Migration-audit mode skips
    # the pre-check; surfacing only what the model itself rejects is the
    # whole point of the audit pass.
    if mode is EnumValidatorMode.STRICT:
        precheck_errors = _strict_field_precheck_errors(canonical_node_type, raw)
        if precheck_errors:
            return ModelCorpusValidationReport(
                path=path,
                bucket=classification.bucket,
                mode=mode,
                passed=False,
                errors=precheck_errors,
                normalized=normalized,
            )

    try:
        model_cls.model_validate(raw)
        return ModelCorpusValidationReport(
            path=path,
            bucket=classification.bucket,
            mode=mode,
            passed=True,
            errors=[],
            normalized=normalized,
        )
    except ValidationError as exc:
        return ModelCorpusValidationReport(
            path=path,
            bucket=classification.bucket,
            mode=mode,
            passed=False,
            errors=[str(e) for e in exc.errors()],
            normalized=normalized,
        )


__all__ = ["validate_contract_file"]
