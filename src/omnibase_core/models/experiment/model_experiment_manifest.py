# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Experiment manifest: the frozen success contract with its rule hash (OMN-22001)."""

import hashlib
import json
from typing import ClassVar
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_experiment_estimator import EnumExperimentEstimator
from omnibase_core.enums.enum_experiment_slot import EnumExperimentSlot
from omnibase_core.enums.enum_experiment_subject_kind import EnumExperimentSubjectKind
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.experiment.model_manifest_evidence_source import (
    ModelManifestEvidenceSource,
)
from omnibase_core.models.experiment.model_manifest_guardrail import (
    ModelManifestGuardrail,
)
from omnibase_core.models.experiment.model_manifest_metric_formula import (
    ModelManifestMetricFormula,
)
from omnibase_core.models.experiment.model_manifest_safety_condition import (
    ModelManifestSafetyCondition,
)
from omnibase_core.models.experiment.model_manifest_transition import (
    ModelManifestTransition,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

_RESOLVABLE: tuple[str, ...] = (
    "eligible_cohort_rule",
    "intake_source_ref",
    "enrollment_cutoff",
    "due_cutoff",
    "maturity_cutoff",
    "exclusions",
    "changed_scope_rule",
    "evidence_sources",
    "provenance_rule",
    "coverage_floor",
    "cohort_floor",
    "freshness_max_age_hours",
    "baseline_snapshot_ref",
    "baseline_rate",
    "metric_formulas",
    "comparison_rule",
    "rounding_rule",
    "target_rate",
    "guardrails",
    "safety_fail_conditions",
    "missing_rule",
    "late_rule",
    "duplicate_rule",
    "permitted_transitions",
)


class ModelExperimentManifest(BaseModel):
    """Everything the evaluator needs to judge one experiment, or the gaps that block it.

    Freezing is the MASS rule: ``rule_sha`` hashes every other value before any
    treatment outcome is read, and a changed value is a new experiment. A value the
    approved configuration has not set stays ``None`` and blocks evaluation:
    ``unresolved_fields`` names it, ``is_resolved`` is False and
    ``require_resolved`` raises. An empty tuple is a declared "none", not a gap.

    The manifest declares its ``estimator``; the comparison compute dispatches on it.

    Attributes:
        experiment_id: Identity of the experiment.
        subject_kind: What the experiment is about.
        estimator: Estimator the comparison compute dispatches on.
        slot: Origin slot, for retrospective experiments.
        manifest_version: Version of this manifest.
        evaluator_version: Evaluator version the manifest was frozen against.
        frozen_at: When the manifest was frozen, before treatment outcomes were read.
        rule_sha: SHA-256 of every other value (64 lowercase hex).
        eligible_cohort_rule: Who is eligible, in words.
        intake_source_ref: The cohort's independent intake source.
        enrollment_cutoff: Last moment a unit may enrol.
        due_cutoff: Moment a unit falls due.
        maturity_cutoff: Moment a unit's outcome counts.
        exclusions: Exclusion rules; empty when none apply.
        changed_scope_rule: How a changed scope is handled.
        evidence_sources: Evidence schemas with their source snapshots and hashes.
        provenance_rule: The provenance every record must carry.
        coverage_floor: Capture coverage needed to trust the measurement (0 to 1).
        cohort_floor: Minimum number of eligible due units.
        freshness_max_age_hours: Oldest evidence, in hours, that still counts.
        baseline_snapshot_ref: Reference to the baseline snapshot.
        baseline_rate: Primary-endpoint rate of the baseline snapshot.
        metric_formulas: Formula of every metric.
        comparison_rule: How treatment is compared with the target.
        rounding_rule: How values are rounded before comparison.
        target_rate: Primary-endpoint rate the treatment must not exceed.
        guardrails: Guardrail bounds.
        safety_fail_conditions: Predeclared safety-failure conditions.
        missing_rule: How missing evidence is treated.
        late_rule: How late evidence is treated.
        duplicate_rule: How duplicate evidence is treated.
        permitted_transitions: Lifecycle transitions the experiment may take.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    experiment_id: UUID
    subject_kind: EnumExperimentSubjectKind
    estimator: EnumExperimentEstimator
    slot: EnumExperimentSlot | None = None
    manifest_version: ModelSemVer
    evaluator_version: ModelSemVer
    frozen_at: AwareDatetime
    rule_sha: str = Field(pattern=r"^[0-9a-f]{64}$")
    eligible_cohort_rule: str | None = Field(default=None, min_length=1)
    intake_source_ref: str | None = Field(default=None, min_length=1)
    enrollment_cutoff: AwareDatetime | None = None
    due_cutoff: AwareDatetime | None = None
    maturity_cutoff: AwareDatetime | None = None
    exclusions: tuple[str, ...] | None = None
    changed_scope_rule: str | None = Field(default=None, min_length=1)
    evidence_sources: tuple[ModelManifestEvidenceSource, ...] | None = None
    provenance_rule: str | None = Field(default=None, min_length=1)
    coverage_floor: float | None = Field(default=None, ge=0.0, le=1.0)
    cohort_floor: int | None = Field(default=None, ge=1)
    freshness_max_age_hours: int | None = Field(default=None, ge=0)
    baseline_snapshot_ref: str | None = Field(default=None, min_length=1)
    baseline_rate: float | None = Field(default=None, ge=0.0)
    metric_formulas: tuple[ModelManifestMetricFormula, ...] | None = None
    comparison_rule: str | None = Field(default=None, min_length=1)
    rounding_rule: str | None = Field(default=None, min_length=1)
    target_rate: float | None = Field(default=None, ge=0.0)
    guardrails: tuple[ModelManifestGuardrail, ...] | None = None
    safety_fail_conditions: tuple[ModelManifestSafetyCondition, ...] | None = None
    missing_rule: str | None = Field(default=None, min_length=1)
    late_rule: str | None = Field(default=None, min_length=1)
    duplicate_rule: str | None = Field(default=None, min_length=1)
    permitted_transitions: tuple[ModelManifestTransition, ...] | None = None

    _RESOLVABLE_NAMES: ClassVar[tuple[str, ...]] = _RESOLVABLE

    @classmethod
    def resolvable_fields(cls) -> tuple[str, ...]:
        """Names of the values that may be unresolved, in declaration order."""
        return cls._RESOLVABLE_NAMES

    def unresolved_fields(self) -> tuple[str, ...]:
        """Names of the contract values that are still unset, in declaration order."""
        return tuple(
            name for name in self._RESOLVABLE_NAMES if getattr(self, name) is None
        )

    @property
    def is_resolved(self) -> bool:
        """True only when no contract value is unresolved."""
        return not self.unresolved_fields()

    def require_resolved(self) -> None:
        """Raise unless every contract value is resolved. Evaluation calls this first."""
        unresolved = self.unresolved_fields()
        if unresolved:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="manifest has unresolved values: " + ", ".join(unresolved),
            )

    def computed_rule_sha(self) -> str:
        """SHA-256 of the canonical JSON of every value except ``rule_sha``."""
        canonical = json.dumps(
            self.model_dump(mode="json", exclude={"rule_sha"}),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def rule_sha_matches(self) -> bool:
        """True when ``rule_sha`` is the hash of this manifest's values."""
        return self.rule_sha == self.computed_rule_sha()
