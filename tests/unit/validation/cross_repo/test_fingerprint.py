# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for fingerprint utility.

Verifies determinism, uniqueness, and format of fingerprints
used for baseline tracking in cross-repo validation.

Related ticket: OMN-1774
"""

from __future__ import annotations

import pytest

from omnibase_core.validation.cross_repo.util_fingerprint import generate_fingerprint


class TestGenerateFingerprint:
    """Tests for generate_fingerprint function."""

    def test_fingerprint_stability_same_inputs_same_output(self) -> None:
        """Verify same inputs always produce same fingerprint."""
        rule_id = "repo_boundaries"
        file_path = "src/app/handler.py"
        symbol = "infra.services.kafka"

        # Generate multiple fingerprints with same inputs
        fp1 = generate_fingerprint(rule_id, file_path, symbol)
        fp2 = generate_fingerprint(rule_id, file_path, symbol)
        fp3 = generate_fingerprint(rule_id, file_path, symbol)

        assert fp1 == fp2 == fp3

    def test_fingerprint_uniqueness_different_rule_id(self) -> None:
        """Verify different rule_id produces different fingerprint."""
        file_path = "src/app/handler.py"
        symbol = "infra.services.kafka"

        fp1 = generate_fingerprint("repo_boundaries", file_path, symbol)
        fp2 = generate_fingerprint("forbidden_imports", file_path, symbol)

        assert fp1 != fp2

    def test_fingerprint_uniqueness_different_file_path(self) -> None:
        """Verify different file_path produces different fingerprint."""
        rule_id = "repo_boundaries"
        symbol = "infra.services.kafka"

        fp1 = generate_fingerprint(rule_id, "src/app/handler.py", symbol)
        fp2 = generate_fingerprint(rule_id, "src/app/service.py", symbol)

        assert fp1 != fp2

    def test_fingerprint_uniqueness_different_symbol(self) -> None:
        """Verify different symbol produces different fingerprint."""
        rule_id = "repo_boundaries"
        file_path = "src/app/handler.py"

        fp1 = generate_fingerprint(rule_id, file_path, "infra.services.kafka")
        fp2 = generate_fingerprint(rule_id, file_path, "infra.services.redis")

        assert fp1 != fp2

    def test_fingerprint_format_16_hex_chars(self) -> None:
        """Verify fingerprint is exactly 16 lowercase hex characters."""
        fp = generate_fingerprint("test_rule", "test/file.py", "test.module")

        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)

    def test_fingerprint_with_empty_strings(self) -> None:
        """Verify fingerprint works with empty strings."""
        fp = generate_fingerprint("", "", "")

        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)

    def test_fingerprint_with_special_characters(self) -> None:
        """Verify fingerprint handles special characters."""
        fp = generate_fingerprint(
            "rule/with:special",
            "path/with spaces/file.py",
            "module.with-dashes.and_underscores",
        )

        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)

    def test_fingerprint_with_unicode(self) -> None:
        """Verify fingerprint handles unicode characters."""
        fp = generate_fingerprint(
            "rule_test",
            "path/to/file.py",
            "module.with.unicode",
        )

        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)

    def test_fingerprint_whitespace_normalization(self) -> None:
        """Verify leading/trailing whitespace is normalized."""
        fp1 = generate_fingerprint("rule", "path/file.py", "module.name")
        fp2 = generate_fingerprint("  rule  ", "  path/file.py  ", "  module.name  ")

        assert fp1 == fp2

    def test_fingerprint_order_matters(self) -> None:
        """Verify argument order affects fingerprint."""
        # Swapping arguments should produce different fingerprints
        fp1 = generate_fingerprint("a", "b", "c")
        fp2 = generate_fingerprint("b", "a", "c")
        fp3 = generate_fingerprint("c", "b", "a")

        assert fp1 != fp2
        assert fp2 != fp3
        assert fp1 != fp3

    def test_fingerprint_no_collision_similar_inputs(self) -> None:
        """Verify no collision for similar but different inputs."""
        # These could potentially collide if not properly delimited
        fp1 = generate_fingerprint("ab", "cd", "ef")
        fp2 = generate_fingerprint("abc", "d", "ef")
        fp3 = generate_fingerprint("ab", "c", "def")

        assert fp1 != fp2
        assert fp2 != fp3
        assert fp1 != fp3

    @pytest.mark.parametrize(
        ("rule_id", "file_path", "symbol"),
        [
            ("repo_boundaries", "src/main.py", "os.path"),
            ("forbidden_imports", "tests/test_main.py", "internal.module"),
            ("topic_conventions", "src/events/handler.py", "kafka.producer"),
            ("error_taxonomy", "src/errors/custom.py", "base.error"),
        ],
    )
    def test_fingerprint_various_inputs(
        self, rule_id: str, file_path: str, symbol: str
    ) -> None:
        """Verify fingerprint works with various realistic inputs."""
        fp = generate_fingerprint(rule_id, file_path, symbol)

        assert len(fp) == 16
        assert all(c in "0123456789abcdef" for c in fp)

    def test_fingerprint_determinism_across_multiple_calls(self) -> None:
        """Stress test: verify determinism across many calls."""
        inputs = [
            ("rule1", "path1.py", "sym1"),
            ("rule2", "path2.py", "sym2"),
            ("rule3", "path3.py", "sym3"),
        ]

        # Generate fingerprints in first pass
        first_pass = [generate_fingerprint(r, p, s) for r, p, s in inputs]

        # Generate again in second pass
        second_pass = [generate_fingerprint(r, p, s) for r, p, s in inputs]

        assert first_pass == second_pass
