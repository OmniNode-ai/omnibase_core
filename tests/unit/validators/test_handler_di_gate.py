# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for handler_di_gate validator (OMN-10726)."""

from pathlib import Path

import pytest

from omnibase_core.validators.handler_di_gate import validate_file, validate_paths

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _handler(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / f"nodes/my_node/handlers/{name}"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _node_file(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "nodes/my_node/node.py"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _non_handler(tmp_path: Path, name: str, content: str) -> Path:
    """A Python file NOT in a handlers/ directory."""
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Rule: constructor_signature
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConstructorSignature:
    def test_good_handler_container_only_passes(self, tmp_path: Path) -> None:
        p = _handler(
            tmp_path,
            "handler_foo.py",
            """\
class HandlerFoo:
    def __init__(self, container):
        self._bus = container.get_service("ProtocolEventBus")
""",
        )
        findings = validate_file(p, frozenset({"constructor_signature"}))
        assert findings == []

    def test_good_handler_container_annotated_passes(self, tmp_path: Path) -> None:
        p = _handler(
            tmp_path,
            "handler_foo.py",
            """\
class HandlerFoo:
    def __init__(self, container: ModelONEXContainer) -> None:
        self._bus = container.get_service("ProtocolEventBus")
""",
        )
        findings = validate_file(p, frozenset({"constructor_signature"}))
        assert findings == []

    def test_extra_param_flagged(self, tmp_path: Path) -> None:
        p = _handler(
            tmp_path,
            "handler_bad.py",
            """\
class HandlerBad:
    def __init__(self, container, event_bus):
        self._bus = event_bus
""",
        )
        findings = validate_file(p, frozenset({"constructor_signature"}))
        assert len(findings) == 1
        assert findings[0].rule == "constructor_signature"
        assert "HandlerBad" in findings[0].message
        assert "event_bus" in findings[0].message

    def test_wrong_param_name_flagged(self, tmp_path: Path) -> None:
        p = _handler(
            tmp_path,
            "handler_bad.py",
            """\
class HandlerBad:
    def __init__(self, event_bus):
        self._bus = event_bus
""",
        )
        findings = validate_file(p, frozenset({"constructor_signature"}))
        assert len(findings) == 1
        assert findings[0].rule == "constructor_signature"

    def test_no_params_after_self_passes(self, tmp_path: Path) -> None:
        """Parameterless __init__ has no signature violation (direct_construction rule covers it)."""
        p = _handler(
            tmp_path,
            "handler_foo.py",
            """\
class HandlerFoo:
    def __init__(self):
        pass
""",
        )
        findings = validate_file(p, frozenset({"constructor_signature"}))
        assert findings == []

    def test_suppression_marker_silences(self, tmp_path: Path) -> None:
        p = _handler(
            tmp_path,
            "handler_bad.py",
            """\
class HandlerBad:
    def __init__(self, container, extra):  # handler-di-ok: legacy param
        pass
""",
        )
        findings = validate_file(p, frozenset({"constructor_signature"}))
        assert findings == []


# ---------------------------------------------------------------------------
# Rule: direct_construction
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDirectConstruction:
    def test_container_resolve_passes(self, tmp_path: Path) -> None:
        p = _handler(
            tmp_path,
            "handler_foo.py",
            """\
class HandlerFoo:
    def __init__(self, container):
        self._bus = container.resolve("ProtocolEventBus")
        self._store = container.get_service("ProtocolStore")
""",
        )
        findings = validate_file(p, frozenset({"direct_construction"}))
        assert findings == []

    def test_direct_event_bus_construction_flagged(self, tmp_path: Path) -> None:
        p = _handler(
            tmp_path,
            "handler_bad.py",
            """\
from omnibase_infra.event_bus import EventBusInmemory

class HandlerBad:
    def __init__(self, container):
        self._bus = EventBusInmemory()
""",
        )
        findings = validate_file(p, frozenset({"direct_construction"}))
        assert len(findings) == 1
        assert findings[0].rule == "direct_construction"
        assert "EventBusInmemory" in findings[0].message

    def test_direct_db_connection_flagged(self, tmp_path: Path) -> None:
        p = _handler(
            tmp_path,
            "handler_bad.py",
            """\
import sqlite3

class HandlerBad:
    def __init__(self, container):
        self._conn = sqlite3.connect(":memory:")
""",
        )
        findings = validate_file(p, frozenset({"direct_construction"}))
        assert len(findings) == 1
        assert findings[0].rule == "direct_construction"
        assert "sqlite3.connect" in findings[0].message

    def test_direct_adapter_construction_flagged(self, tmp_path: Path) -> None:
        p = _handler(
            tmp_path,
            "handler_bad.py",
            """\
class HandlerBad:
    def __init__(self, container):
        self._adapter = SomeAdapter()
""",
        )
        findings = validate_file(p, frozenset({"direct_construction"}))
        assert len(findings) == 1
        assert findings[0].rule == "direct_construction"
        assert "SomeAdapter" in findings[0].message

    def test_suppression_marker_silences(self, tmp_path: Path) -> None:
        p = _handler(
            tmp_path,
            "handler_bad.py",
            """\
class HandlerBad:
    def __init__(self, container):
        self._bus = EventBusInmemory()  # handler-di-ok: test-only shim
""",
        )
        findings = validate_file(p, frozenset({"direct_construction"}))
        assert findings == []

    def test_non_self_assignment_not_flagged(self, tmp_path: Path) -> None:
        """Local variable assignments are not flagged."""
        p = _handler(
            tmp_path,
            "handler_foo.py",
            """\
class HandlerFoo:
    def __init__(self, container):
        local = SomeHelper()
        self._bus = container.get_service("ProtocolEventBus")
""",
        )
        findings = validate_file(p, frozenset({"direct_construction"}))
        assert findings == []


# ---------------------------------------------------------------------------
# File targeting
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFileTargeting:
    def test_non_handler_class_in_non_handler_dir_skipped(self, tmp_path: Path) -> None:
        """Classes outside handlers/ and nodes/ directories are not scanned."""
        p = _non_handler(
            tmp_path,
            "services/service_foo.py",
            """\
class HandlerFoo:
    def __init__(self, container, extra):
        self._bus = EventBusInmemory()
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
    def __init__(self, container, extra):
        self._bus = EventBusInmemory()
""",
            encoding="utf-8",
        )
        findings = validate_file(p)
        assert findings == []

    def test_node_py_file_is_scanned(self, tmp_path: Path) -> None:
        p = _node_file(
            tmp_path,
            """\
class NodeFoo:
    def __init__(self, container, extra_dep):
        pass
""",
        )
        findings = validate_file(p, frozenset({"constructor_signature"}))
        assert len(findings) == 1

    def test_validate_paths_scans_directory(self, tmp_path: Path) -> None:
        _handler(
            tmp_path,
            "handler_a.py",
            """\
class HandlerA:
    def __init__(self, container, event_bus):
        pass
""",
        )
        _handler(
            tmp_path,
            "handler_b.py",
            """\
class HandlerB:
    def __init__(self, container):
        self._bus = container.get_service("ProtocolEventBus")
""",
        )
        findings = validate_paths([tmp_path], frozenset({"constructor_signature"}))
        assert len(findings) == 1
        assert "HandlerA" in findings[0].message
