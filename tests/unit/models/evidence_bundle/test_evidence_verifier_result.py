# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Executed falsifiers for the evidence verifier result (OMN-18785)."""

from __future__ import annotations

from datetime import UTC, datetime
from itertools import permutations

import pytest
from pydantic import ValidationError

from omnibase_core.models.evidence_bundle import (
    ModelEvidenceVerifierCheck,
    ModelEvidenceVerifierResult,
    ModelStandardEvidenceBundle,
    ModelStandardRunManifest,
)
from omnibase_core.models.runtime.model_runtime_identity import ModelRuntimeIdentity

pytestmark = pytest.mark.unit

_NOW = datetime(2025, 1, 1, tzinfo=UTC)


def _identity() -> ModelRuntimeIdentity:
    return ModelRuntimeIdentity.model_validate(
        {
            "host": "test-host",
            "locus_kind": "container",
            "execution_locus": "verifier-container",
            "interpreter": "/usr/bin/python3",
            "packages": {
                "omnibase-core": {
                    "name": "omnibase-core",
                    "version": "1.0.0",
                    "source": "vcs",
                    "commit": "a" * 40,
                }
            },
            "stamped_at": _NOW,
        }
    )


def _check(
    name: str = "artifact_presence", *, ok: bool = True, indeterminate: bool = False
) -> dict[str, object]:
    return {
        "name": name,
        "ok": ok,
        "evidence": "Read the artifact manifest",
        "indeterminate": indeterminate,
    }


def _payload(*checks: dict[str, object]) -> dict[str, object]:
    return {
        "correlation_id": "verification-run",
        "verifier": _identity(),
        "checks": checks,
    }


@pytest.mark.parametrize("status", ["PASS", "FAIL", "ADVISORY", "PENDING"])
@pytest.mark.parametrize("ok", [True, False])
def test_status_is_never_an_input(status: str, ok: bool) -> None:
    # The old shape accepts both contradictions, including PASS with ok=False.
    payload = _payload(_check(ok=ok))
    payload.update(status=status, verifier="ci-verifier")
    with pytest.raises(ValidationError) as exc:
        ModelEvidenceVerifierResult.model_validate(payload)
    assert any(
        error["loc"] == ("status",) and error["type"] == "extra_forbidden"
        for error in exc.value.errors()
    )


def test_display_string_is_not_a_verifier_identity() -> None:
    payload = _payload(_check())
    payload.update(status="PASS", verifier="arbitrary display string")
    with pytest.raises(ValidationError) as exc:
        ModelEvidenceVerifierResult.model_validate(payload)
    assert any(error["loc"] == ("verifier",) for error in exc.value.errors())


@pytest.mark.parametrize("field", ["name", "ok", "evidence"])
@pytest.mark.parametrize("ok", [True, False])
def test_checks_require_typed_fields(field: str, ok: bool) -> None:
    check = _check(ok=ok)
    del check[field]
    with pytest.raises(ValidationError) as exc:
        ModelEvidenceVerifierResult.model_validate(_payload(check))
    assert any(
        error["loc"] == ("checks", 0, field) and error["type"] == "missing"
        for error in exc.value.errors()
    )


@pytest.mark.parametrize("field", ["name", "evidence"])
@pytest.mark.parametrize("value", ["", " \t\n", 1, None])
def test_check_text_is_nonempty(field: str, value: object) -> None:
    check = _check()
    check[field] = value
    with pytest.raises(ValidationError) as exc:
        ModelEvidenceVerifierResult.model_validate(_payload(check))
    assert any(error["loc"] == ("checks", 0, field) for error in exc.value.errors())


@pytest.mark.parametrize("field", ["ok", "indeterminate"])
@pytest.mark.parametrize("value", ["true", "false", 0, 1, None])
def test_check_booleans_are_strict(field: str, value: object) -> None:
    check = _check()
    check[field] = value
    with pytest.raises(ValidationError) as exc:
        ModelEvidenceVerifierResult.model_validate(_payload(check))
    assert any(error["loc"] == ("checks", 0, field) for error in exc.value.errors())


def test_passing_check_cannot_be_indeterminate() -> None:
    with pytest.raises(ValidationError, match="both passing and indeterminate"):
        ModelEvidenceVerifierResult.model_validate(
            _payload(_check(ok=True, indeterminate=True))
        )


@pytest.mark.parametrize("extra", [{"result": "pass"}, {"outcome": "PASS"}])
def test_check_rejects_untyped_or_caller_supplied_outcomes(
    extra: dict[str, str],
) -> None:
    check = _check()
    check.update(extra)
    with pytest.raises(ValidationError) as exc:
        ModelEvidenceVerifierResult.model_validate(_payload(check))
    assert any(
        error["loc"] == ("checks", 0, next(iter(extra)))
        and error["type"] == "extra_forbidden"
        for error in exc.value.errors()
    )


