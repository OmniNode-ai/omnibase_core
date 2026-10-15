# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the context-source contract models (OMN-18531 / TC.1)."""

import hashlib
from datetime import UTC, datetime
from enum import StrEnum

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_context_factor import EnumContextFactor
from omnibase_core.enums.enum_context_source_error_code import (
    EnumContextSourceErrorCode,
)
from omnibase_core.enums.enum_context_source_status import EnumContextSourceStatus
from omnibase_core.enums.enum_context_span_unit import EnumContextSpanUnit
from omnibase_core.enums.enum_context_supersession_status import (
    EnumContextSupersessionStatus,
)
from omnibase_core.models.context.model_context_access import ModelContextAccess
from omnibase_core.models.context.model_context_caller_scope import (
    ModelContextCallerScope,
)
from omnibase_core.models.context.model_context_source_entry import (
    ModelContextSourceEntry,
)
from omnibase_core.models.context.model_context_source_request import (
    ModelContextSourceRequest,
)
from omnibase_core.models.context.model_context_source_result import (
    ModelContextSourceResult,
)
from omnibase_core.models.context.model_context_source_span import (
    ModelContextSourceSpan,
)

AS_OF = datetime(2026, 10, 15, 5, 0, tzinfo=UTC)
TEXT = "Do not deploy without approval."


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _entry(**overrides: object) -> ModelContextSourceEntry:
    fields: dict[str, object] = {
        "factor": EnumContextFactor.CLAUDE_MD,
        "text": TEXT,
        "text_sha256": _sha(TEXT),
        "status": EnumContextSourceStatus.RESOLVED,
        "as_of": AS_OF,
    }
    fields.update(overrides)
    return ModelContextSourceEntry.model_validate(fields)


def _span() -> ModelContextSourceSpan:
    return ModelContextSourceSpan(unit=EnumContextSpanUnit.LINE, start=3, end=4)


@pytest.mark.unit
class TestEnums:
    def test_status_has_the_six_plan_values(self) -> None:
        assert issubclass(EnumContextSourceStatus, StrEnum)
        assert {m.value for m in EnumContextSourceStatus} == {
            "resolved",
            "unresolved",
            "ambiguous",
            "stale",
            "denied",
            "unavailable",
        }

    def test_supersession_values(self) -> None:
        assert [m.value for m in EnumContextSupersessionStatus] == [
            "active",
            "superseded",
            "amended",
            "corrected",
            "unknown",
        ]


@pytest.mark.unit
class TestFrozenAndForbid:
    @pytest.mark.parametrize(
        "model",
        [
            ModelContextCallerScope,
            ModelContextAccess,
            ModelContextSourceSpan,
            ModelContextSourceEntry,
            ModelContextSourceRequest,
            ModelContextSourceResult,
        ],
    )
    def test_config(self, model: type) -> None:
        assert model.model_config["frozen"] is True
        assert model.model_config["extra"] == "forbid"

    def test_entry_is_immutable(self) -> None:
        entry = _entry()
        with pytest.raises(ValidationError):
            entry.__setattr__("text", "other")

    def test_entry_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError):
            _entry(surprise=1)


@pytest.mark.unit
class TestEntryHash:
    def test_matching_hash_validates(self) -> None:
        assert _entry().text_sha256 == _sha(TEXT)

    def test_mismatched_hash_fails(self) -> None:
        with pytest.raises(ValidationError, match="does not match"):
            _entry(text_sha256=_sha("different text"))

    def test_malformed_hash_fails(self) -> None:
        with pytest.raises(ValidationError):
            _entry(text_sha256="not-a-hash")


@pytest.mark.unit
class TestVerbatimVerified:
    def test_without_source_ref_or_span_fails(self) -> None:
        with pytest.raises(ValidationError, match="source_ref and span"):
            _entry(verbatim_verified=True)

    def test_with_source_ref_only_fails(self) -> None:
        with pytest.raises(ValidationError, match="source_ref and span"):
            _entry(verbatim_verified=True, source_ref="CLAUDE.md@abc123")

    def test_with_span_only_fails(self) -> None:
        with pytest.raises(ValidationError, match="source_ref and span"):
            _entry(verbatim_verified=True, span=_span())

    def test_with_both_validates(self) -> None:
        entry = _entry(
            verbatim_verified=True, source_ref="CLAUDE.md@abc123", span=_span()
        )
        assert entry.verbatim_verified is True

    def test_cannot_also_be_a_paraphrase(self) -> None:
        with pytest.raises(ValidationError, match="paraphrase"):
            _entry(
                verbatim_verified=True,
                paraphrase=True,
                source_ref="CLAUDE.md@abc123",
                span=_span(),
            )

    def test_unverified_defaults(self) -> None:
        entry = _entry()
        assert entry.verbatim_verified is False
        assert entry.supersession_status is EnumContextSupersessionStatus.UNKNOWN


@pytest.mark.unit
class TestSpan:
    def test_end_before_start_fails(self) -> None:
        with pytest.raises(ValidationError, match="before start"):
            ModelContextSourceSpan(unit=EnumContextSpanUnit.CHARACTER, start=5, end=2)


@pytest.mark.unit
class TestCallerScope:
    def test_every_field_is_optional(self) -> None:
        scope = ModelContextCallerScope()
        assert scope.task_class is None
        assert scope.request_paths == ()
        assert scope.cited_ruling_stamps == ()

    def test_carries_the_named_fields(self) -> None:
        scope = ModelContextCallerScope(
            task_class="compaction",
            node_archetype="effect",
            request_paths=("a/b.py",),
            repository="omnibase_core",
            lane="omn18531-tc1",
            lane_kind="build",
            cited_ruling_stamps=("2026-10-15T03:37:58Z",),
            cited_plan_paths=("beta/plans/x.md",),
            ticket="OMN-18531",
        )
        assert scope.ticket == "OMN-18531"


