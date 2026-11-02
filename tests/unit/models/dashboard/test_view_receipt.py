# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for view delivery and render receipt contracts (OMN-21999).

Exercise schema compatibility, immutable records, typed causes, identifiers and
timezone-aware timestamps across the delivery and render lifecycle.
"""

from datetime import UTC, datetime, timedelta, timezone
from types import SimpleNamespace

import jsonschema
import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.enums.enum_empty_state_reason import EnumEmptyStateReason
from omnibase_core.enums.enum_view_decode_outcome import EnumViewDecodeOutcome
from omnibase_core.enums.enum_view_render_disposition import EnumViewRenderDisposition
from omnibase_core.models.dashboard.model_view_delivery_receipt import (
    ModelViewDeliveryReceipt,
)
from omnibase_core.models.dashboard.model_view_render_completed_record import (
    ModelViewRenderCompletedRecord,
)
from omnibase_core.models.dashboard.model_view_render_receipt import (
    ModelViewRenderReceipt,
)
from omnibase_core.models.dashboard.model_view_render_started_record import (
    ModelViewRenderStartedRecord,
)

__all__: list[str] = []

TICK = datetime(2026, 11, 2, 12, tzinfo=UTC)
DIGEST = "sha256:" + "a" * 64


def delivery() -> ModelViewDeliveryReceipt:
    """Build a successfully decoded delivery receipt."""
    return ModelViewDeliveryReceipt(
        request_id="request:1",
        view_id="dashboard.main",
        origin_tick=TICK,
        source_document_digest=DIGEST,
        received_at=TICK + timedelta(seconds=1),
        decode_outcome=EnumViewDecodeOutcome.DECODED,
    )


def started() -> ModelViewRenderStartedRecord:
    """Build the first record sent by the renderer."""
    return ModelViewRenderStartedRecord(
        started_at=TICK + timedelta(seconds=2),
        view_id="dashboard.main",
        source_document_digest=DIGEST,
    )


def completed() -> ModelViewRenderCompletedRecord:
    """Build a completed render that drew sections and rows."""
    return ModelViewRenderCompletedRecord(
        completed_at=TICK + timedelta(seconds=3),
        disposition=EnumViewRenderDisposition.DRAWN,
        section_ids_drawn=("section:1", "section_2"),
        row_ids_drawn=("row:1", "row-2"),
    )


def receipt() -> ModelViewRenderReceipt:
    """Build a receipt containing both render records."""
    return ModelViewRenderReceipt(
        render_id="render:1", started=started(), completed=completed()
    )


def instances() -> tuple[BaseModel, ...]:
    """Provide each model and both stages of the render receipt."""
    return (
        delivery(),
        started(),
        completed(),
        receipt(),
        ModelViewRenderReceipt(render_id="render:pending", started=started()),
    )


@pytest.mark.unit
class TestViewReceipt:
    @pytest.mark.parametrize("instance", instances())
    def test_view_receipt_valid_schema_and_json_roundtrip(
        self, instance: BaseModel
    ) -> None:
        payload = instance.model_dump(mode="json")
        jsonschema.validate(payload, type(instance).model_json_schema())
        assert type(instance).model_validate(payload) == instance

    @pytest.mark.parametrize("instance", instances())
    def test_view_receipt_extra_field_refused(self, instance: BaseModel) -> None:
        with pytest.raises(ValidationError, match="extra_forbidden"):
            type(instance).model_validate({**instance.model_dump(), "extra": 1})

    @pytest.mark.parametrize("instance", instances())
    def test_view_receipt_from_attributes(self, instance: BaseModel) -> None:
        attributes = SimpleNamespace(**instance.model_dump())
        assert type(instance).model_validate(attributes) == instance

    def test_view_receipt_models_are_frozen(self) -> None:
        delivered = delivery()
        begin = started()
        end = completed()
        rendered = receipt()
        with pytest.raises(ValidationError, match="frozen_instance"):
            delivered.__setattr__("request_id", "other")
        with pytest.raises(ValidationError, match="frozen_instance"):
            begin.__setattr__("view_id", "other")
        with pytest.raises(ValidationError, match="frozen_instance"):
            end.__setattr__("cause", EnumEmptyStateReason.NO_DATA)
        with pytest.raises(ValidationError, match="frozen_instance"):
            rendered.__setattr__("render_id", "other")

    @pytest.mark.parametrize(
        ("instance", "field"),
        [
            (delivery(), "origin_tick"),
            (delivery(), "received_at"),
            (started(), "started_at"),
            (completed(), "completed_at"),
        ],
    )
    @pytest.mark.parametrize("as_string", [False, True])
    def test_view_receipt_naive_datetime_refused(
        self, instance: BaseModel, field: str, as_string: bool
    ) -> None:
        naive = TICK.replace(tzinfo=None)
        payload = instance.model_dump()
        payload[field] = naive.isoformat() if as_string else naive
        with pytest.raises(ValidationError, match="timezone_aware"):
            type(instance).model_validate(payload)

    @pytest.mark.parametrize("record", ["started", "completed"])
    def test_view_receipt_nested_naive_datetime_refused(self, record: str) -> None:
        field = "started_at" if record == "started" else "completed_at"
        nested = started() if record == "started" else completed()
        payload = receipt().model_dump()
        payload[record] = {**nested.model_dump(), field: TICK.replace(tzinfo=None)}
        with pytest.raises(ValidationError, match="timezone_aware"):
            ModelViewRenderReceipt.model_validate(payload)

    @pytest.mark.parametrize(
        ("instance", "field"),
        [
            (delivery(), "request_id"),
            (delivery(), "view_id"),
            (started(), "view_id"),
            (receipt(), "render_id"),
            (completed(), "section_ids_drawn"),
            (completed(), "row_ids_drawn"),
        ],
    )
    @pytest.mark.parametrize("bad", ["", " ", "has space", "a" * 129, "_leading"])
    def test_view_receipt_malformed_id_refused(
        self, instance: BaseModel, field: str, bad: str
    ) -> None:
        value: str | tuple[str, ...] = (bad,) if field.endswith("_drawn") else bad
        with pytest.raises(ValidationError, match="string_pattern_mismatch"):
            type(instance).model_validate({**instance.model_dump(), field: value})

    @pytest.mark.parametrize("instance", [delivery(), started()])
    @pytest.mark.parametrize(
        "bad",
        [
            "",
            " ",
            "has space",
            "a" * 129,
            "sha256:ABC",
            "md5:" + "a" * 64,
            "sha256:" + "A" * 64,
            "sha256:" + "g" * 64,
            "sha256:" + "a" * 63,
            "sha256:" + "a" * 65,
        ],
    )
    def test_view_receipt_malformed_digest_refused(
        self, instance: BaseModel, bad: str
    ) -> None:
        payload = {**instance.model_dump(), "source_document_digest": bad}
        with pytest.raises(ValidationError, match="string_pattern_mismatch"):
            type(instance).model_validate(payload)

    def test_view_receipt_id_length_boundary_and_punctuation(self) -> None:
        identifier = "A_.:-" + "z" * 123
        delivered = ModelViewDeliveryReceipt.model_validate(
            {**delivery().model_dump(), "request_id": identifier, "view_id": identifier}
        )
        assert delivered.request_id == identifier
        assert delivered.view_id == identifier
        begin = ModelViewRenderStartedRecord.model_validate(
            {**started().model_dump(), "view_id": identifier}
        )
        assert begin.view_id == identifier
        end = ModelViewRenderCompletedRecord.model_validate(
            {
                **completed().model_dump(),
                "section_ids_drawn": (identifier,),
                "row_ids_drawn": (identifier,),
            }
        )
        assert end.section_ids_drawn == end.row_ids_drawn == (identifier,)
        rendered = ModelViewRenderReceipt(render_id=identifier, started=begin)
        assert rendered.render_id == identifier

    @pytest.mark.parametrize("outcome", list(EnumViewDecodeOutcome))
    @pytest.mark.parametrize("cause", [None, *EnumEmptyStateReason])
    def test_view_receipt_delivery_cause_rules(
        self, outcome: EnumViewDecodeOutcome, cause: EnumEmptyStateReason | None
    ) -> None:
        payload = {
            **delivery().model_dump(),
            "decode_outcome": outcome,
            "decode_cause": cause,
        }
        if (outcome == EnumViewDecodeOutcome.DECODED) == (cause is None):
            instance = ModelViewDeliveryReceipt.model_validate(payload)
            assert instance.decode_outcome == outcome
            assert instance.decode_cause == cause
        else:
            with pytest.raises(ValidationError, match="decode_cause"):
                ModelViewDeliveryReceipt.model_validate(payload)

    @pytest.mark.parametrize("disposition", list(EnumViewRenderDisposition))
    @pytest.mark.parametrize("cause", [None, *EnumEmptyStateReason])
    def test_view_receipt_completed_cause_rules(
        self,
        disposition: EnumViewRenderDisposition,
        cause: EnumEmptyStateReason | None,
    ) -> None:
        payload = {
            "completed_at": TICK,
            "disposition": disposition,
            "cause": cause,
        }
        if (disposition == EnumViewRenderDisposition.DRAWN) == (cause is None):
            instance = ModelViewRenderCompletedRecord.model_validate(payload)
            assert instance.disposition == disposition
            assert instance.cause == cause
            assert instance.section_ids_drawn == instance.row_ids_drawn == ()
        else:
            with pytest.raises(ValidationError, match="cause"):
                ModelViewRenderCompletedRecord.model_validate(payload)

    @pytest.mark.parametrize("outcome", list(EnumViewDecodeOutcome))
    def test_view_receipt_delivery_omitted_cause(
        self, outcome: EnumViewDecodeOutcome
    ) -> None:
        payload = delivery().model_dump(exclude={"decode_cause"})
        payload["decode_outcome"] = outcome
        if outcome == EnumViewDecodeOutcome.DECODED:
            assert ModelViewDeliveryReceipt.model_validate(payload).decode_cause is None
        else:
            with pytest.raises(ValidationError, match="decode_cause"):
                ModelViewDeliveryReceipt.model_validate(payload)

    @pytest.mark.parametrize("disposition", list(EnumViewRenderDisposition))
    def test_view_receipt_completed_omitted_cause(
        self, disposition: EnumViewRenderDisposition
    ) -> None:
        payload = {"completed_at": TICK, "disposition": disposition}
        if disposition == EnumViewRenderDisposition.DRAWN:
            assert ModelViewRenderCompletedRecord.model_validate(payload).cause is None
        else:
            with pytest.raises(ValidationError, match="cause"):
                ModelViewRenderCompletedRecord.model_validate(payload)

    @pytest.mark.parametrize(
        ("sections", "rows"),
        [(("section:1",), ()), ((), ("row:1",)), (("section:1",), ("row:1",))],
    )
    def test_view_receipt_refused_cannot_claim_drawn_ids(
        self, sections: tuple[str, ...], rows: tuple[str, ...]
    ) -> None:
        with pytest.raises(ValidationError, match="refused requires empty"):
            ModelViewRenderCompletedRecord(
                completed_at=TICK,
                disposition=EnumViewRenderDisposition.REFUSED,
                cause=EnumEmptyStateReason.SCHEMA_INVALID,
                section_ids_drawn=sections,
                row_ids_drawn=rows,
            )

    @pytest.mark.parametrize("field", ["section_ids_drawn", "row_ids_drawn"])
    @pytest.mark.parametrize(
        "disposition",
        [EnumViewRenderDisposition.DRAWN, EnumViewRenderDisposition.DRAWN_WITH_CAUSE],
    )
    def test_view_receipt_duplicate_drawn_ids_refused(
        self, field: str, disposition: EnumViewRenderDisposition
    ) -> None:
        cause = (
            None
            if disposition == EnumViewRenderDisposition.DRAWN
            else EnumEmptyStateReason.NO_DATA
        )
        payload = {
            **completed().model_dump(),
            "disposition": disposition,
            "cause": cause,
            field: ("duplicate", "duplicate"),
        }
        with pytest.raises(
            ValidationError, match=f"{field} must not contain duplicates"
        ):
            ModelViewRenderCompletedRecord.model_validate(payload)

    @pytest.mark.parametrize("seconds", [-1, 0, 1])
    def test_view_receipt_completion_order(self, seconds: int) -> None:
        begin = started()
        end = ModelViewRenderCompletedRecord(
            completed_at=begin.started_at + timedelta(seconds=seconds),
            disposition=EnumViewRenderDisposition.DRAWN,
        )
        if seconds < 0:
            with pytest.raises(
                ValidationError, match="completed_at must not be before"
            ):
                ModelViewRenderReceipt(
                    render_id="render:1", started=begin, completed=end
                )
        else:
            assert (
                ModelViewRenderReceipt(
                    render_id="render:1", started=begin, completed=end
                ).completed
                == end
            )

    def test_view_receipt_completion_compares_instants_across_offsets(self) -> None:
        begin = started()
        end = ModelViewRenderCompletedRecord(
            completed_at=begin.started_at.astimezone(timezone(timedelta(hours=-5))),
            disposition=EnumViewRenderDisposition.DRAWN,
        )
        assert (
            ModelViewRenderReceipt(
                render_id="render:1", started=begin, completed=end
            ).completed
            == end
        )

    @pytest.mark.parametrize(
        ("instance", "field"),
        [(delivery(), "decode_outcome"), (completed(), "disposition")],
    )
    def test_view_receipt_enums_are_closed(
        self, instance: BaseModel, field: str
    ) -> None:
        with pytest.raises(ValidationError, match="enum"):
            type(instance).model_validate({**instance.model_dump(), field: "maybe"})
