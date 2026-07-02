# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Selection-semantics tests for ``MixinNodeDispatch`` (OMN-12549, epic OMN-12525).

These pin the core-side seam's selection tuple

    (status, ordered dispatcher_ids, message_category, message_type, dlq_topic)

against the behavior it ports from the live
``omnibase_infra.runtime.message_dispatch_engine`` ``_find_matching_dispatchers`` +
``dispatch()`` selection path. The cross-repo dual-implementation parity gate
(OMN-12548 Mode B, in omnibase_infra) asserts tuple equality against the engine
itself; these tests are the in-repo proof that the ported semantics are correct
and stay stable, using only core symbols.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.models.dispatch.model_dispatch_route import ModelDispatchRoute
from omnibase_core.models.errors import ModelOnexError
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.nodes.node_effect import NodeEffect
from omnibase_core.nodes.node_orchestrator import NodeOrchestrator
from omnibase_core.runtime.mixin_node_dispatch import MixinNodeDispatch

pytestmark = pytest.mark.unit

_EVENTS_TOPIC = "onex.evt.platform.thing-happened.v1"  # onex-topic-allow: test fixture


def _noop_dispatcher(_envelope: object) -> None:
    """Inert dispatcher — selection never invokes it."""
    return


class _AlphaPayload(BaseModel):
    value: int = 0


class _BetaPayload(BaseModel):
    value: int = 0


def _selection_tuple(result: object) -> tuple[object, ...]:
    """Extract the design-D2 equivalence tuple from a ModelDispatchResult."""
    raw = getattr(result, "dispatcher_id", None) or ""
    ordered = [d for d in (p.strip() for p in raw.split(",")) if d]
    category = getattr(result, "message_category", None)
    return (
        result.status.value,
        tuple(ordered),
        category.value if category is not None else None,
        getattr(result, "message_type", None),
        getattr(result, "dlq_topic", None),
    )


def _envelope(*, event_type: str | None, payload: object) -> ModelEventEnvelope[object]:
    kwargs: dict[str, object] = {"payload": payload}
    if event_type is not None:
        kwargs["event_type"] = event_type
    return ModelEventEnvelope(**kwargs)


def _register_single(
    mixin: MixinNodeDispatch,
    *,
    dispatcher_id: str = "d1",
    message_types: set[str] | None = None,
    payload_type_matcher: object = None,
    topic_pattern: str = "onex.evt.platform.*.v1",
    route_message_type: str | None = None,
) -> None:
    mixin.register_dispatcher(
        dispatcher_id=dispatcher_id,
        dispatcher=_noop_dispatcher,
        category=EnumMessageCategory.EVENT,
        message_types=message_types,
        # NOTE(OMN-12549): tests pass matcher callables with narrower payload
        # assumptions to pin runtime behavior around rejected payloads.
        payload_type_matcher=payload_type_matcher,  # type: ignore[arg-type]
    )
    mixin.register_route(
        ModelDispatchRoute(
            route_id=f"r-{dispatcher_id}",
            topic_pattern=topic_pattern,
            message_category=EnumMessageCategory.EVENT,
            message_type=route_message_type,
            handler_id=dispatcher_id,
        )
    )


# ---------------------------------------------------------------------------
# Success path + fan-out ordering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_success_single_dispatcher_selection_tuple() -> None:
    mixin = MixinNodeDispatch()
    _register_single(mixin)
    mixin.freeze()

    result = await mixin.dispatch(
        _EVENTS_TOPIC, _envelope(event_type=None, payload=_AlphaPayload())
    )
    assert _selection_tuple(result) == (
        "success",
        ("d1",),
        "event",
        "_AlphaPayload",
        None,
    )


@pytest.mark.asyncio
async def test_fanout_preserves_registration_order() -> None:
    """Multiple dispatchers on one topic fan out in route registration order."""
    mixin = MixinNodeDispatch()
    for did in ("d_a", "d_b", "d_c"):
        _register_single(mixin, dispatcher_id=did)
    mixin.freeze()

    result = await mixin.dispatch(
        _EVENTS_TOPIC, _envelope(event_type=None, payload=_AlphaPayload())
    )
    status, ordered, *_ = _selection_tuple(result)
    assert status == "success"
    assert ordered == ("d_a", "d_b", "d_c")


@pytest.mark.asyncio
async def test_event_type_overrides_payload_class_for_message_type() -> None:
    mixin = MixinNodeDispatch()
    _register_single(mixin, message_types={"platform.thing.v1"})
    mixin.freeze()

    result = await mixin.dispatch(
        _EVENTS_TOPIC,
        _envelope(event_type="platform.thing.v1", payload=_AlphaPayload()),
    )
    status, ordered, _cat, message_type, _dlq = _selection_tuple(result)
    assert status == "success"
    assert ordered == ("d1",)
    assert message_type == "platform.thing.v1"


