# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for validate_no_none_guard_publish.py (OMN-10818)."""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "validation"))

from validate_no_none_guard_publish import NoneGuardPublishDetector, scan_python_source


class TestNoneGuardPublishDetector:
    """Tests for none-guard-before-publish detection."""

    def _detect(self, code: str) -> list[tuple[int, str]]:
        source_lines = code.splitlines()
        tree = ast.parse(code)
        detector = NoneGuardPublishDetector(source_lines)
        detector.visit(tree)
        return detector.violations

    def test_detects_self_event_bus_none_guard_publish(self):
        code = """
class MyHandler:
    def handle(self, event):
        if self._event_bus is not None:
            self._event_bus.publish(event)
"""
        viols = self._detect(code)
        assert len(viols) == 1

    def test_detects_self_event_bus_attr_none_guard(self):
        code = """
class MyHandler:
    def handle(self, event):
        if self.event_bus is not None:
            self.event_bus.emit(event)
"""
        viols = self._detect(code)
        assert len(viols) == 1

    def test_detects_local_event_bus_none_guard(self):
        code = """
def publish_if_available(event_bus, event):
    if event_bus is not None:
        event_bus.dispatch(event)
"""
        viols = self._detect(code)
        assert len(viols) == 1

    def test_detects_truthy_guard(self):
        """if event_bus: ... is equivalent to none guard."""
        code = """
def run(event_bus, event):
    if event_bus:
        event_bus.send(event)
"""
        viols = self._detect(code)
        assert len(viols) == 1

    def test_detects_send_method(self):
        code = """
class H:
    def handle(self, e):
        if self._event_bus is not None:
            self._event_bus.send(e)
"""
        viols = self._detect(code)
        assert len(viols) == 1

    def test_detects_emit_method(self):
        code = """
class H:
    def handle(self, e):
        if self._event_bus is not None:
            self._event_bus.emit(e)
"""
        viols = self._detect(code)
        assert len(viols) == 1

    def test_allows_unconditional_publish(self):
        """Required bus — no guard needed."""
        code = """
class H:
    def handle(self, e):
        self._event_bus.publish(e)
"""
        viols = self._detect(code)
        assert len(viols) == 0

    def test_allows_none_guard_without_publish(self):
        """Guard without a publish/emit call is fine."""
        code = """
class H:
    def handle(self, e):
        if self._event_bus is not None:
            result = self._event_bus.get_topic()
"""
        viols = self._detect(code)
        assert len(viols) == 0

    def test_allows_none_guard_ok_annotation(self):
        code = """
class H:
    def handle(self, e):
        if self._event_bus is not None:  # none-guard-ok: optional bus in test harness
            self._event_bus.publish(e)
"""
        viols = self._detect(code)
        assert len(viols) == 0

    def test_detects_multiple_violations(self):
        code = """
class H:
    def a(self, e):
        if self._event_bus is not None:
            self._event_bus.publish(e)

    def b(self, e):
        if self.event_bus is not None:
            self.event_bus.emit(e)
"""
        viols = self._detect(code)
        assert len(viols) == 2

    def test_no_false_positive_non_bus_guard(self):
        """None-guarding a non-bus object is fine."""
        code = """
class H:
    def handle(self):
        if self._db is not None:
            self._db.execute("SELECT 1")
"""
        viols = self._detect(code)
        assert len(viols) == 0


class TestScanPythonSource:
    def test_scan_violating_source(self, tmp_path: Path):
        f = tmp_path / "bad.py"
        f.write_text(
            """
class H:
    def handle(self, e):
        if self._event_bus is not None:
            self._event_bus.publish(e)
""",
            encoding="utf-8",
        )
        viols = scan_python_source(f)
        assert len(viols) == 1

    def test_scan_clean_source(self, tmp_path: Path):
        f = tmp_path / "ok.py"
        f.write_text(
            """
class H:
    def handle(self, e):
        self._event_bus.publish(e)
""",
            encoding="utf-8",
        )
        viols = scan_python_source(f)
        assert viols == []

    def test_scan_skips_test_files(self, tmp_path: Path):
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        f = tests_dir / "test_h.py"
        f.write_text(
            """
class H:
    def handle(self, e):
        if self._event_bus is not None:
            self._event_bus.publish(e)
""",
            encoding="utf-8",
        )
        viols = scan_python_source(f)
        assert viols == []