@pytest.mark.unit
class TestAccessAndRequest:
    def _request(self, **overrides: object) -> ModelContextSourceRequest:
        fields: dict[str, object] = {
            "factor": EnumContextFactor.CLAUDE_MD,
            "access": ModelContextAccess(tenant_id="lab"),
            "revision": "abc123",
        }
        fields.update(overrides)
        return ModelContextSourceRequest.model_validate(fields)

    def test_valid_request(self) -> None:
        request = self._request(scopes=("process",), task_kind="lane_brief")
        assert request.access.tenant_id == "lab"
        assert request.access.principal_authenticated is False
        assert request.caller_scope == ModelContextCallerScope()

    def test_refuses_construction_without_access(self) -> None:
        with pytest.raises(ValidationError, match="access"):
            ModelContextSourceRequest.model_validate(
                {"factor": EnumContextFactor.CLAUDE_MD, "revision": "abc123"}
            )

    def test_access_without_tenant_id_fails(self) -> None:
        with pytest.raises(ValidationError, match="tenant_id"):
            ModelContextAccess.model_validate({})

    def test_access_with_blank_tenant_id_fails(self) -> None:
        with pytest.raises(ValidationError, match="tenant_id"):
            ModelContextAccess(tenant_id="")

    def test_request_refuses_blank_revision(self) -> None:
        with pytest.raises(ValidationError, match="revision"):
            self._request(revision="")


@pytest.mark.unit
class TestResult:
    def test_carries_paging_counts_and_timings(self) -> None:
        result = ModelContextSourceResult(
            status=EnumContextSourceStatus.RESOLVED,
            entries=(_entry(),),
            has_more=True,
            entry_counts={"git": 1},
            leg_timings_ms={"read": 12, "verify": 3},
        )
        assert result.has_more is True
        assert result.entry_counts == {"git": 1}
        assert result.leg_timings_ms == {"read": 12, "verify": 3}

    def test_defaults_for_the_typed_fields(self) -> None:
        result = ModelContextSourceResult(status=EnumContextSourceStatus.UNRESOLVED)
        assert result.has_more is False
        assert result.entry_counts == {}
        assert result.leg_timings_ms == {}
        assert result.error_code is None

    def test_resolved_with_no_entries_fails(self) -> None:
        with pytest.raises(ValidationError, match="at least one entry"):
            ModelContextSourceResult(status=EnumContextSourceStatus.RESOLVED)

    @pytest.mark.parametrize(
        "status",
        [
            EnumContextSourceStatus.UNRESOLVED,
            EnumContextSourceStatus.DENIED,
            EnumContextSourceStatus.UNAVAILABLE,
        ],
    )
    def test_no_entry_statuses_refuse_entries(
        self, status: EnumContextSourceStatus
    ) -> None:
        with pytest.raises(ValidationError, match="must not carry entries"):
            ModelContextSourceResult(status=status, entries=(_entry(),))

    @pytest.mark.parametrize(
        "status", [EnumContextSourceStatus.STALE, EnumContextSourceStatus.AMBIGUOUS]
    )
    def test_stale_and_ambiguous_may_carry_entries(
        self, status: EnumContextSourceStatus
    ) -> None:
        assert ModelContextSourceResult(status=status, entries=(_entry(),)).entries

    def test_error_code_only_on_unavailable(self) -> None:
        with pytest.raises(ValidationError, match="UNAVAILABLE"):
            ModelContextSourceResult(
                status=EnumContextSourceStatus.UNRESOLVED,
                error_code=EnumContextSourceErrorCode.INVALID_RESPONSE,
            )

    def test_error_message_requires_error_code(self) -> None:
        with pytest.raises(ValidationError, match="error_code"):
            ModelContextSourceResult(
                status=EnumContextSourceStatus.UNAVAILABLE, error_message="boom"
            )

    def test_raw_valid_response_round_trips(self) -> None:
        good = ModelContextSourceResult(
            status=EnumContextSourceStatus.RESOLVED, entries=(_entry(),)
        )
        assert ModelContextSourceResult.from_raw_response(good.model_dump()) == good

    def test_invalid_response_yields_typed_error_not_empty_resolved(self) -> None:
        bad_entry = _entry().model_dump() | {"text_sha256": _sha("tampered")}
        result = ModelContextSourceResult.from_raw_response(
            {"status": "resolved", "entries": [bad_entry]}
        )
        assert result.status is EnumContextSourceStatus.UNAVAILABLE
        assert result.error_code is EnumContextSourceErrorCode.INVALID_RESPONSE
        assert result.error_message
        assert result.entries == ()

    def test_response_missing_status_yields_typed_error(self) -> None:
        result = ModelContextSourceResult.from_raw_response({"entries": []})
        assert result.status is EnumContextSourceStatus.UNAVAILABLE
        assert result.error_code is EnumContextSourceErrorCode.INVALID_RESPONSE

    def test_request_error_result(self) -> None:
        result = ModelContextSourceResult.error(
            EnumContextSourceErrorCode.INVALID_REQUEST, "no access"
        )
        assert result.status is EnumContextSourceStatus.UNAVAILABLE
        assert result.error_code is EnumContextSourceErrorCode.INVALID_REQUEST
