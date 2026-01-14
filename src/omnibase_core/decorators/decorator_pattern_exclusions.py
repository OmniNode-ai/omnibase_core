"""
ONEX Pattern Exclusion Decorators.
Provides fine-grained control over ONEX strict typing standards enforcement.
"""

from collections.abc import Callable
from typing import Any

from omnibase_core.models.decorators.model_pattern_exclusion_info import (
    ModelPatternExclusionInfo,
)

# Self-exclusion: This module contains example code and infrastructure
# ONEX_EXCLUDE: dict_str_any - Example code in docstrings and function signatures
# ONEX_EXCLUDE: any_type - Example code and infrastructure utilities


class ONEXPatternExclusion:
    """Marks functions/classes as excluded from specific ONEX pattern enforcement."""

    def __init__(
        self,
        excluded_patterns: set[str],
        reason: str,
        scope: str = "function",
        reviewer: str | None = None,
    ):
        """
        Initialize pattern exclusion decorator.

        Args:
            excluded_patterns: Set of patterns to exclude (e.g., {'dict_str_any', 'any_type'})
            reason: Justification for the exclusion
            scope: Scope of exclusion ('function', 'class', 'method')
            reviewer: Optional code reviewer who approved the exclusion
        """
        self.excluded_patterns = excluded_patterns
        self.reason = reason
        self.scope = scope
        self.reviewer = reviewer

    def __call__(self, target: Callable[..., Any] | type) -> Callable[..., Any] | type:
        """Apply the exclusion to the target function or class."""
        # NOTE(OMN-1302): Dynamic attributes for exclusion metadata on decoratee.
        # Safe because attributes read via hasattr/getattr at runtime.
        if not hasattr(target, "_onex_pattern_exclusions"):
            target._onex_pattern_exclusions = set()  # type: ignore[attr-defined]

        existing_exclusions: set[str] = getattr(
            target, "_onex_pattern_exclusions", set()
        )
        existing_exclusions.update(self.excluded_patterns)
        target._onex_pattern_exclusions = existing_exclusions  # type: ignore[union-attr]
        target._onex_exclusion_reason = self.reason  # type: ignore[union-attr]
        target._onex_exclusion_scope = self.scope  # type: ignore[union-attr]
        target._onex_exclusion_reviewer = self.reviewer  # type: ignore[union-attr]

        return target


def allow_any_type(reason: str, reviewer: str | None = None) -> ONEXPatternExclusion:
    """
    Allow usage of Any type annotation.

    Args:
        reason: Justification for allowing Any usage
        reviewer: Optional code reviewer who approved this

    Example:
        @allow_any_type("Runtime data with unknown structure from external API")
        def process_external_data(self, data: Any) -> ProcessingResult:
            ...
    """
    return ONEXPatternExclusion(
        excluded_patterns={"any_type"},
        reason=reason,
        reviewer=reviewer,
    )


def allow_mixed_types(reason: str, reviewer: str | None = None) -> ONEXPatternExclusion:
    """
    Allow usage of both Any and Dict[str, Any] patterns.

    Args:
        reason: Justification for allowing mixed type patterns
        reviewer: Optional code reviewer who approved this

    Example:
        @allow_mixed_types("Modern interface standards layer")
        def legacy_adapter(self, data: Any) -> Dict[str, Any]:
            ...
    """
    return ONEXPatternExclusion(
        excluded_patterns={"any_type", "dict_str_any"},
        reason=reason,
        reviewer=reviewer,
    )


def allow_legacy_pattern(
    pattern: str, reason: str, reviewer: str | None = None
) -> ONEXPatternExclusion:
    """
    Allow specific legacy pattern that doesn't conform to ONEX standards.

    Args:
        pattern: Specific pattern to allow (e.g., 'logging_call', 'string_literal')
        reason: Justification for allowing the legacy pattern
        reviewer: Optional code reviewer who approved this

    Example:
        @allow_legacy_pattern("print_statement", "Development debugging only")
        def debug_helper(self, message: str):
            print(f"DEBUG: {message}")  # Normally forbidden
    """
    return ONEXPatternExclusion(
        excluded_patterns={pattern},
        reason=reason,
        reviewer=reviewer,
    )


def exclude_from_onex_standards(
    *patterns: str,
    reason: str,
    reviewer: str | None = None,
) -> ONEXPatternExclusion:
    """
    Generic exclusion decorator for multiple ONEX standard patterns.

    Args:
        patterns: Variable number of pattern names to exclude
        reason: Justification for the exclusions
        reviewer: Optional code reviewer who approved this

    Example:
        @exclude_from_onex_standards(
            'dict_str_any', 'any_type', 'dynamic_import',
            reason="Plugin system requires dynamic type handling",
            reviewer="senior_architect"
        )
        def dynamic_plugin_loader(self, plugin_config: Any) -> Dict[str, Any]:
            ...
    """
    return ONEXPatternExclusion(
        excluded_patterns=set(patterns),
        reason=reason,
        reviewer=reviewer,
    )


# Utility functions for pre-commit hooks to check exclusions


def has_pattern_exclusion(obj: Any, pattern: str) -> bool:
    """
    Check if an object has exclusion for a specific pattern.

    Args:
        obj: Function, method, or class to check
        pattern: Pattern name to check for exclusion

    Returns:
        True if the pattern is excluded for this object
    """
    if not hasattr(obj, "_onex_pattern_exclusions"):
        return False
    exclusions: set[str] = getattr(obj, "_onex_pattern_exclusions", set())
    return pattern in exclusions


def get_exclusion_info(obj: Any) -> ModelPatternExclusionInfo | None:
    """
    Get exclusion information for an object.

    Args:
        obj: Function, method, or class to check

    Returns:
        ModelPatternExclusionInfo with exclusion info or None if no exclusions
    """
    if not hasattr(obj, "_onex_pattern_exclusions"):
        return None

    return ModelPatternExclusionInfo(
        excluded_patterns=getattr(obj, "_onex_pattern_exclusions", set()),
        reason=getattr(obj, "_onex_exclusion_reason", "No reason provided"),
        scope=getattr(obj, "_onex_exclusion_scope", "function"),
        reviewer=getattr(obj, "_onex_exclusion_reviewer", None),
    )


def is_excluded_from_pattern_check(
    file_path: str,
    line_number: int,
    pattern: str,
) -> bool:
    """
    Check if a specific line in a file is excluded from pattern checking.
    This function can be enhanced to parse AST and check decorator exclusions.

    Args:
        file_path: Path to the Python file
        line_number: Line number to check
        pattern: Pattern name to check

    Returns:
        True if the line should be excluded from pattern checking
    """
    # For now, this is a placeholder that can be enhanced with AST parsing
    # to check if the line is within a function/class that has exclusion decorators

    try:
        with open(file_path, encoding="utf-8") as f:
            lines = f.readlines()

        # Look backwards from the current line to find decorator exclusions
        for i in range(max(0, line_number - 20), line_number):
            line = lines[i].strip()

            # Check for exclusion decorators
            if f"@allow_{pattern}" in line or "@exclude_from_onex_standards" in line:
                return True

            # Check for inline exclusion comments
            if f"# ONEX_EXCLUDE: {pattern}" in line or "# ONEX_EXCLUDE_ALL" in line:
                return True

        return False

    except (FileNotFoundError, IndexError, UnicodeDecodeError):
        return False
