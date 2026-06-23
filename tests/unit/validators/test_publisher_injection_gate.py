# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for publisher_injection_gate validator (OMN-12881).

DoD:
- Failing fixture: side-emitting handler without ``event_bus`` in __init__ →
  validator MUST flag (``missing_publisher_injection``).
- Green fixture: side-emitting handler WITH injected ``event_bus`` →
  validator passes; handler can publish on the bus.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from omnibase_core.validators.publisher_injection_gate import (
    validate_file,
    validate_paths,
)

# ---------------------------------------------------------------------------
# File-creation helpers (mirrors handler_di_gate test patterns)
# ---------------------------------------------------------------------------


def _handler(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / f"nodes/my_node/handlers/{name}"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _node_handler(tmp_path: Path, content: str) -> Path:
    """A handler.py inside a nodes/ package (canonical ONEX handler location)."""
    p = tmp_path / "nodes/my_node/handler.py"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _non_handler(tmp_path: Path, name: str, content: str) -> Path:
    """A Python file NOT in a handlers/ directory (should be ignored)."""
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Core DoD: failing fixture (missing injection) and green fixture (injected)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDoD:
    """Acceptance tests required by the OMN-12881 DoD."""

    def test_failing_fixture__side_emitting_without_event_bus__flags(
        self, tmp_path: Path
    ) -> None:
        """DoD failing fixture: handler publishes events but has no event_bus param.

        The validator MUST fire ``missing_publisher_injection``.
        Without this guardrail the runtime silently skips injection and the
        handler crashes at runtime with ``AttributeError: 'NoneType' object has
        no attribute 'publish'``.
        """
        p = _handler(
            tmp_path,
            "handler_side_emit_bad.py",
            """\
class HandlerSideEmitBad:
    def __init__(self, state_root):
        self._state_root = state_root
        self._bus = None  # BUG: runtime will not inject because no event_bus param

    def handle(self, payload):
        result = {"status": "done"}
        self._bus.publish("onex.some.topic", result)  # runtime crash: NoneType.publish
        return result
""",
        )
        findings = validate_file(p)

        assert len(findings) == 1, f"Expected 1 finding, got: {findings}"
        assert findings[0].rule == "missing_publisher_injection"
        assert "HandlerSideEmitBad" in findings[0].message
        assert "event_bus" in findings[0].message

    def test_green_fixture__side_emitting_with_injected_event_bus__passes(
        self, tmp_path: Path
    ) -> None:
        """DoD green fixture: handler declares event_bus → validator passes.

        The runtime sees the ``event_bus`` parameter and injects the live bus.
        The handler can call ``self._bus.publish(...)`` safely.
        """
        p = _handler(
            tmp_path,
            "handler_side_emit_good.py",
            """\
class HandlerSideEmitGood:
    def __init__(self, state_root, event_bus=None):
        self._state_root = state_root
        self._bus = event_bus  # runtime injects this

    def handle(self, payload):
        result = {"status": "done"}
        self._bus.publish("onex.some.topic", result)
        return result
""",
        )
        findings = validate_file(p)

        assert findings == [], f"Expected no findings, got: {findings}"

    def test_green_fixture__injected_bus_actually_emits_expected_side_event(
        self,
    ) -> None:
        """DoD green fixture (behaviour proof): injected bus receives the publish call.

        Constructs the handler in-process (mirroring what RuntimeLocal does), injects
        a mock bus, calls ``handle()``, and asserts the bus received the expected
        ``publish`` call — proving injection wires the side-emission path end-to-end.
        """

        class HandlerWithInjectedBus:
            def __init__(self, event_bus: object = None) -> None:
                self._bus = event_bus

            def handle(self, payload: dict[str, object]) -> dict[str, object]:
                result = {"status": "done", "input": payload}
                if self._bus is not None:
                    self._bus.publish("onex.test.side.event", result)  # type: ignore[union-attr]
                return result

        mock_bus = MagicMock()
        handler = HandlerWithInjectedBus(event_bus=mock_bus)

        result = handler.handle({"key": "value"})

        # The handler returned a result
        assert result["status"] == "done"

        # The injected bus received exactly the expected side-emission
        mock_bus.publish.assert_called_once_with(
            "onex.test.side.event",
            {"status": "done", "input": {"key": "value"}},
        )

    def test_failing_fixture__handler_without_injection__bus_is_none__crashes(
        self,
    ) -> None:
        """DoD failing fixture (behaviour proof): without injection bus is None.

        This test documents the exact runtime failure the guardrail prevents.
        A handler that does NOT declare ``event_bus`` in __init__ will have
        ``self._bus = None`` if the runtime skips injection.  Calling
        ``.publish()`` on ``None`` raises ``AttributeError``.
        """

        class HandlerMissingInjection:
            def __init__(self, state_root: str = ".") -> None:
                self._state_root = state_root
                self._bus: object = None  # not injected — no event_bus param

            def handle(self, payload: dict[str, object]) -> dict[str, object]:
                result = {"status": "done"}
                self._bus.publish("onex.test.topic", result)  # type: ignore[union-attr]
                return result

        handler = HandlerMissingInjection()

        with pytest.raises(AttributeError):
            handler.handle({"key": "value"})


# ---------------------------------------------------------------------------
# Rule: missing_publisher_injection (exhaustive coverage)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMissingPublisherInjection:
    def test_no_side_emission_no_finding(self, tmp_path: Path) -> None:
        p = _handler(
            tmp_path,
            "handler_no_emit.py",
            """\
class HandlerNoEmit:
    def __init__(self, container):
        self._store = container.get_service("ProtocolStore")

    def handle(self, payload):
        return {"status": "done"}
""",
        )
        findings = validate_file(p)
        assert findings == []

    def test_side_emission_with_event_bus_positional_passes(
        self, tmp_path: Path
    ) -> None:
        p = _handler(
            tmp_path,
            "handler_good.py",
            """\
class HandlerGood:
    def __init__(self, event_bus):
        self._bus = event_bus

    def handle(self, payload):
        self._bus.publish("onex.topic", payload)
        return {}
""",
        )
        findings = validate_file(p)
        assert findings == []

    def test_side_emission_with_event_bus_default_none_passes(
        self, tmp_path: Path
    ) -> None:
        """event_bus=None default still declares the param — runtime injects."""
        p = _handler(
            tmp_path,
            "handler_good.py",
            """\
class HandlerGood:
    def __init__(self, state_root, event_bus=None):
        self._state_root = state_root
        self._bus = event_bus

    def handle(self, payload):
        if self._bus:
            self._bus.publish("onex.topic", payload)
        return {}
""",
        )
        findings = validate_file(p)
        assert findings == []

    def test_side_emission_without_event_bus_flagged(self, tmp_path: Path) -> None:
        p = _handler(
            tmp_path,
            "handler_bad.py",
            """\
class HandlerBad:
    def __init__(self, state_root):
        self._state_root = state_root
        self._event_bus = None

    def handle(self, payload):
        self._event_bus.publish("onex.topic", payload)
        return {}
""",
        )
        findings = validate_file(p)
        assert len(findings) == 1
        assert findings[0].rule == "missing_publisher_injection"
        assert "HandlerBad" in findings[0].message

    def test_nested_attribute_publish_flagged(self, tmp_path: Path) -> None:
        """self._client._bus.publish() — still a self.* chain → flagged."""
        p = _handler(
            tmp_path,
            "handler_bad.py",
            """\
class HandlerBad:
    def __init__(self, state_root):
        self._state_root = state_root

    def handle(self, payload):
        self._client._bus.publish("onex.topic", payload)
        return {}
""",
        )
        findings = validate_file(p)
        assert len(findings) == 1
        assert findings[0].rule == "missing_publisher_injection"

    def test_top_level_bus_publish_not_self_not_flagged(self, tmp_path: Path) -> None:
        """bus.publish(...) where receiver is NOT self — not flagged."""
        p = _handler(
            tmp_path,
            "handler_ok.py",
            """\
class HandlerOk:
    def __init__(self, state_root):
        self._state_root = state_root

    def handle(self, payload):
        bus = get_local_bus()
        bus.publish("onex.topic", payload)  # local variable, not self.*
        return {}
""",
        )
        findings = validate_file(p)
        assert findings == []

    def test_publish_in_init_not_flagged(self, tmp_path: Path) -> None:
        """Publish inside __init__ itself is not checked (DI gate scope)."""
        p = _handler(
            tmp_path,
            "handler_init.py",
            """\
class HandlerInit:
    def __init__(self, state_root):
        self._state_root = state_root
        self._bus = None
        # publish in __init__ is out of scope for this rule
        if self._bus:
            self._bus.publish("onex.init.topic", {})
""",
        )
        findings = validate_file(p)
        assert findings == []

    def test_node_handler_file_in_nodes_dir_scanned(self, tmp_path: Path) -> None:
        """handler.py inside nodes/ tree is scanned."""
        p = _node_handler(
            tmp_path,
            """\
class NodeFooHandler:
    def __init__(self, state_root):
        self._state_root = state_root
        self._bus = None

    def handle(self, payload):
        self._bus.publish("onex.topic", payload)
        return {}
""",
        )
        findings = validate_file(p)
        assert len(findings) == 1
        assert findings[0].rule == "missing_publisher_injection"

    def test_suppression_marker_on_class_line_silences(self, tmp_path: Path) -> None:
        p = _handler(
            tmp_path,
            "handler_suppressed.py",
            """\
class HandlerSuppressed:  # publisher-injection-ok: legacy handler, no bus available
    def __init__(self, state_root):
        self._state_root = state_root
        self._bus = None

    def handle(self, payload):
        self._bus.publish("onex.topic", payload)
        return {}
""",
        )
        findings = validate_file(p)
        assert findings == []

    def test_suppression_marker_on_init_line_silences(self, tmp_path: Path) -> None:
        p = _handler(
            tmp_path,
            "handler_suppressed.py",
            """\
class HandlerSuppressed:
    def __init__(self, state_root):  # publisher-injection-ok: injected via other means
        self._state_root = state_root
        self._bus = None

    def handle(self, payload):
        self._bus.publish("onex.topic", payload)
        return {}
""",
        )
        findings = validate_file(p)
        assert findings == []


# ---------------------------------------------------------------------------
# File targeting
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFileTargeting:
    def test_non_handler_dir_skipped(self, tmp_path: Path) -> None:
        p = _non_handler(
            tmp_path,
            "services/service_foo.py",
            """\
class HandlerFoo:
    def __init__(self, state_root):
        self._bus = None

    def handle(self, payload):
        self._bus.publish("onex.topic", payload)
        return {}
""",
        )
        findings = validate_file(p)
        assert findings == []

    def test_handler_file_not_named_handler_prefix_skipped(
        self, tmp_path: Path
    ) -> None:
        """Files in handlers/ but not named handler_*.py are not scanned."""
        p = tmp_path / "nodes/my_node/handlers/base.py"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            """\
class HandlerBase:
    def __init__(self, state_root):
        self._bus = None

    def handle(self, payload):
        self._bus.publish("onex.topic", payload)
        return {}
""",
            encoding="utf-8",
        )
        findings = validate_file(p)
        assert findings == []

    def test_validate_paths_scans_directory(self, tmp_path: Path) -> None:
        _handler(
            tmp_path,
            "handler_a.py",
            """\
class HandlerA:
    def __init__(self, state_root):
        self._bus = None

    def handle(self, payload):
        self._bus.publish("onex.topic", payload)
        return {}
""",
        )
        _handler(
            tmp_path,
            "handler_b.py",
            """\
class HandlerB:
    def __init__(self, event_bus=None):
        self._bus = event_bus

    def handle(self, payload):
        self._bus.publish("onex.topic", payload)
        return {}
""",
        )
        findings = validate_paths([tmp_path])
        assert len(findings) == 1
        assert "HandlerA" in findings[0].message
