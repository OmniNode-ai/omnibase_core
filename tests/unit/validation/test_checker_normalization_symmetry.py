# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for checker_normalization_symmetry.

Detects producer/consumer topic-normalization asymmetry — specifically the
OMN-9215 class where a producer emits ``.send(TopicBase.X.strip(), ...)`` while
the consumer does ``.subscribe([TopicBase.X])`` unchanged, leading to dispatcher
key drift.

Minimum viable scope (OMN-9333):
    * `.strip()` asymmetry on TopicBase.X arguments to send/subscribe/handler_for.
    * Follow-ups filed: OMN-9339 (Pydantic), OMN-9340 (casefold), OMN-9341 (contract YAML).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.validation.checker_normalization_symmetry import (
    NormalizationSymmetryChecker,
    scan_source_tree,
)

pytestmark = pytest.mark.unit


RED_PRODUCER_SOURCE = '''
"""Producer that strips whitespace off the topic before emit — OMN-9215 pattern."""
from omnibase_core.topics import TopicBase


class _Producer:
    def emit(self) -> None:
        topic = TopicBase.SESSION_STARTED.strip()
        self._bus.send(topic, {"foo": "bar"})
'''

RED_CONSUMER_SOURCE = '''
"""Consumer that subscribes to the raw TopicBase value — no strip."""
from omnibase_core.topics import TopicBase


class _Consumer:
    def register(self) -> None:
        self._bus.subscribe([TopicBase.SESSION_STARTED])
'''


GREEN_SYMMETRIC_STRIP_SOURCE = '''
"""Both sides strip — symmetric, validator should pass."""
from omnibase_core.topics import TopicBase


class _Producer:
    def emit(self) -> None:
        topic = TopicBase.SESSION_STARTED.strip()
        self._bus.send(topic, {})


class _Consumer:
    def register(self) -> None:
        self._bus.subscribe([TopicBase.SESSION_STARTED.strip()])
'''


GREEN_SYMMETRIC_RAW_SOURCE = '''
"""Neither side strips — symmetric, validator should pass."""
from omnibase_core.topics import TopicBase


class _Producer:
    def emit(self) -> None:
        self._bus.send(TopicBase.SESSION_STARTED, {})


class _Consumer:
    def register(self) -> None:
        self._bus.subscribe([TopicBase.SESSION_STARTED])
'''


def _write_fixture(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source)
    return path


class TestNormalizationSymmetryChecker:
    def test_flags_omn9215_whitespace_asymmetry(self, tmp_path: Path) -> None:
        _write_fixture(tmp_path, "producer.py", RED_PRODUCER_SOURCE)
        _write_fixture(tmp_path, "consumer.py", RED_CONSUMER_SOURCE)

        issues = scan_source_tree(tmp_path)

        assert len(issues) == 1, f"expected one asymmetry finding, got: {issues}"
        issue = issues[0]
        assert "SESSION_STARTED" in issue.message
        assert "strip" in issue.message.lower()
        assert "producer" in issue.message.lower()
        assert "consumer" in issue.message.lower()

    def test_passes_when_both_sides_strip(self, tmp_path: Path) -> None:
        _write_fixture(tmp_path, "symmetric_strip.py", GREEN_SYMMETRIC_STRIP_SOURCE)

        issues = scan_source_tree(tmp_path)

        assert issues == [], f"unexpected findings on symmetric-strip fixture: {issues}"

    def test_passes_when_neither_side_strips(self, tmp_path: Path) -> None:
        _write_fixture(tmp_path, "symmetric_raw.py", GREEN_SYMMETRIC_RAW_SOURCE)

        issues = scan_source_tree(tmp_path)

        assert issues == [], f"unexpected findings on symmetric-raw fixture: {issues}"

    def test_passes_when_no_topicbase_refs(self, tmp_path: Path) -> None:
        _write_fixture(
            tmp_path,
            "unrelated.py",
            "def f() -> int:\n    return 42\n",
        )

        issues = scan_source_tree(tmp_path)

        assert issues == []

    def test_ignores_producer_only_files(self, tmp_path: Path) -> None:
        """Producer emits with strip but no consumer anywhere — no asymmetry to flag."""
        _write_fixture(tmp_path, "producer_only.py", RED_PRODUCER_SOURCE)

        issues = scan_source_tree(tmp_path)

        assert issues == []

    def test_checker_visitor_records_topic_uses(self) -> None:
        """The ast.NodeVisitor records producer and consumer topic uses per file."""
        import ast

        tree = ast.parse(RED_PRODUCER_SOURCE)
        checker = NormalizationSymmetryChecker("producer.py")
        checker.visit(tree)

        assert len(checker.topic_uses) == 1
        use = checker.topic_uses[0]
        assert use.role == "producer"
        assert use.topic_name == "SESSION_STARTED"
        assert use.normalizations == ("strip",)

    def test_scope_isolation_prevents_cross_function_binding_reuse(
        self, tmp_path: Path
    ) -> None:
        """A topic binding in one function must not resolve in a sibling function."""
        source = """
from omnibase_core.topics import TopicBase

class _Handler:
    def setup(self) -> None:
        topic = TopicBase.SESSION_STARTED.strip()
        self._bus.send(topic, {})

    def teardown(self) -> None:
        # `topic` is not defined here; should NOT inherit from setup()
        self._bus.subscribe([TopicBase.SESSION_STARTED])
"""
        _write_fixture(tmp_path, "scope_test.py", source)
        issues = scan_source_tree(tmp_path)
        # Both sides use SESSION_STARTED; producer strips, consumer does not —
        # correctly flagged. Key assertion: the issue references teardown's consumer,
        # not a phantom binding carried over from setup.
        assert len(issues) == 1
        issue = issues[0]
        assert "SESSION_STARTED" in issue.message

    def test_divergent_pair_reporting_picks_actual_mismatch(
        self, tmp_path: Path
    ) -> None:
        """Issue message should cite the actually divergent producer+consumer pair."""
        source = """
from omnibase_core.topics import TopicBase

class _Mixed:
    def produce_strip(self) -> None:
        self._bus.send(TopicBase.SESSION_STARTED.strip(), {})

    def consume_raw(self) -> None:
        self._bus.subscribe([TopicBase.SESSION_STARTED])
"""
        _write_fixture(tmp_path, "mixed.py", source)
        issues = scan_source_tree(tmp_path)
        assert len(issues) == 1
        issue = issues[0]
        # The reported producer normalizations must be the divergent one (strip)
        assert "strip" in issue.message.lower()
