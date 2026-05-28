# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the @shim decorator (OMN-4418)."""

from __future__ import annotations

import datetime

import pytest

from omnibase_core.decorators.decorator_shim import (
    SHIM_ATTR,
    ModelShimMetadata,
    get_shim_metadata,
    has_shim,
    shim,
)


@pytest.mark.unit
class TestShimDecorator:
    """Test suite for the @shim decorator."""

    _EXPIRES = datetime.date(2026, 6, 1)

    def _make_shim(self) -> ModelShimMetadata:
        return ModelShimMetadata(
            ticket_id="OMN-9999",
            expires_on=self._EXPIRES,
            reason="legacy compat",
            replacement="omnibase_compat.dtos.NewModel",
        )

    def test_decorator_preserves_function_behavior(self) -> None:
        @shim(
            ticket_id="OMN-9999",
            expires_on=self._EXPIRES,
            reason="legacy compat",
            replacement="omnibase_compat.dtos.NewModel",
        )
        def add(a: int, b: int) -> int:
            return a + b

        assert add(2, 3) == 5

    def test_decorator_preserves_docstring(self) -> None:
        @shim(
            ticket_id="OMN-9999",
            expires_on=self._EXPIRES,
            reason="r",
            replacement="x",
        )
        def documented() -> None:
            """Original docstring."""

        assert documented.__doc__ == "Original docstring."

    def test_shim_attr_attached(self) -> None:
        @shim(
            ticket_id="OMN-9999",
            expires_on=self._EXPIRES,
            reason="r",
            replacement="x",
        )
        def fn() -> None: ...

        meta = getattr(fn, SHIM_ATTR)
        assert isinstance(meta, ModelShimMetadata)
        assert meta.ticket_id == "OMN-9999"
        assert meta.expires_on == self._EXPIRES

    def test_has_shim_true(self) -> None:
        @shim(
            ticket_id="OMN-1",
            expires_on=self._EXPIRES,
            reason="r",
            replacement="x",
        )
        def fn() -> None: ...

        assert has_shim(fn) is True

    def test_has_shim_false_for_plain_function(self) -> None:
        def plain() -> None: ...

        assert has_shim(plain) is False

    def test_get_shim_metadata_returns_model(self) -> None:
        @shim(
            ticket_id="OMN-42",
            expires_on=self._EXPIRES,
            reason="reason text",
            replacement="NewClass",
        )
        def fn() -> None: ...

        meta = get_shim_metadata(fn)
        assert meta is not None
        assert meta.ticket_id == "OMN-42"
        assert meta.reason == "reason text"
        assert meta.replacement == "NewClass"

    def test_get_shim_metadata_returns_none_for_plain(self) -> None:
        def plain() -> None: ...

        assert get_shim_metadata(plain) is None

    def test_model_is_frozen(self) -> None:
        meta = self._make_shim()
        with pytest.raises(Exception):
            meta.ticket_id = "changed"  # type: ignore[misc]

    def test_metadata_fields_strongly_typed(self) -> None:
        meta = self._make_shim()
        assert isinstance(meta.expires_on, datetime.date)
        assert isinstance(meta.ticket_id, str)

    def test_decorator_stacks_with_other_decorators(self) -> None:
        call_log: list[str] = []

        def audit(f):  # type: ignore[no-untyped-def]
            def wrapper(*a, **kw):  # type: ignore[no-untyped-def]
                call_log.append("audit")
                return f(*a, **kw)

            return wrapper

        @audit
        @shim(
            ticket_id="OMN-9999",
            expires_on=self._EXPIRES,
            reason="r",
            replacement="x",
        )
        def fn() -> str:
            call_log.append("fn")
            return "ok"

        assert fn() == "ok"
        assert call_log == ["audit", "fn"]
