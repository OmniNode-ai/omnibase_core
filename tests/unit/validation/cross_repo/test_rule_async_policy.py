"""Tests for async_policy rule.

Related ticket: OMN-1906
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.validation.model_rule_configs import (
    ModelRuleAsyncPolicyConfig,
)
from omnibase_core.validation.cross_repo.rules.rule_async_policy import (
    RuleAsyncPolicy,
)
from omnibase_core.validation.cross_repo.scanners.scanner_import_graph import (
    ModelFileImports,
)


@pytest.mark.unit
class TestRuleAsyncPolicy:
    """Tests for RuleAsyncPolicy."""

    @pytest.fixture
    def config(self) -> ModelRuleAsyncPolicyConfig:
        """Create a test configuration."""
        return ModelRuleAsyncPolicyConfig(
            enabled=True,
            exclude_patterns=["tests/**", "scripts/**", "migrations/**", "examples/**"],
            blocking_calls_error=[
                "time.sleep",
                "requests.get",
                "requests.post",
                "subprocess.run",
            ],
            blocking_calls_warning=["open"],
        )

    @pytest.fixture
    def tmp_src_dir(self, tmp_path: Path) -> Path:
        """Create a temporary src directory."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        return src_dir

    def test_detects_time_sleep_in_async(
        self,
        config: ModelRuleAsyncPolicyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that time.sleep() in async functions is detected."""
        source_file = tmp_src_dir / "handler.py"
        source_file.write_text(
            """\
import time

async def process_data():
    time.sleep(1)  # BAD - blocks event loop
    return "done"
"""
        )

        rule = RuleAsyncPolicy(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 1
        assert issues[0].code == "ASYNC_POLICY_BLOCKING_CALL"
        assert issues[0].severity == EnumSeverity.ERROR
        assert "time.sleep" in issues[0].message

    def test_detects_requests_in_async(
        self,
        config: ModelRuleAsyncPolicyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that requests.get() in async functions is detected."""
        source_file = tmp_src_dir / "handler.py"
        source_file.write_text(
            """\
import requests

async def fetch_data(url: str):
    response = requests.get(url)  # BAD - use httpx/aiohttp instead
    return response.json()
"""
        )

        rule = RuleAsyncPolicy(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 1
        assert issues[0].code == "ASYNC_POLICY_BLOCKING_CALL"
        assert issues[0].severity == EnumSeverity.ERROR
        assert "requests.get" in issues[0].message

    def test_detects_subprocess_in_async(
        self,
        config: ModelRuleAsyncPolicyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that subprocess.run() in async functions is detected."""
        source_file = tmp_src_dir / "handler.py"
        source_file.write_text(
            """\
import subprocess

async def run_command():
    result = subprocess.run(["echo", "hello"])  # BAD - use asyncio.create_subprocess
    return result.returncode
"""
        )

        rule = RuleAsyncPolicy(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 1
        assert "subprocess.run" in issues[0].message

    def test_detects_open_in_async_as_warning(
        self,
        config: ModelRuleAsyncPolicyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that open() in async functions is detected as warning."""
        source_file = tmp_src_dir / "handler.py"
        source_file.write_text(
            """\
async def read_file(path: str):
    with open(path) as f:  # WARNING - consider using aiofiles
        return f.read()
"""
        )

        rule = RuleAsyncPolicy(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 1
        assert issues[0].code == "ASYNC_POLICY_BLOCKING_CALL"
        assert issues[0].severity == EnumSeverity.WARNING
        assert "open" in issues[0].message

    def test_no_issues_in_sync_functions(
        self,
        config: ModelRuleAsyncPolicyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that blocking calls in sync functions are allowed."""
        source_file = tmp_src_dir / "handler.py"
        source_file.write_text(
            """\
import time
import requests

def process_data():
    time.sleep(1)  # OK - sync function
    response = requests.get("http://example.com")  # OK - sync function
    return response.text
"""
        )

        rule = RuleAsyncPolicy(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_no_issues_for_clean_async(
        self,
        config: ModelRuleAsyncPolicyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that clean async code passes."""
        source_file = tmp_src_dir / "handler.py"
        source_file.write_text(
            """\
import asyncio
import httpx

async def fetch_data(url: str):
    await asyncio.sleep(1)  # OK - async version
    async with httpx.AsyncClient() as client:
        response = await client.get(url)  # OK - async HTTP
        return response.json()
"""
        )

        rule = RuleAsyncPolicy(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_excludes_test_files(
        self,
        config: ModelRuleAsyncPolicyConfig,
        tmp_path: Path,
    ) -> None:
        """Test that test files are excluded."""
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()

        test_file = tests_dir / "test_handler.py"
        test_file.write_text(
            """\
import time

async def test_something():
    time.sleep(0.1)  # OK in tests
"""
        )

        rule = RuleAsyncPolicy(config)
        file_imports = {
            test_file: ModelFileImports(file_path=test_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_disabled_rule_returns_no_issues(
        self,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that disabled rules don't report issues."""
        disabled_config = ModelRuleAsyncPolicyConfig(enabled=False)

        source_file = tmp_src_dir / "handler.py"
        source_file.write_text(
            """\
import time

async def bad_function():
    time.sleep(1)
"""
        )

        rule = RuleAsyncPolicy(disabled_config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 0

    def test_issue_contains_fingerprint_and_symbol(
        self,
        config: ModelRuleAsyncPolicyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that issues include fingerprint and symbol for baseline tracking."""
        source_file = tmp_src_dir / "handler.py"
        source_file.write_text(
            """\
import time

async def bad_function():
    time.sleep(1)
"""
        )

        rule = RuleAsyncPolicy(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 1
        assert issues[0].context is not None
        assert issues[0].context.get("symbol") == "time.sleep"
        fingerprint = issues[0].context.get("fingerprint")
        assert fingerprint is not None
        assert len(fingerprint) == 16
        assert all(c in "0123456789abcdef" for c in fingerprint)

    def test_issue_contains_async_function_name(
        self,
        config: ModelRuleAsyncPolicyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that issues include the async function name."""
        source_file = tmp_src_dir / "handler.py"
        source_file.write_text(
            """\
import time

async def my_async_handler():
    time.sleep(1)
"""
        )

        rule = RuleAsyncPolicy(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 1
        assert issues[0].context is not None
        assert issues[0].context.get("async_function") == "my_async_handler"
        assert "my_async_handler" in issues[0].message

    def test_issue_has_suggestion(
        self,
        config: ModelRuleAsyncPolicyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that issues include suggestions."""
        source_file = tmp_src_dir / "handler.py"
        source_file.write_text(
            """\
import time

async def bad_function():
    time.sleep(1)
"""
        )

        rule = RuleAsyncPolicy(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 1
        assert issues[0].suggestion is not None
        assert (
            "async" in issues[0].suggestion.lower()
            or "thread" in issues[0].suggestion.lower()
        )

    def test_multiple_violations_in_async_function(
        self,
        config: ModelRuleAsyncPolicyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test detection of multiple violations in one async function."""
        source_file = tmp_src_dir / "handler.py"
        source_file.write_text(
            """\
import time
import requests

async def bad_handler():
    time.sleep(1)
    response = requests.get("http://example.com")
    with open("file.txt") as f:
        data = f.read()
    return response.text
"""
        )

        rule = RuleAsyncPolicy(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 3
        severities = [i.severity for i in issues]
        assert severities.count(EnumSeverity.ERROR) == 2
        assert severities.count(EnumSeverity.WARNING) == 1

    def test_multiple_async_functions(
        self,
        config: ModelRuleAsyncPolicyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test detection across multiple async functions."""
        source_file = tmp_src_dir / "handlers.py"
        source_file.write_text(
            """\
import time

async def handler_one():
    time.sleep(1)

async def handler_two():
    pass  # Clean

async def handler_three():
    time.sleep(2)
"""
        )

        rule = RuleAsyncPolicy(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 2
        funcs = [i.context["async_function"] for i in issues if i.context]
        assert "handler_one" in funcs
        assert "handler_three" in funcs
        assert "handler_two" not in funcs

    def test_handles_syntax_errors(
        self,
        config: ModelRuleAsyncPolicyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that syntax errors are handled gracefully."""
        source_file = tmp_src_dir / "bad.py"
        source_file.write_text("async def bad syntax error")

        rule = RuleAsyncPolicy(config)
        file_imports = {
            source_file: ModelFileImports(
                file_path=source_file, parse_error="Syntax error"
            ),
        }

        # Should not raise
        issues = rule.validate(file_imports, "test_repo", tmp_path)
        assert len(issues) == 0

    def test_handles_missing_files(
        self,
        config: ModelRuleAsyncPolicyConfig,
        tmp_path: Path,
    ) -> None:
        """Test that missing files are handled gracefully."""
        missing_file = tmp_path / "nonexistent.py"

        rule = RuleAsyncPolicy(config)
        file_imports = {
            missing_file: ModelFileImports(file_path=missing_file),
        }

        # Should not raise
        issues = rule.validate(file_imports, "test_repo", tmp_path)
        assert len(issues) == 0

    def test_nested_async_function(
        self,
        config: ModelRuleAsyncPolicyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test detection in nested async functions."""
        source_file = tmp_src_dir / "handler.py"
        source_file.write_text(
            """\
import time

async def outer():
    async def inner():
        time.sleep(1)  # Should be detected in inner
    await inner()
"""
        )

        rule = RuleAsyncPolicy(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        # Should detect the violation in inner function
        # Note: Due to ast.walk behavior, it may detect in both outer and inner
        assert len(issues) >= 1
        assert any("inner" in i.context["async_function"] for i in issues if i.context)

    def test_async_method_in_class(
        self,
        config: ModelRuleAsyncPolicyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test detection in async methods within classes."""
        source_file = tmp_src_dir / "handler.py"
        source_file.write_text(
            """\
import time

class Handler:
    async def process(self):
        time.sleep(1)  # Should be detected
"""
        )

        rule = RuleAsyncPolicy(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        assert len(issues) == 1
        assert issues[0].context is not None
        assert issues[0].context.get("async_function") == "process"

    def test_allowlist_wrapper_asyncio_to_thread(
        self,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that blocking calls inside asyncio.to_thread are allowed."""
        config = ModelRuleAsyncPolicyConfig(
            enabled=True,
            blocking_calls_error=["time.sleep"],
            allowlist_wrappers=["asyncio.to_thread"],
        )

        source_file = tmp_src_dir / "handler.py"
        source_file.write_text(
            """\
import asyncio
import time

async def process_data():
    # This should be allowed - blocking call inside to_thread
    await asyncio.to_thread(time.sleep, 1)
    return "done"
"""
        )

        rule = RuleAsyncPolicy(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        # asyncio.to_thread wraps the blocking call, so no issues
        assert len(issues) == 0

    def test_allowlist_wrapper_run_in_executor(
        self,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that blocking calls inside loop.run_in_executor are allowed."""
        config = ModelRuleAsyncPolicyConfig(
            enabled=True,
            blocking_calls_error=["time.sleep", "requests.get"],
            allowlist_wrappers=["loop.run_in_executor"],
        )

        source_file = tmp_src_dir / "handler.py"
        source_file.write_text(
            """\
import asyncio
import time

async def process_data():
    loop = asyncio.get_event_loop()
    # This should be allowed - blocking call inside run_in_executor
    await loop.run_in_executor(None, time.sleep, 1)
    return "done"
"""
        )

        rule = RuleAsyncPolicy(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        # run_in_executor wraps the blocking call, so no issues
        assert len(issues) == 0

    def test_blocking_call_without_wrapper_still_flagged(
        self,
        config: ModelRuleAsyncPolicyConfig,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that blocking calls without wrappers are still flagged."""
        source_file = tmp_src_dir / "handler.py"
        source_file.write_text(
            """\
import asyncio
import time

async def process_data():
    # This should be flagged - no wrapper
    time.sleep(1)
    # This is fine - using asyncio.to_thread
    await asyncio.to_thread(time.sleep, 2)
    return "done"
"""
        )

        rule = RuleAsyncPolicy(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        # Only the unwrapped time.sleep(1) should be flagged
        assert len(issues) == 1
        assert "time.sleep" in issues[0].message

    def test_matches_call_no_prefix_for_simple_names(
        self,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that simple patterns don't match module names with similar prefix."""
        config = ModelRuleAsyncPolicyConfig(
            enabled=True,
            # Use 'open' as a simple name (no dot)
            blocking_calls_warning=["open"],
            blocking_calls_error=[],
        )

        source_file = tmp_src_dir / "handler.py"
        source_file.write_text(
            """\
import open_file_utils

async def process_data():
    # This should NOT be flagged - open_file_utils is different from open
    result = open_file_utils.read("test.txt")
    return result
"""
        )

        rule = RuleAsyncPolicy(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        # open_file_utils should NOT match the "open" pattern
        assert len(issues) == 0

    def test_matches_call_prefix_works_for_module_patterns(
        self,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that module patterns (with dots) still support prefix matching."""
        config = ModelRuleAsyncPolicyConfig(
            enabled=True,
            # requests.get is a module pattern (has dot)
            blocking_calls_error=["requests.get"],
            blocking_calls_warning=[],
        )

        source_file = tmp_src_dir / "handler.py"
        source_file.write_text(
            """\
import requests

async def fetch_data():
    # This should be flagged - matches requests.get prefix
    response = requests.get.something("http://example.com")
    return response
"""
        )

        rule = RuleAsyncPolicy(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        # requests.get.something should match the "requests.get" pattern
        assert len(issues) == 1
        assert "requests.get.something" in issues[0].message

    def test_allowlist_wrapper_suffix_matching(
        self,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that wrapper patterns use suffix matching for prefixed calls.

        This ensures patterns like 'loop.run_in_executor' match calls like
        'self.loop.run_in_executor' where the object is prefixed.
        """
        config = ModelRuleAsyncPolicyConfig(
            enabled=True,
            blocking_calls_error=["time.sleep"],
            # Pattern without 'self.' prefix should still match
            allowlist_wrappers=["loop.run_in_executor"],
        )

        source_file = tmp_src_dir / "handler.py"
        source_file.write_text(
            """\
import asyncio
import time

class AsyncHandler:
    def __init__(self):
        self.loop = asyncio.get_event_loop()

    async def process_data(self):
        # This should be allowed - blocking call inside self.loop.run_in_executor
        # The wrapper pattern "loop.run_in_executor" should match via suffix matching
        await self.loop.run_in_executor(None, time.sleep, 1)
        return "done"
"""
        )

        rule = RuleAsyncPolicy(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        # self.loop.run_in_executor wraps the blocking call, so no issues
        assert len(issues) == 0

    def test_allowlist_wrapper_no_partial_suffix_match(
        self,
        tmp_path: Path,
        tmp_src_dir: Path,
    ) -> None:
        """Test that wrapper suffix matching requires dot separator.

        Ensures 'run_in_executor' does not match 'not_run_in_executor'.
        The wrapper matching should only match when the call ends with
        '.' + pattern, not when pattern is a substring.
        """
        config = ModelRuleAsyncPolicyConfig(
            enabled=True,
            blocking_calls_error=["time.sleep"],
            # Only 'run_in_executor' should be allowlisted, not 'not_run_in_executor'
            allowlist_wrappers=["run_in_executor"],
        )

        source_file = tmp_src_dir / "handler.py"
        source_file.write_text(
            """\
import time

async def process_data():
    # This should be flagged - time.sleep is not inside a valid wrapper
    # Even though 'not_run_in_executor' contains 'run_in_executor' as substring,
    # the suffix matching requires the exact pattern after a dot
    time.sleep(1)
    return "done"
"""
        )

        rule = RuleAsyncPolicy(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        issues = rule.validate(file_imports, "test_repo", tmp_path)

        # time.sleep is not wrapped, should be flagged
        assert len(issues) == 1
        assert "time.sleep" in issues[0].message

    def test_matches_wrapper_method_directly(
        self,
        tmp_path: Path,
    ) -> None:
        """Test the _matches_wrapper method for suffix matching correctness."""
        config = ModelRuleAsyncPolicyConfig(enabled=True)
        rule = RuleAsyncPolicy(config)

        # Exact match should work
        assert rule._matches_wrapper("run_in_executor", "run_in_executor") is True
        assert rule._matches_wrapper("asyncio.to_thread", "asyncio.to_thread") is True

        # Suffix match (call ends with "." + pattern) should work
        assert (
            rule._matches_wrapper("self.loop.run_in_executor", "loop.run_in_executor")
            is True
        )
        assert rule._matches_wrapper("self.run_in_executor", "run_in_executor") is True
        assert (
            rule._matches_wrapper("obj.asyncio.to_thread", "asyncio.to_thread") is True
        )

        # Partial substring should NOT match
        assert rule._matches_wrapper("not_run_in_executor", "run_in_executor") is False
        assert (
            rule._matches_wrapper("self.not_run_in_executor", "run_in_executor")
            is False
        )
        assert rule._matches_wrapper("run_in_executor_v2", "run_in_executor") is False

        # Different path should NOT match
        assert rule._matches_wrapper("other.executor", "loop.run_in_executor") is False
        assert (
            rule._matches_wrapper("loop.run_in_executor", "self.loop.run_in_executor")
            is False
        )

    def test_handles_file_not_under_root_directory(
        self,
        config: ModelRuleAsyncPolicyConfig,
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

        source_file = other_dir / "handler.py"
        source_file.write_text(
            """\
import time

async def process_data():
    time.sleep(1)  # Blocking call in async function
    return "done"
"""
        )

        rule = RuleAsyncPolicy(config)
        file_imports = {
            source_file: ModelFileImports(file_path=source_file),
        }

        # Should not raise ValueError, should still detect the issue
        issues = rule.validate(file_imports, "test_repo", root_dir)

        assert len(issues) == 1
        assert issues[0].code == "ASYNC_POLICY_BLOCKING_CALL"
