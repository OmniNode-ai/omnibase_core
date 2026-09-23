# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-18928: terminal outcome and final-content verdict stay independent."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_delegation_content_verdict import (
    EnumDelegationContentVerdict,
)
from omnibase_core.enums.enum_delegation_operational_outcome import (
    EnumDelegationOperationalOutcome,
)
from omnibase_core.enums.enum_delegation_terminal_failure_cause import (
    EnumDelegationTerminalFailureCause,
)
from omnibase_core.models.delegation.wire.model_delegation_completed import (
    ModelDelegationCompleted,
)
from omnibase_core.models.delegation.wire.model_delegation_failed import (
    ModelDelegationFailed,
)
from omnibase_core.models.delegation.wire.model_delegation_result import (
    ModelDelegationResult,
)


def _terminal(**overrides: object) -> ModelDelegationResult:
    fields: dict[str, object] = {
        "correlation_id": uuid4(),
        "task_type": "document",
        "model_used": "provider/model",
        "endpoint_url": "https://example.invalid/v1",
        "content": "",
        "quality_passed": False,
        "quality_score": None,
        "latency_ms": 0,
        "fallback_to_claude": False,
        "operational_outcome": EnumDelegationOperationalOutcome.PROVIDER_QUOTA,
        "content_verdict": EnumDelegationContentVerdict.NOT_APPLICABLE,
        "terminal_failure_cause": (
            EnumDelegationTerminalFailureCause.PROVIDER_QUOTA_EXHAUSTED
        ),
    }
    fields.update(overrides)
    return ModelDelegationResult(**fields)  # type: ignore[arg-type]


def _construction_terminal(**overrides: object) -> ModelDelegationFailed:
    """Build the intentionally sparse carrier for a failed construction."""
    fields: dict[str, object] = {
        "correlation_id": uuid4(),
        "task_type": "document",
        "model_used": "provider/model",
        "endpoint_url": "https://example.invalid/v1",
        "content": "raw response whose final evidence did not survive",
        "quality_passed": True,
        "quality_score": None,
        "latency_ms": 0,
        "fallback_to_claude": False,
        "operational_outcome": (
            EnumDelegationOperationalOutcome.TERMINAL_CONSTRUCTION_FAILED
        ),
        "content_verdict": EnumDelegationContentVerdict.UNDETERMINED,
        "terminal_failure_reason": "terminal_construction_failed",
    }
    fields.update(overrides)
    return ModelDelegationFailed(**fields)  # type: ignore[arg-type]


def test_quota_terminal_is_not_model_content_failure() -> None:
    """A provider quota result has no final content to score."""
    terminal = _terminal()

    assert (
        terminal.operational_outcome is EnumDelegationOperationalOutcome.PROVIDER_QUOTA
    )
    assert terminal.content_verdict is EnumDelegationContentVerdict.NOT_APPLICABLE
    dumped = terminal.model_dump(mode="json")
    assert dumped["content_verdict"] == "not_applicable"
    assert "quality_score" not in dumped


def test_final_content_verdict_does_not_rewrite_attempt_history() -> None:
    """Missing final content does not erase prior-attempt evidence."""
    terminal = _terminal(
        escalation_history=(
            {
                "tier_name": "local",
                "model_used": "local/model",
                "quality_score": 0.8,
                "failure_reasons": [],
            },
        ),
    )

    assert terminal.content == ""
    assert terminal.content_verdict is EnumDelegationContentVerdict.NOT_APPLICABLE
    assert terminal.escalation_history[0]["model_used"] == "local/model"


def test_refusal_has_no_final_deliverable_but_preserves_its_gate_score() -> None:
    """A model refusal is distinct from no provider response or usable content."""
    terminal = _terminal(
        operational_outcome=EnumDelegationOperationalOutcome.REFUSED,
        content_verdict=EnumDelegationContentVerdict.NOT_APPLICABLE,
        content="NO",
        quality_score=0.0,
        terminal_failure_cause=None,
    )

    assert terminal.content_verdict is EnumDelegationContentVerdict.NOT_APPLICABLE
    assert terminal.quality_score == 0.0


def test_quota_terminal_cannot_claim_unusable_model_content() -> None:
    """Provider absence is not an unusable answer."""
    with pytest.raises(
        ValidationError, match="no-response outcome requires not_applicable"
    ):
        _terminal(content_verdict=EnumDelegationContentVerdict.UNUSABLE)


@pytest.mark.parametrize(
    ("outcome", "cause"),
    [
        (EnumDelegationOperationalOutcome.PROVIDER_UNAVAILABLE, None),
        (EnumDelegationOperationalOutcome.TIMEOUT, None),
        (EnumDelegationOperationalOutcome.CANCELLED, None),
    ],
)
def test_no_response_operational_terminal_has_no_numeric_quality(
    outcome: EnumDelegationOperationalOutcome,
    cause: EnumDelegationTerminalFailureCause | None,
) -> None:
    """Availability and lifecycle failures have no final content to score."""
    terminal = _terminal(
        operational_outcome=outcome,
        terminal_failure_cause=cause,
    )

    assert terminal.quality_score is None
    assert terminal.content_verdict is EnumDelegationContentVerdict.NOT_APPLICABLE
    assert "quality_score" not in terminal.model_dump(mode="json")