# ---------------------------------------------------------------------------
# NO_DISPATCHER + DLQ deriver injection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_dispatcher_without_deriver_has_none_dlq() -> None:
    mixin = MixinNodeDispatch()
    _register_single(mixin, topic_pattern="onex.evt.other.*.v1")
    mixin.freeze()

    result = await mixin.dispatch(
        _EVENTS_TOPIC, _envelope(event_type=None, payload=_AlphaPayload())
    )
    status, ordered, category, _mt, dlq = _selection_tuple(result)
    assert status == "no_dispatcher"
    assert ordered == ()
    assert category == "event"
    assert dlq is None


@pytest.mark.asyncio
async def test_no_dispatcher_uses_injected_deriver() -> None:
    """The injected deriver supplies the ``dlq_topic`` element of the tuple."""
    mixin = MixinNodeDispatch()
    _register_single(mixin, topic_pattern="onex.evt.other.*.v1")

    seen: list[tuple[str | None, str]] = []

    def _deriver(event_type: str | None, topic: str) -> str | None:
        seen.append((event_type, topic))
        return "onex.dlq.omnibase-infra.platform.v1"  # onex-topic-allow: test fixture

    mixin.set_dlq_topic_deriver(_deriver)
    mixin.freeze()

    result = await mixin.dispatch(
        _EVENTS_TOPIC,
        _envelope(event_type="platform.x.v1", payload=_AlphaPayload()),
    )
    assert _selection_tuple(result)[4] == "onex.dlq.omnibase-infra.platform.v1"
    # event_type is forwarded normalized (non-empty), topic verbatim.
    assert seen == [("platform.x.v1", _EVENTS_TOPIC)]


@pytest.mark.asyncio
async def test_deriver_raise_is_swallowed_to_none() -> None:
    mixin = MixinNodeDispatch()
    _register_single(mixin, topic_pattern="onex.evt.other.*.v1")

    def _bad(_event_type: str | None, _topic: str) -> str | None:
        raise RuntimeError("boom")

    mixin.set_dlq_topic_deriver(_bad)
    mixin.freeze()

    result = await mixin.dispatch(
        _EVENTS_TOPIC, _envelope(event_type=None, payload=_AlphaPayload())
    )
    assert _selection_tuple(result)[0] == "no_dispatcher"
    assert _selection_tuple(result)[4] is None


# ---------------------------------------------------------------------------
# INVALID_MESSAGE
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_uncategorizable_topic_is_invalid_message() -> None:
    mixin = MixinNodeDispatch()
    _register_single(mixin)
    mixin.freeze()

    # No category segment (events/commands/intents/evt/cmd/intent) -> None category.
    result = await mixin.dispatch(
        "weird.random.topic", _envelope(event_type=None, payload=_AlphaPayload())
    )
    assert _selection_tuple(result) == (
        "invalid_message",
        (),
        None,
        None,
        None,
    )


# ---------------------------------------------------------------------------
# Payload type-scoping (OMN-12416)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_type_scoped_matcher_accepts_matching_payload() -> None:
    mixin = MixinNodeDispatch()
    _register_single(mixin, payload_type_matcher=lambda p: isinstance(p, _AlphaPayload))
    mixin.freeze()

    result = await mixin.dispatch(
        _EVENTS_TOPIC, _envelope(event_type=None, payload=_AlphaPayload())
    )
    assert _selection_tuple(result)[0] == "success"


@pytest.mark.asyncio
async def test_type_scoped_matcher_rejects_nonmatching_payload() -> None:
    """A type-scoped dispatcher whose matcher rejects the payload is dropped ->
    NO_DISPATCHER, not an error (OMN-12416)."""
    mixin = MixinNodeDispatch()
    _register_single(mixin, payload_type_matcher=lambda p: isinstance(p, _AlphaPayload))
    mixin.freeze()

    result = await mixin.dispatch(
        _EVENTS_TOPIC, _envelope(event_type=None, payload=_BetaPayload())
    )
    assert _selection_tuple(result)[0] == "no_dispatcher"


@pytest.mark.asyncio
async def test_type_scoped_matcher_rejects_none_payload() -> None:
    mixin = MixinNodeDispatch()
    _register_single(mixin, payload_type_matcher=lambda p: isinstance(p, _AlphaPayload))
    mixin.freeze()

    result = await mixin.dispatch(
        _EVENTS_TOPIC, _envelope(event_type=None, payload=None)
    )
    assert _selection_tuple(result)[0] == "no_dispatcher"