def test_zero_checks_cannot_produce_a_pass() -> None:
    with pytest.raises(ValidationError) as exc:
        ModelEvidenceVerifierResult.model_validate(_payload())
    assert any(
        error["loc"] == ("checks",) and error["type"] == "too_short"
        for error in exc.value.errors()
    )


def test_duplicate_check_names_are_refused() -> None:
    with pytest.raises(ValidationError, match="duplicate check names"):
        ModelEvidenceVerifierResult.model_validate(_payload(_check(), _check(ok=False)))


@pytest.mark.parametrize(
    ("ok", "indeterminate", "expected"),
    [(True, False, "PASS"), (False, False, "FAIL"), (False, True, "INDETERMINATE")],
)
def test_verdict_and_check_outcome_are_derived(
    ok: bool, indeterminate: bool, expected: str
) -> None:
    result = ModelEvidenceVerifierResult.model_validate(
        _payload(_check(ok=ok, indeterminate=indeterminate))
    )
    assert result.status.value == expected
    assert result.checks[0].outcome.value == expected
    assert result.checks[0].evidence == "Read the artifact manifest"
    assert result.verifier == _identity()
    serialized = result.model_dump(mode="json")
    assert serialized["status"] == expected
    assert serialized["checks"][0]["outcome"] == expected
    assert (
        ModelEvidenceVerifierResult.model_validate_json(
            result.model_dump_json(round_trip=True)
        )
        == result
    )


@pytest.mark.parametrize(
    ("checks", "expected"),
    [
        ((_check("present"), _check("hash")), "PASS"),
        (
            (_check("present"), _check("hash", ok=False, indeterminate=True)),
            "INDETERMINATE",
        ),
        (
            (
                _check("present"),
                _check("hash", ok=False, indeterminate=True),
                _check("contract", ok=False),
            ),
            "FAIL",
        ),
    ],
)
def test_aggregation_is_order_independent(
    checks: tuple[dict[str, object], ...], expected: str
) -> None:
    for ordered in permutations(checks):
        result = ModelEvidenceVerifierResult.model_validate(_payload(*ordered))
        assert result.status.value == expected
        assert tuple(check.name for check in result.checks) == tuple(
            check["name"] for check in ordered
        )


def test_bundle_constructs_and_round_trips_with_typed_verifier_result() -> None:
    result = ModelEvidenceVerifierResult.model_validate(_payload(_check()))
    bundle = ModelStandardEvidenceBundle(
        correlation_id=result.correlation_id,
        run_manifest=ModelStandardRunManifest(
            correlation_id=result.correlation_id,
            runner="test-runner",
            started_at=_NOW,
            expected_artifacts=("verifier_result.json",),
        ),
        verifier_result=result,
    )
    assert bundle.is_complete
    assert (
        ModelStandardEvidenceBundle.model_validate_json(
            bundle.model_dump_json(round_trip=True)
        )
        == bundle
    )


def test_verdict_and_typed_checks_are_frozen() -> None:
    result = ModelEvidenceVerifierResult.model_validate(_payload(_check()))
    with pytest.raises(ValidationError, match="frozen"):
        result.status = "FAIL"
    with pytest.raises(ValidationError, match="frozen"):
        result.checks[0].ok = False


def test_schema_marks_derived_status_read_only() -> None:
    validation = ModelEvidenceVerifierResult.model_json_schema()
    serialization = ModelEvidenceVerifierResult.model_json_schema(mode="serialization")
    assert "status" not in validation["properties"]
    assert serialization["properties"]["status"]["readOnly"] is True


@pytest.mark.parametrize("field", ["packages", "execution_locus", "stamped_at"])
def test_verifier_requires_existing_runtime_identity_fields(field: str) -> None:
    identity = _identity().model_dump(round_trip=True)
    del identity[field]
    payload = _payload(_check())
    payload["verifier"] = identity
    with pytest.raises(ValidationError) as exc:
        ModelEvidenceVerifierResult.model_validate(payload)
    assert any(error["loc"] == ("verifier", field) for error in exc.value.errors())


def test_typed_checks_construct_through_the_package_export() -> None:
    check = ModelEvidenceVerifierCheck(
        name="artifact_presence", ok=True, evidence="Read the artifact manifest"
    )
    result = ModelEvidenceVerifierResult(
        correlation_id="verification-run", verifier=_identity(), checks=(check,)
    )
    assert result.checks == (check,)
    assert result.status.value == "PASS"