@pytest.mark.parametrize("outcome", [EnumDelegationOperationalOutcome.SCHEMA_REJECTED])
def test_malformed_final_content_is_unusable_but_still_scored(
    outcome: EnumDelegationOperationalOutcome,
) -> None:
    """A returned malformed schema is not an availability failure."""
    terminal = _terminal(
        operational_outcome=outcome,
        content_verdict=EnumDelegationContentVerdict.UNUSABLE,
        content="No, I cannot comply.",
        quality_score=1.0,
        terminal_failure_cause=None,
    )

    assert terminal.quality_score == 1.0
    assert terminal.content_verdict is EnumDelegationContentVerdict.UNUSABLE


@pytest.mark.parametrize(
    ("quality_passed", "content_verdict", "quality_score", "match"),
    [
        (
            True,
            EnumDelegationContentVerdict.UNUSABLE,
            0.4,
            "quality_passed requires usable",
        ),
        (False, EnumDelegationContentVerdict.NOT_APPLICABLE, 0.4, "requires unusable"),
        (False, EnumDelegationContentVerdict.UNUSABLE, None, "requires quality_score"),
    ],
)
def test_quality_rejected_requires_failed_scored_unusable_content(
    quality_passed: bool,
    content_verdict: EnumDelegationContentVerdict,
    quality_score: float | None,
    match: str,
) -> None:
    """A gate-rejected response is neither provider absence nor completion."""
    with pytest.raises(ValidationError, match=match):
        _terminal(
            operational_outcome=EnumDelegationOperationalOutcome.QUALITY_REJECTED,
            content_verdict=content_verdict,
            quality_passed=quality_passed,
            quality_score=quality_score,
            terminal_failure_cause=None,
        )


def test_clean_terminal_content_stays_usable_when_attempt_trace_has_preamble() -> None:
    """The returned content and retained provider trace are distinct facts."""
    terminal = _terminal(
        operational_outcome=EnumDelegationOperationalOutcome.COMPLETED,
        content_verdict=EnumDelegationContentVerdict.USABLE,
        content="Final answer",
        quality_passed=True,
        quality_score=1.0,
        preamble_chars=9,
        terminal_failure_cause=None,
    )

    assert terminal.content_verdict is EnumDelegationContentVerdict.USABLE
    assert terminal.preamble_chars == 9


def test_completed_unusable_content_cannot_claim_quality_acceptance() -> None:
    """Gate acceptance requires a usable final returned deliverable."""
    with pytest.raises(
        ValidationError, match="quality_passed requires usable content verdict"
    ):
        _terminal(
            operational_outcome=EnumDelegationOperationalOutcome.COMPLETED,
            content_verdict=EnumDelegationContentVerdict.UNUSABLE,
            content="Provider preamble followed by a partial answer",
            quality_passed=True,
            quality_score=1.0,
            terminal_failure_cause=None,
        )


@pytest.mark.parametrize(
    ("outcome", "verdict"),
    [
        (
            EnumDelegationOperationalOutcome.COMPLETED,
            EnumDelegationContentVerdict.USABLE,
        ),
        (
            EnumDelegationOperationalOutcome.QUALITY_REJECTED,
            EnumDelegationContentVerdict.UNUSABLE,
        ),
    ],
)
def test_evaluated_final_content_cannot_omit_quality_score(
    outcome: EnumDelegationOperationalOutcome,
    verdict: EnumDelegationContentVerdict,
) -> None:
    """Only a no-final-content verdict may omit numeric quality evidence."""
    with pytest.raises(ValidationError, match="evaluated content requires quality"):
        _terminal(
            operational_outcome=outcome,
            content_verdict=verdict,
            quality_passed=outcome is EnumDelegationOperationalOutcome.COMPLETED,
            quality_score=None,
            terminal_failure_cause=None,
        )


def test_new_classifications_must_arrive_as_a_pair() -> None:
    """A new producer cannot emit only one half of the terminal truth."""
    with pytest.raises(ValidationError, match="provided together"):
        _terminal(content_verdict=None)
    with pytest.raises(ValidationError, match="provided together"):
        _terminal(operational_outcome=None)


def test_legacy_terminal_omits_new_classifications_for_consumer_compatibility() -> None:
    """Released consumers can still parse a terminal produced before OMN-18928."""
    legacy = ModelDelegationFailed(
        correlation_id=uuid4(),
        task_type="document",
        model_used="none",
        endpoint_url="none",
        content="",
        quality_passed=False,
        quality_score=0.0,
        latency_ms=0,
        fallback_to_claude=False,
    )

    dumped = legacy.model_dump(mode="json")
    assert "operational_outcome" not in dumped
    assert "content_verdict" not in dumped