@pytest.mark.asyncio
async def test_type_scoped_matcher_can_accept_none_payload() -> None:
    mixin = MixinNodeDispatch()
    _register_single(mixin, payload_type_matcher=lambda p: p is None)
    mixin.freeze()

    result = await mixin.dispatch(
        _EVENTS_TOPIC, _envelope(event_type=None, payload=None)
    )
    assert _selection_tuple(result)[0] == "success"


@pytest.mark.asyncio
async def test_raising_matcher_is_treated_as_non_match() -> None:
    def _raises(_payload: object) -> bool:
        raise ValueError("not my type")

    mixin = MixinNodeDispatch()
    _register_single(mixin, payload_type_matcher=_raises)
    mixin.freeze()

    result = await mixin.dispatch(
        _EVENTS_TOPIC, _envelope(event_type=None, payload=_AlphaPayload())
    )
    assert _selection_tuple(result)[0] == "no_dispatcher"


# ---------------------------------------------------------------------------
# Message-type filters
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatcher_message_types_filter_excludes_mismatch() -> None:
    mixin = MixinNodeDispatch()
    _register_single(mixin, message_types={"SomethingElse"})
    mixin.freeze()

    result = await mixin.dispatch(
        _EVENTS_TOPIC, _envelope(event_type=None, payload=_AlphaPayload())
    )
    assert _selection_tuple(result)[0] == "no_dispatcher"


@pytest.mark.asyncio
async def test_route_message_type_filter_excludes_mismatch() -> None:
    mixin = MixinNodeDispatch()
    _register_single(mixin, route_message_type="OnlyThisType")
    mixin.freeze()

    result = await mixin.dispatch(
        _EVENTS_TOPIC, _envelope(event_type=None, payload=_AlphaPayload())
    )
    assert _selection_tuple(result)[0] == "no_dispatcher"


@pytest.mark.asyncio
async def test_dispatcher_message_types_are_snapshotted_on_registration() -> None:
    message_types = {"_AlphaPayload"}
    mixin = MixinNodeDispatch()
    _register_single(mixin, message_types=message_types)
    message_types.clear()
    mixin.freeze()

    result = await mixin.dispatch(
        _EVENTS_TOPIC, _envelope(event_type=None, payload=_AlphaPayload())
    )
    assert _selection_tuple(result)[0] == "success"


@pytest.mark.asyncio
async def test_route_id_comes_from_selected_dispatcher_route() -> None:
    mixin = MixinNodeDispatch()
    _register_single(
        mixin,
        dispatcher_id="d_reject",
        payload_type_matcher=lambda p: isinstance(p, _BetaPayload),
    )
    _register_single(
        mixin,
        dispatcher_id="d_accept",
        payload_type_matcher=lambda p: isinstance(p, _AlphaPayload),
    )
    mixin.freeze()

    result = await mixin.dispatch(
        _EVENTS_TOPIC, _envelope(event_type=None, payload=_AlphaPayload())
    )
    assert result.route_id == "r-d_accept"
    assert _selection_tuple(result)[1] == ("d_accept",)


# ---------------------------------------------------------------------------
# Lifecycle / guard rails
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_before_freeze_raises_invalid_state() -> None:
    mixin = MixinNodeDispatch()
    _register_single(mixin)
    with pytest.raises(ModelOnexError) as exc:
        await mixin.dispatch(
            _EVENTS_TOPIC, _envelope(event_type=None, payload=_AlphaPayload())
        )
    assert exc.value.error_code == EnumCoreErrorCode.INVALID_STATE


def test_register_after_freeze_raises() -> None:
    mixin = MixinNodeDispatch()
    _register_single(mixin)
    mixin.freeze()
    with pytest.raises(ModelOnexError) as exc:
        mixin.register_dispatcher(
            dispatcher_id="d2",
            dispatcher=_noop_dispatcher,
            category=EnumMessageCategory.EVENT,
        )
    assert exc.value.error_code == EnumCoreErrorCode.INVALID_STATE


def test_duplicate_dispatcher_id_rejected() -> None:
    mixin = MixinNodeDispatch()
    mixin.register_dispatcher(
        dispatcher_id="d1",
        dispatcher=_noop_dispatcher,
        category=EnumMessageCategory.EVENT,
    )
    with pytest.raises(ModelOnexError) as exc:
        mixin.register_dispatcher(
            dispatcher_id="d1",
            dispatcher=_noop_dispatcher,
            category=EnumMessageCategory.EVENT,
        )
    assert exc.value.error_code == EnumCoreErrorCode.DUPLICATE_REGISTRATION


