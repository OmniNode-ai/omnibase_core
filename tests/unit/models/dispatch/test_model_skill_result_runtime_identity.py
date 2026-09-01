# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelSkillResult must carry a runtime-identity stamp (OMN-17308).

RED-first suite for epic OMN-17306. Every assertion here fails before the
``runtime_identity`` field exists, because a receipt with no self-identification
is currently a perfectly valid receipt — which is precisely how the OMN-16932
probe produced a laptop-local result that read as a ``.201`` lane result.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from omnibase_core.enums.enum_execution_locus_kind import EnumExecutionLocusKind
from omnibase_core.enums.enum_package_source_kind import EnumPackageSourceKind
from omnibase_core.enums.enum_skill_result_status import EnumSkillResultStatus
from omnibase_core.models.dispatch.model_skill_result import (
    SKILL_RESULT_SCHEMA_VERSION,
    ModelSkillResult,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.models.runtime.model_package_identity import ModelPackageIdentity
from omnibase_core.models.runtime.model_runtime_identity import ModelRuntimeIdentity


class StubResult(BaseModel):
    """Concrete result model standing in for a skill's typed result."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    answer: str


def _identity() -> ModelRuntimeIdentity:
    return ModelRuntimeIdentity(
        host="probe-host",
        locus_kind=EnumExecutionLocusKind.VENV,
        execution_locus="/opt/venvs/onex",
        interpreter="/opt/venvs/onex/bin/python3.12",
        packages={
            "omnimarket": ModelPackageIdentity(
                name="omnimarket",
                version="0.4.11",
                commit="66b7131a3508000000000000000000000000abcd",
                source=EnumPackageSourceKind.VCS,
            ),
        },
        stamped_at=datetime(2026, 8, 31, 8, 10, 54, tzinfo=UTC),
    )


def _kwargs(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "skill_name": "delegate",
        "node_name": "node_delegate_skill_orchestrator",
        "status": EnumSkillResultStatus.SUCCESS,
        "correlation_id": uuid4(),
        "run_id": uuid4(),
        "exit_code": 0,
        "duration_ms": 1250,
        "result": StubResult(answer="alive"),
        "result_model": (
            "tests.unit.models.dispatch."
            "test_model_skill_result_runtime_identity.StubResult"
        ),
    }
    base.update(overrides)
    return base


@pytest.mark.unit
class TestRuntimeIdentityRequiredAtCurrentSchema:
    """A current-schema receipt cannot be built without self-identification."""

    def test_current_schema_receipt_without_identity_is_refused(self) -> None:
        """The core enforcement: unstamped receipts are UNCONSTRUCTABLE.

        Not "detected later" — refused at construction, so no code path can
        emit one and no artifact can carry one.
        """
        with pytest.raises(ValidationError) as excinfo:
            ModelSkillResult[StubResult](**_kwargs())  # type: ignore[arg-type]
        assert "runtime_identity" in str(excinfo.value)

    def test_current_schema_receipt_with_identity_is_accepted(self) -> None:
        receipt = ModelSkillResult[StubResult](
            **_kwargs(runtime_identity=_identity())  # type: ignore[arg-type]
        )
        assert receipt.runtime_identity is not None
        assert receipt.runtime_identity.host == "probe-host"

    def test_schema_version_advanced_to_the_requiring_version(self) -> None:
        """The bump is what makes the default construction path fail closed."""
        assert ModelSemVer(major=1, minor=1, patch=0) <= SKILL_RESULT_SCHEMA_VERSION


@pytest.mark.unit
class TestGrandfathering:
    """History is grandfathered by schema version, never rewritten."""

    def test_pre_requirement_receipt_still_validates(self) -> None:
        """A receipt stamped 1.0.0 predates the requirement and stays valid.

        Rewriting old receipts to add an identity they never had would
        manufacture the exact fiction this epic exists to stop. The honest
        record is "this receipt predates the requirement", and the schema
        version is what says so.
        """
        receipt = ModelSkillResult[StubResult](
            **_kwargs(schema_version=ModelSemVer(major=1, minor=0, patch=0))  # type: ignore[arg-type]
        )
        assert receipt.runtime_identity is None

    def test_grandfathered_receipt_round_trips_from_json(self) -> None:
        receipt = ModelSkillResult[StubResult](
            **_kwargs(schema_version=ModelSemVer(major=1, minor=0, patch=0))  # type: ignore[arg-type]
        )
        restored = ModelSkillResult[StubResult].model_validate_json(
            receipt.model_dump_json()
        )
        assert restored == receipt

    def test_stamped_receipt_round_trips_from_json(self) -> None:
        receipt = ModelSkillResult[StubResult](
            **_kwargs(runtime_identity=_identity())  # type: ignore[arg-type]
        )
        restored = ModelSkillResult[StubResult].model_validate_json(
            receipt.model_dump_json()
        )
        assert restored == receipt
        assert restored.runtime_identity == _identity()


class TestDocumentedExampleStaysExecutable:
    """The module's own docstring must not teach a pattern that raises.

    The 1.0.0 -> 1.1.0 bump silently invalidated the class docstring's example,
    which constructed a receipt with no ``runtime_identity``. Nothing collected
    doctests, so the documented example became un-runnable while still reading
    as authoritative — a docs-shaped instance of exactly the drift epic
    OMN-17306 exists to close (a surface asserting something the code no longer
    does). This test executes the docstring so the example is verified rather
    than assumed.
    """

    def test_module_doctests_execute_clean(self) -> None:
        import doctest

        from omnibase_core.models.dispatch import model_skill_result

        results = doctest.testmod(
            model_skill_result,
            verbose=False,
            optionflags=doctest.ELLIPSIS,
        )
        assert results.failed == 0, (
            f"{results.failed} of {results.attempted} doctest example(s) in "
            "model_skill_result failed — the documented construction pattern "
            "no longer matches the model's own validation rules."
        )
        assert results.attempted > 0, (
            "no doctest examples were executed; this guard would pass "
            "vacuously (OMN-14531 failure class)"
        )
