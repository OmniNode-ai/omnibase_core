# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for transport_mock_lint validator (OMN-13026).

Covers:
- bare AsyncMock/MagicMock on event_bus assignment target → FAIL
- bare AsyncMock/MagicMock on kafka keyword argument → FAIL
- AsyncMock with spec= → PASS
- MagicMock with spec_set= → PASS
- suppression token → PASS
- non-transport variable name (e.g. plain "handler") → PASS
- annotated assignment (event_bus: X = AsyncMock()) → FAIL
- synthetic violation confirming gate demonstrates red output (DoD: reverting
  #1181 fix fails the gate)
"""

from pathlib import Path

import pytest

from omnibase_core.validators.transport_mock_lint import (
    SUPPRESSION_TOKEN,
    Finding,
    validate_file,
    validate_paths,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _test_file(tmp_path: Path, name: str, content: str) -> Path:
    """Write a test file at tests/<name> under tmp_path."""
    p = tmp_path / "tests" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _non_test_file(tmp_path: Path, name: str, content: str) -> Path:
    """Write a non-test file at src/<name> under tmp_path."""
    p = tmp_path / "src" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Assignment-target detection (Case 1: simple assignment)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSimpleAssignmentTarget:
    def test_bare_asyncmock_on_event_bus_fails(self, tmp_path: Path) -> None:
        p = _test_file(
            tmp_path,
            "test_example.py",
            "from unittest.mock import AsyncMock\nevent_bus = AsyncMock()\n",
        )
        findings = validate_file(p)
        assert len(findings) == 1
        assert isinstance(findings[0], Finding)
        assert findings[0].mock_name == "AsyncMock"
        assert findings[0].surface_name == "event_bus"

    def test_bare_magicmock_on_kafka_fails(self, tmp_path: Path) -> None:
        p = _test_file(
            tmp_path,
            "test_example.py",
            "from unittest.mock import MagicMock\nkafka = MagicMock()\n",
        )
        findings = validate_file(p)
        assert len(findings) == 1
        assert findings[0].mock_name == "MagicMock"
        assert findings[0].surface_name == "kafka"

    def test_bare_asyncmock_on_transport_fails(self, tmp_path: Path) -> None:
        p = _test_file(
            tmp_path,
            "test_example.py",
            "from unittest.mock import AsyncMock\ntransport = AsyncMock()\n",
        )
        findings = validate_file(p)
        assert len(findings) == 1

    def test_asyncmock_with_spec_passes(self, tmp_path: Path) -> None:
        p = _test_file(
            tmp_path,
            "test_example.py",
            "from unittest.mock import AsyncMock\n"
            "from omnibase_core.protocols.event_bus.protocol_event_bus_base import ProtocolEventBusBase\n"
            "event_bus = AsyncMock(spec=ProtocolEventBusBase)\n",
        )
        findings = validate_file(p)
        assert findings == []

    def test_asyncmock_with_spec_set_passes(self, tmp_path: Path) -> None:
        p = _test_file(
            tmp_path,
            "test_example.py",
            "from unittest.mock import AsyncMock\n"
            "event_bus = AsyncMock(spec_set=SomeClass)\n",
        )
        findings = validate_file(p)
        assert findings == []

    def test_non_transport_variable_passes(self, tmp_path: Path) -> None:
        p = _test_file(
            tmp_path,
            "test_example.py",
            "from unittest.mock import AsyncMock\nhandler = AsyncMock()\n",
        )
        findings = validate_file(p)
        assert findings == []

    def test_suppression_token_passes(self, tmp_path: Path) -> None:
        p = _test_file(
            tmp_path,
            "test_example.py",
            f"from unittest.mock import AsyncMock\n"
            f"event_bus = AsyncMock()  {SUPPRESSION_TOKEN} protocol not importable here\n",
        )
        findings = validate_file(p)
        assert findings == []

    def test_bus_suffix_variable_fails(self, tmp_path: Path) -> None:
        """Variable name 'owned_bus' should trigger (contains 'bus')."""
        p = _test_file(
            tmp_path,
            "test_example.py",
            "from unittest.mock import AsyncMock\nowned_bus = AsyncMock()\n",
        )
        findings = validate_file(p)
        assert len(findings) == 1

    def test_publisher_variable_fails(self, tmp_path: Path) -> None:
        p = _test_file(
            tmp_path,
            "test_example.py",
            "from unittest.mock import MagicMock\nkafka_publisher = MagicMock()\n",
        )
        findings = validate_file(p)
        assert len(findings) == 1


# ---------------------------------------------------------------------------
# Annotated assignment (Case 2)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAnnotatedAssignment:
    def test_bare_asyncmock_annotated_event_bus_fails(self, tmp_path: Path) -> None:
        p = _test_file(
            tmp_path,
            "test_example.py",
            "from unittest.mock import AsyncMock\nevent_bus: object = AsyncMock()\n",
        )
        findings = validate_file(p)
        assert len(findings) == 1

    def test_annotated_with_spec_passes(self, tmp_path: Path) -> None:
        p = _test_file(
            tmp_path,
            "test_example.py",
            "from unittest.mock import AsyncMock\n"
            "event_bus: object = AsyncMock(spec=SomeProto)\n",
        )
        findings = validate_file(p)
        assert findings == []


# ---------------------------------------------------------------------------
# Keyword argument at call site (Case 3)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestKeywordArgument:
    def test_bare_asyncmock_kwarg_event_bus_fails(self, tmp_path: Path) -> None:
        """SomeHandler(event_bus=AsyncMock()) should fail."""
        p = _test_file(
            tmp_path,
            "test_example.py",
            "from unittest.mock import AsyncMock\n"
            "handler = SomeHandler(event_bus=AsyncMock())\n",
        )
        findings = validate_file(p)
        assert len(findings) == 1
        assert findings[0].surface_name == "event_bus"

    def test_bare_magicmock_kwarg_kafka_publisher_fails(self, tmp_path: Path) -> None:
        p = _test_file(
            tmp_path,
            "test_example.py",
            "from unittest.mock import MagicMock\n"
            "obj = SomeClass(kafka_publisher=MagicMock())\n",
        )
        findings = validate_file(p)
        assert len(findings) == 1

    def test_kwarg_with_spec_passes(self, tmp_path: Path) -> None:
        p = _test_file(
            tmp_path,
            "test_example.py",
            "from unittest.mock import AsyncMock\n"
            "handler = SomeHandler(event_bus=AsyncMock(spec=ProtocolEventBus))\n",
        )
        findings = validate_file(p)
        assert findings == []

    def test_non_transport_kwarg_passes(self, tmp_path: Path) -> None:
        p = _test_file(
            tmp_path,
            "test_example.py",
            "from unittest.mock import AsyncMock\n"
            "handler = SomeHandler(container=AsyncMock())\n",
        )
        findings = validate_file(p)
        assert findings == []


# ---------------------------------------------------------------------------
# File type filtering (only test files scanned)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFileTypeFiltering:
    def test_source_file_skipped(self, tmp_path: Path) -> None:
        """A src/ file that is not a test file should not be scanned."""
        p = _non_test_file(
            tmp_path,
            "module.py",
            "from unittest.mock import AsyncMock\nevent_bus = AsyncMock()\n",
        )
        findings = validate_file(p)
        # validate_file scans the file but _should_scan filters by name;
        # however validate_file itself does NOT filter — filtering is done
        # at validate_paths level.
        # Direct validate_file call processes what's given; path-level filtering
        # is only applied via validate_paths.
        _ = findings  # We test validate_paths filtering below.

    def test_validate_paths_skips_non_test_files(self, tmp_path: Path) -> None:
        """validate_paths should skip src/ files that are not test_*.py."""
        p = _non_test_file(
            tmp_path,
            "module.py",
            "from unittest.mock import AsyncMock\nevent_bus = AsyncMock()\n",
        )
        findings = validate_paths([p])
        assert findings == []

    def test_validate_paths_scans_test_files(self, tmp_path: Path) -> None:
        p = _test_file(
            tmp_path,
            "test_bus.py",
            "from unittest.mock import AsyncMock\nevent_bus = AsyncMock()\n",
        )
        findings = validate_paths([p])
        assert len(findings) == 1

    def test_validate_paths_directory_scan(self, tmp_path: Path) -> None:
        """validate_paths directory scan finds violations in nested test files."""
        p = _test_file(
            tmp_path,
            "test_nested.py",
            "from unittest.mock import MagicMock\nevent_bus = MagicMock()\n",
        )
        _ = p
        findings = validate_paths([tmp_path])
        assert len(findings) == 1


# ---------------------------------------------------------------------------
# Synthetic violation — DoD requirement: "reverting #1181 fix fails the gate"
#
# This test directly asserts that the gate catches the exact pattern from
# PR #1181: bare AsyncMock() bound to an EventBusKafka mock surface without
# spec=.  The gate MUST report at least one finding for this input.
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSyntheticViolation:
    """Proves the gate catches the pattern that caused the #1181 incident."""

    def test_pr_1181_pattern_fails_gate(self, tmp_path: Path) -> None:
        """Bare AsyncMock without spec= on EventBusKafka surface must be caught."""
        p = _test_file(
            tmp_path,
            "test_generation_publisher.py",
            # Exact pattern from PR #1181:
            "from unittest.mock import AsyncMock\n"
            "from omnibase_infra.event_bus.event_bus_kafka import EventBusKafka\n"
            "\n"
            "def test_publisher():\n"
            "    event_bus = AsyncMock()  # bare — no spec=EventBusKafka\n"
            "    # This silently allowed .stop() which doesn't exist on EventBusKafka\n",
        )
        findings = validate_file(p)
        assert len(findings) == 1, (
            "transport-mock-lint must catch bare AsyncMock() on 'event_bus' "
            "surface (PR #1181 regression pattern)"
        )
        assert findings[0].mock_name == "AsyncMock"
        assert "bus" in findings[0].surface_name.lower()

    def test_pr_1181_fixed_passes_gate(self, tmp_path: Path) -> None:
        """With spec=EventBusKafka the gate must NOT fire."""
        p = _test_file(
            tmp_path,
            "test_generation_publisher.py",
            "from unittest.mock import AsyncMock\n"
            "from omnibase_infra.event_bus.event_bus_kafka import EventBusKafka\n"
            "\n"
            "def test_publisher():\n"
            "    event_bus = AsyncMock(spec=EventBusKafka)\n",
        )
        findings = validate_file(p)
        assert findings == [], (
            "AsyncMock(spec=EventBusKafka) is compliant — gate must not fire"
        )


# ---------------------------------------------------------------------------
# Multiple findings in one file
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMultipleFindings:
    def test_multiple_violations_all_reported(self, tmp_path: Path) -> None:
        p = _test_file(
            tmp_path,
            "test_multi.py",
            "from unittest.mock import AsyncMock, MagicMock\n"
            "event_bus = AsyncMock()\n"
            "kafka_publisher = MagicMock()\n"
            "transport = AsyncMock()\n",
        )
        findings = validate_file(p)
        assert len(findings) == 3

    def test_mixed_good_bad(self, tmp_path: Path) -> None:
        p = _test_file(
            tmp_path,
            "test_mixed.py",
            "from unittest.mock import AsyncMock, MagicMock\n"
            "event_bus = AsyncMock(spec=SomeProto)\n"
            "kafka = MagicMock()\n",
        )
        findings = validate_file(p)
        assert len(findings) == 1
        assert findings[0].surface_name == "kafka"


# ---------------------------------------------------------------------------
# Attribute-style imports (mock.AsyncMock / mock.MagicMock)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAttributeStyleImport:
    def test_attribute_style_asyncmock_fails(self, tmp_path: Path) -> None:
        p = _test_file(
            tmp_path,
            "test_attr.py",
            "import unittest.mock as mock\nevent_bus = mock.AsyncMock()\n",
        )
        findings = validate_file(p)
        assert len(findings) == 1

    def test_attribute_style_with_spec_passes(self, tmp_path: Path) -> None:
        p = _test_file(
            tmp_path,
            "test_attr.py",
            "import unittest.mock as mock\n"
            "event_bus = mock.AsyncMock(spec=SomeProto)\n",
        )
        findings = validate_file(p)
        assert findings == []
