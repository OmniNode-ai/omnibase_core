"""Tests for duplicate_protocols rule.

Related ticket: OMN-1906
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.validation.model_rule_configs import (
    ModelRuleDuplicateProtocolsConfig,
)
from omnibase_core.validation.cross_repo.rules.rule_duplicate_protocols import (
    RuleDuplicateProtocols,
)
from omnibase_core.validation.cross_repo.scanners.scanner_import_graph import (
    ModelFileImports,
)


@pytest.mark.unit
class TestRuleDuplicateProtocols:
    """Tests for RuleDuplicateProtocols."""

    @pytest.fixture
    def config(self) -> ModelRuleDuplicateProtocolsConfig:
        """Create a test configuration."""
        return ModelRuleDuplicateProtocolsConfig(
            enabled=True,
            severity=EnumSeverity.ERROR,
            exclude_patterns=["tests/**", "examples/**", "deprecated/**"],
            protocol_suffix="Protocol",
        )

    @pytest.fixture
    def tmp_src_dir(self, tmp_path: Path) -> Path:
        """Create a temporary src directory."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        return src_dir

    def test_detects_duplicate_protocol(
        self,
        config: ModelRuleDuplicateProtocolsConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that duplicate protocols are detected."""
        # Create two files with the same protocol
        file1 = tmp_src_dir / "module_a.py"
        file1.write_text(
            """\
from typing import Protocol

class MyProtocol(Protocol):
    def method(self) -> None: ...
"""
        )

        file2 = tmp_src_dir / "module_b.py"
        file2.write_text(
            """\
from typing import Protocol

class MyProtocol(Protocol):
    def method(self) -> None: ...
"""
        )

        rule = RuleDuplicateProtocols(config)
        file_imports = {
            file1: ModelFileImports(file_path=file1),
            file2: ModelFileImports(file_path=file2),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        # Should detect 2 issues (one for each file)
        assert len(issues) == 2
        assert all(i.code == "DUPLICATE_PROTOCOL" for i in issues)
        assert all("MyProtocol" in i.message for i in issues)

    def test_no_issues_for_unique_protocols(
        self,
        config: ModelRuleDuplicateProtocolsConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that unique protocols don't cause issues."""
        file1 = tmp_src_dir / "module_a.py"
        file1.write_text(
            """\
from typing import Protocol

class ProtocolA(Protocol):
    def method(self) -> None: ...
"""
        )

        file2 = tmp_src_dir / "module_b.py"
        file2.write_text(
            """\
from typing import Protocol

class ProtocolB(Protocol):
    def method(self) -> None: ...
"""
        )

        rule = RuleDuplicateProtocols(config)
        file_imports = {
            file1: ModelFileImports(file_path=file1),
            file2: ModelFileImports(file_path=file2),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_excludes_test_files(
        self,
        config: ModelRuleDuplicateProtocolsConfig,
        tmp_path: Path,
    ) -> None:
        """Test that test files are excluded."""
        # Create a tests directory with duplicates
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        file1 = tests_dir / "test_a.py"
        file1.write_text("class TestProtocol: pass")

        file2 = tests_dir / "test_b.py"
        file2.write_text("class TestProtocol: pass")

        rule = RuleDuplicateProtocols(config)
        file_imports = {
            file1: ModelFileImports(file_path=file1),
            file2: ModelFileImports(file_path=file2),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        # Both files should be excluded
        assert len(issues) == 0

    def test_excludes_examples_files(
        self,
        config: ModelRuleDuplicateProtocolsConfig,
        tmp_path: Path,
    ) -> None:
        """Test that example files are excluded."""
        examples_dir = tmp_path / "examples"
        examples_dir.mkdir()

        file1 = examples_dir / "example_a.py"
        file1.write_text("class ExampleProtocol: pass")

        file2 = examples_dir / "example_b.py"
        file2.write_text("class ExampleProtocol: pass")

        rule = RuleDuplicateProtocols(config)
        file_imports = {
            file1: ModelFileImports(file_path=file1),
            file2: ModelFileImports(file_path=file2),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_disabled_rule_returns_no_issues(
        self,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that disabled rules don't report issues."""
        disabled_config = ModelRuleDuplicateProtocolsConfig(enabled=False)

        file1 = tmp_src_dir / "module_a.py"
        file1.write_text("class MyProtocol: pass")

        file2 = tmp_src_dir / "module_b.py"
        file2.write_text("class MyProtocol: pass")

        rule = RuleDuplicateProtocols(disabled_config)
        file_imports = {
            file1: ModelFileImports(file_path=file1),
            file2: ModelFileImports(file_path=file2),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_detects_protocol_by_suffix(
        self,
        config: ModelRuleDuplicateProtocolsConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that protocols are detected by name suffix."""
        file1 = tmp_src_dir / "module_a.py"
        file1.write_text("class EventHandlerProtocol: pass")

        file2 = tmp_src_dir / "module_b.py"
        file2.write_text("class EventHandlerProtocol: pass")

        rule = RuleDuplicateProtocols(config)
        file_imports = {
            file1: ModelFileImports(file_path=file1),
            file2: ModelFileImports(file_path=file2),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 2
        assert all("EventHandlerProtocol" in i.message for i in issues)

    def test_detects_protocol_by_inheritance(
        self,
        config: ModelRuleDuplicateProtocolsConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that protocols are detected by inheriting from Protocol."""
        file1 = tmp_src_dir / "module_a.py"
        file1.write_text(
            """\
from typing import Protocol

class Handler(Protocol):
    def handle(self) -> None: ...
"""
        )

        file2 = tmp_src_dir / "module_b.py"
        file2.write_text(
            """\
from typing import Protocol

class Handler(Protocol):
    def handle(self) -> None: ...
"""
        )

        rule = RuleDuplicateProtocols(config)
        file_imports = {
            file1: ModelFileImports(file_path=file1),
            file2: ModelFileImports(file_path=file2),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 2
        assert all("Handler" in i.message for i in issues)

    def test_issue_contains_fingerprint_and_symbol(
        self,
        config: ModelRuleDuplicateProtocolsConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that issues include fingerprint and symbol for baseline tracking."""
        file1 = tmp_src_dir / "module_a.py"
        file1.write_text("class MyProtocol: pass")

        file2 = tmp_src_dir / "module_b.py"
        file2.write_text("class MyProtocol: pass")

        rule = RuleDuplicateProtocols(config)
        file_imports = {
            file1: ModelFileImports(file_path=file1),
            file2: ModelFileImports(file_path=file2),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 2
        for issue in issues:
            assert issue.context is not None
            assert issue.context.get("symbol") == "MyProtocol"
            fingerprint = issue.context.get("fingerprint")
            assert fingerprint is not None
            assert len(fingerprint) == 16
            assert all(c in "0123456789abcdef" for c in fingerprint)

    def test_issue_contains_other_files(
        self,
        config: ModelRuleDuplicateProtocolsConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that issues include list of other files with the same protocol."""
        file1 = tmp_src_dir / "module_a.py"
        file1.write_text("class DuplicatedProtocol: pass")

        file2 = tmp_src_dir / "module_b.py"
        file2.write_text("class DuplicatedProtocol: pass")

        rule = RuleDuplicateProtocols(config)
        file_imports = {
            file1: ModelFileImports(file_path=file1),
            file2: ModelFileImports(file_path=file2),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 2
        for issue in issues:
            assert issue.context is not None
            assert "other_files" in issue.context
            # other_files is now a comma-separated string
            assert issue.context["other_files"] != ""

    def test_handles_syntax_errors(
        self,
        config: ModelRuleDuplicateProtocolsConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that syntax errors are handled gracefully."""
        file1 = tmp_src_dir / "good.py"
        file1.write_text("class MyProtocol: pass")

        file2 = tmp_src_dir / "bad.py"
        file2.write_text("class MyProtocol syntax error here")

        rule = RuleDuplicateProtocols(config)
        file_imports = {
            file1: ModelFileImports(file_path=file1),
            file2: ModelFileImports(file_path=file2, parse_error="Syntax error"),
        }

        # Should not raise, and should skip the bad file
        issues = rule.validate(file_imports, "test_repo", tmp_path)

        # Only the good file should be analyzed, no duplicates
        assert len(issues) == 0

    def test_handles_missing_files(
        self,
        config: ModelRuleDuplicateProtocolsConfig,
        tmp_path: Path,
    ) -> None:
        """Test that missing files are handled gracefully."""
        missing_file = tmp_path / "nonexistent.py"

        rule = RuleDuplicateProtocols(config)
        file_imports = {
            missing_file: ModelFileImports(file_path=missing_file),
        }

        # Should not raise
        issues = rule.validate(file_imports, "test_repo", tmp_path)
        assert len(issues) == 0

    def test_custom_protocol_suffix(
        self,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test custom protocol suffix configuration."""
        custom_config = ModelRuleDuplicateProtocolsConfig(
            enabled=True,
            severity=EnumSeverity.ERROR,
            protocol_suffix="Interface",
        )

        file1 = tmp_src_dir / "module_a.py"
        file1.write_text("class MyInterface: pass")

        file2 = tmp_src_dir / "module_b.py"
        file2.write_text("class MyInterface: pass")

        rule = RuleDuplicateProtocols(custom_config)
        file_imports = {
            file1: ModelFileImports(file_path=file1),
            file2: ModelFileImports(file_path=file2),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 2
        assert all("MyInterface" in i.message for i in issues)

    def test_issue_has_suggestion(
        self,
        config: ModelRuleDuplicateProtocolsConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that issues include suggestions."""
        file1 = tmp_src_dir / "module_a.py"
        file1.write_text("class MyProtocol: pass")

        file2 = tmp_src_dir / "module_b.py"
        file2.write_text("class MyProtocol: pass")

        rule = RuleDuplicateProtocols(config)
        file_imports = {
            file1: ModelFileImports(file_path=file1),
            file2: ModelFileImports(file_path=file2),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 2
        for issue in issues:
            assert issue.suggestion is not None
            assert "consolidat" in issue.suggestion.lower()

    def test_three_or_more_duplicates(
        self,
        config: ModelRuleDuplicateProtocolsConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test detection when protocol is duplicated in 3+ files."""
        file1 = tmp_src_dir / "module_a.py"
        file1.write_text("class SharedProtocol: pass")

        file2 = tmp_src_dir / "module_b.py"
        file2.write_text("class SharedProtocol: pass")

        file3 = tmp_src_dir / "module_c.py"
        file3.write_text("class SharedProtocol: pass")

        rule = RuleDuplicateProtocols(config)
        file_imports = {
            file1: ModelFileImports(file_path=file1),
            file2: ModelFileImports(file_path=file2),
            file3: ModelFileImports(file_path=file3),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 3
        for issue in issues:
            assert issue.context is not None
            # total_definitions is now a string
            assert issue.context["total_definitions"] == "3"
            # other_files is a comma-separated string with 2 files
            other_files = issue.context["other_files"].split(", ")
            assert len(other_files) == 2

    def test_detects_protocol_by_qualified_typing_import(
        self,
        config: ModelRuleDuplicateProtocolsConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that protocols are detected with qualified typing.Protocol import."""
        file1 = tmp_src_dir / "module_a.py"
        file1.write_text(
            """\
import typing

class Handler(typing.Protocol):
    def handle(self) -> None: ...
"""
        )

        file2 = tmp_src_dir / "module_b.py"
        file2.write_text(
            """\
import typing

class Handler(typing.Protocol):
    def handle(self) -> None: ...
"""
        )

        rule = RuleDuplicateProtocols(config)
        file_imports = {
            file1: ModelFileImports(file_path=file1),
            file2: ModelFileImports(file_path=file2),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 2
        assert all("Handler" in i.message for i in issues)

    def test_detects_protocol_by_qualified_typing_extensions_import(
        self,
        config: ModelRuleDuplicateProtocolsConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that protocols are detected with typing_extensions.Protocol import."""
        file1 = tmp_src_dir / "module_a.py"
        file1.write_text(
            """\
import typing_extensions

class Handler(typing_extensions.Protocol):
    def handle(self) -> None: ...
"""
        )

        file2 = tmp_src_dir / "module_b.py"
        file2.write_text(
            """\
import typing_extensions

class Handler(typing_extensions.Protocol):
    def handle(self) -> None: ...
"""
        )

        rule = RuleDuplicateProtocols(config)
        file_imports = {
            file1: ModelFileImports(file_path=file1),
            file2: ModelFileImports(file_path=file2),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 2
        assert all("Handler" in i.message for i in issues)

    def test_detects_protocol_mixed_import_styles(
        self,
        config: ModelRuleDuplicateProtocolsConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that protocols are detected with mixed import styles."""
        file1 = tmp_src_dir / "module_a.py"
        file1.write_text(
            """\
from typing import Protocol

class Handler(Protocol):
    def handle(self) -> None: ...
"""
        )

        file2 = tmp_src_dir / "module_b.py"
        file2.write_text(
            """\
import typing

class Handler(typing.Protocol):
    def handle(self) -> None: ...
"""
        )

        rule = RuleDuplicateProtocols(config)
        file_imports = {
            file1: ModelFileImports(file_path=file1),
            file2: ModelFileImports(file_path=file2),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 2
        assert all("Handler" in i.message for i in issues)

    def test_detects_subscripted_protocol(
        self,
        config: ModelRuleDuplicateProtocolsConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that subscripted Protocol[T] is detected."""
        file1 = tmp_src_dir / "module_a.py"
        file1.write_text(
            """\
from typing import Protocol, TypeVar

T = TypeVar("T")

class GenericHandler(Protocol[T]):
    def handle(self, item: T) -> T: ...
"""
        )

        file2 = tmp_src_dir / "module_b.py"
        file2.write_text(
            """\
from typing import Protocol, TypeVar

T = TypeVar("T")

class GenericHandler(Protocol[T]):
    def handle(self, item: T) -> T: ...
"""
        )

        rule = RuleDuplicateProtocols(config)
        file_imports = {
            file1: ModelFileImports(file_path=file1),
            file2: ModelFileImports(file_path=file2),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 2
        assert all("GenericHandler" in i.message for i in issues)

    def test_detects_qualified_subscripted_protocol(
        self,
        config: ModelRuleDuplicateProtocolsConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that qualified typing.Protocol[T] is detected."""
        file1 = tmp_src_dir / "module_a.py"
        file1.write_text(
            """\
import typing

T = typing.TypeVar("T")

class GenericHandler(typing.Protocol[T]):
    def handle(self, item: T) -> T: ...
"""
        )

        file2 = tmp_src_dir / "module_b.py"
        file2.write_text(
            """\
import typing

T = typing.TypeVar("T")

class GenericHandler(typing.Protocol[T]):
    def handle(self, item: T) -> T: ...
"""
        )

        rule = RuleDuplicateProtocols(config)
        file_imports = {
            file1: ModelFileImports(file_path=file1),
            file2: ModelFileImports(file_path=file2),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 2
        assert all("GenericHandler" in i.message for i in issues)

    def test_handles_file_not_under_root_directory(
        self,
        config: ModelRuleDuplicateProtocolsConfig,
        tmp_path: Path,
    ) -> None:
        """Test that files not under root_directory are handled gracefully.

        When a file path is not relative to root_directory, relative_to()
        would raise ValueError. The rule should handle this gracefully.
        """
        # Create two separate directories (file not under root)
        other_dir = tmp_path / "other"
        other_dir.mkdir()
        root_dir = tmp_path / "root"
        root_dir.mkdir()

        # Create duplicate protocols in the other directory (not under root)
        file1 = other_dir / "module_a.py"
        file1.write_text("class MyProtocol: pass")

        file2 = other_dir / "module_b.py"
        file2.write_text("class MyProtocol: pass")

        rule = RuleDuplicateProtocols(config)
        file_imports = {
            file1: ModelFileImports(file_path=file1),
            file2: ModelFileImports(file_path=file2),
        }

        # Should not raise ValueError, should still detect the duplicates
        issues = rule.validate(file_imports, "test_repo", root_dir)

        assert len(issues) == 2
        assert all("MyProtocol" in i.message for i in issues)