def test_duplicate_route_id_rejected() -> None:
    mixin = MixinNodeDispatch()
    route = ModelDispatchRoute(
        route_id="r1",
        topic_pattern="onex.evt.platform.*.v1",
        message_category=EnumMessageCategory.EVENT,
        handler_id="d1",
    )
    mixin.register_route(route)
    with pytest.raises(ModelOnexError) as exc:
        mixin.register_route(route)
    assert exc.value.error_code == EnumCoreErrorCode.DUPLICATE_REGISTRATION


def test_freeze_validates_route_references_dispatcher() -> None:
    mixin = MixinNodeDispatch()
    mixin.register_route(
        ModelDispatchRoute(
            route_id="r1",
            topic_pattern="onex.evt.platform.*.v1",
            message_category=EnumMessageCategory.EVENT,
            handler_id="missing_dispatcher",
        )
    )
    with pytest.raises(ModelOnexError) as exc:
        mixin.freeze()
    assert exc.value.error_code == EnumCoreErrorCode.ITEM_NOT_REGISTERED


def test_register_route_rejects_existing_dispatcher_category_mismatch() -> None:
    mixin = MixinNodeDispatch()
    mixin.register_dispatcher(
        dispatcher_id="d1",
        dispatcher=_noop_dispatcher,
        category=EnumMessageCategory.COMMAND,
    )
    with pytest.raises(ModelOnexError) as exc:
        mixin.register_route(
            ModelDispatchRoute(
                route_id="r1",
                topic_pattern="onex.evt.platform.*.v1",
                message_category=EnumMessageCategory.EVENT,
                handler_id="d1",
            )
        )
    assert exc.value.error_code == EnumCoreErrorCode.INVALID_PARAMETER


def test_register_dispatcher_rejects_existing_route_category_mismatch() -> None:
    mixin = MixinNodeDispatch()
    mixin.register_route(
        ModelDispatchRoute(
            route_id="r1",
            topic_pattern="onex.evt.platform.*.v1",
            message_category=EnumMessageCategory.EVENT,
            handler_id="d1",
        )
    )
    with pytest.raises(ModelOnexError) as exc:
        mixin.register_dispatcher(
            dispatcher_id="d1",
            dispatcher=_noop_dispatcher,
            category=EnumMessageCategory.COMMAND,
        )
    assert exc.value.error_code == EnumCoreErrorCode.INVALID_PARAMETER


def test_freeze_rejects_route_dispatcher_category_mismatch() -> None:
    mixin = MixinNodeDispatch()
    mixin.register_route(
        ModelDispatchRoute(
            route_id="r1",
            topic_pattern="onex.evt.platform.*.v1",
            message_category=EnumMessageCategory.EVENT,
            handler_id="d1",
        )
    )
    state = mixin._state()
    state.dispatchers["d1"] = SimpleNamespace(
        category=EnumMessageCategory.COMMAND,
        dispatcher_id="d1",
    )  # type: ignore[assignment]
    with pytest.raises(ModelOnexError) as exc:
        mixin.freeze()
    assert exc.value.error_code == EnumCoreErrorCode.INVALID_PARAMETER


def test_empty_dispatcher_id_rejected() -> None:
    mixin = MixinNodeDispatch()
    with pytest.raises(ModelOnexError) as exc:
        mixin.register_dispatcher(
            dispatcher_id="  ",
            dispatcher=_noop_dispatcher,
            category=EnumMessageCategory.EVENT,
        )
    assert exc.value.error_code == EnumCoreErrorCode.INVALID_PARAMETER


# ---------------------------------------------------------------------------
# Node MRO placement (additive; engine stays live)
# ---------------------------------------------------------------------------


def test_mixin_is_in_orchestrator_and_effect_mro() -> None:
    assert MixinNodeDispatch in NodeOrchestrator.__mro__
    assert MixinNodeDispatch in NodeEffect.__mro__


@pytest.mark.asyncio
async def test_disabled_route_is_skipped() -> None:
    mixin = MixinNodeDispatch()
    mixin.register_dispatcher(
        dispatcher_id="d1",
        dispatcher=_noop_dispatcher,
        category=EnumMessageCategory.EVENT,
    )
    mixin.register_route(
        ModelDispatchRoute(
            route_id="r1",
            topic_pattern="onex.evt.platform.*.v1",
            message_category=EnumMessageCategory.EVENT,
            handler_id="d1",
            enabled=False,
        )
    )
    mixin.freeze()
    result = await mixin.dispatch(
        _EVENTS_TOPIC, _envelope(event_type=None, payload=_AlphaPayload())
    )
    assert _selection_tuple(result)[0] == "no_dispatcher"