@pytest.mark.parametrize("quality_passed", [True, False])
def test_construction_failure_round_trips_without_invented_quality_evidence(
    quality_passed: bool,
) -> None:
    """The failed carrier preserves the actual gate bit but no discarded evidence."""
    terminal = _construction_terminal(quality_passed=quality_passed)

    restored = ModelDelegationResult.model_validate_json(terminal.model_dump_json())

    assert restored.correlation_id == terminal.correlation_id
    assert restored.content == terminal.content
    assert restored.quality_passed is quality_passed
    assert (
        restored.operational_outcome
        is EnumDelegationOperationalOutcome.TERMINAL_CONSTRUCTION_FAILED
    )
    assert restored.content_verdict is EnumDelegationContentVerdict.UNDETERMINED
    assert restored.terminal_failure_reason == "terminal_construction_failed"
    assert restored.quality_score is None


@pytest.mark.parametrize(
    "verdict",
    [
        EnumDelegationContentVerdict.NOT_APPLICABLE,
        EnumDelegationContentVerdict.USABLE,
        EnumDelegationContentVerdict.UNUSABLE,
        EnumDelegationContentVerdict.CORRECT,
    ],
)
def test_construction_failure_requires_undetermined_content_verdict(
    verdict: EnumDelegationContentVerdict,
) -> None:
    with pytest.raises(ValidationError, match="requires undetermined"):
        _construction_terminal(content_verdict=verdict)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("terminal_failure_reason", "", "stable terminal_failure_reason"),
        ("terminal_failure_reason", "different", "stable terminal_failure_reason"),
        ("quality_score", 0.9, "cannot carry quality_score"),
        ("required_quality_bar", 0.8, "cannot carry quality-bar evidence"),
        (
            "score_vs_required_bar",
            "at_or_above_bar",
            "cannot carry quality-bar evidence",
        ),
        (
            "failed_acceptance_criteria",
            ("criterion",),
            "cannot carry quality-rule evidence",
        ),
        (
            "rule_evaluations",
            (
                {
                    "rule": "criterion",
                    "enforcement": "blocking",
                    "passed": False,
                    "detail": "failed",
                },
            ),
            "cannot carry quality-rule evidence",
        ),
        (
            "response_contract_evidence",
            {
                "conveyed": True,
                "validated": True,
                "output_shape": "plain_text",
                "contract_sha256": "a" * 64,
                "channel": "response",
            },
            "cannot carry response-contract evidence",
        ),
        ("terminal_failure_cause", "provider_error", "cannot claim provider"),
    ],
)
def test_construction_failure_rejects_discarded_evidence(
    field: str, value: object, match: str
) -> None:
    with pytest.raises(ValidationError, match=match):
        _construction_terminal(**{field: value})


@pytest.mark.parametrize(
    "outcome",
    [
        EnumDelegationOperationalOutcome.COMPLETED,
        EnumDelegationOperationalOutcome.QUALITY_REJECTED,
        EnumDelegationOperationalOutcome.PROVIDER_QUOTA,
    ],
)
def test_undetermined_requires_construction_failure_outcome(
    outcome: EnumDelegationOperationalOutcome,
) -> None:
    with pytest.raises(ValidationError, match="undetermined content verdict requires"):
        _terminal(
            operational_outcome=outcome,
            content_verdict=EnumDelegationContentVerdict.UNDETERMINED,
            quality_passed=False,
            quality_score=None,
            terminal_failure_cause=None,
        )


def test_construction_failure_cannot_use_completed_terminal_class() -> None:
    with pytest.raises(ValidationError, match="must use failed terminal class"):
        ModelDelegationCompleted.model_validate(_construction_terminal().model_dump())


@pytest.mark.parametrize(
    "outcome",
    [
        value
        for value in EnumDelegationOperationalOutcome
        if value is not EnumDelegationOperationalOutcome.TERMINAL_CONSTRUCTION_FAILED
    ],
)
def test_failed_terminal_rejects_quality_pass_for_existing_outcomes(
    outcome: EnumDelegationOperationalOutcome,
) -> None:
    with pytest.raises(ValidationError):
        ModelDelegationFailed.model_validate(
            {
                "correlation_id": uuid4(),
                "task_type": "document",
                "model_used": "provider/model",
                "endpoint_url": "https://example.invalid/v1",
                "content": "response",
                "operational_outcome": outcome,
                "content_verdict": EnumDelegationContentVerdict.USABLE,
                "quality_passed": True,
                "quality_score": 1.0,
                "latency_ms": 0,
                "fallback_to_claude": False,
            }
        )


def test_terminal_schema_publishes_construction_failure_pair() -> None:
    schema = ModelDelegationResult.model_json_schema()
    rendered = str(schema)

    assert "terminal_construction_failed" in rendered
    assert "undetermined" in rendered
