#!/usr/bin/env python3
"""
Phase 2: Pattern 2 Automation - Complex Case Fixes using Python AST.

This script handles ~40-50% of remaining version field failures by:
1. Parsing Python files with AST
2. Finding model instantiations with existing parameters
3. Adding version=ModelSemVer(1, 0, 0) parameter safely
4. Preserving formatting and comments

Pattern:
  Before: ModelEventMappingRule(source_path="x", target_path="y")
  After:  ModelEventMappingRule(source_path="x", target_path="y", version=ModelSemVer(1, 0, 0))

Usage:
  python scripts/fix_version_field_pattern2.py [--dry-run] [-v|--verbose]

Safety:
  - Uses Python AST (no arbitrary code execution)
  - Run with --dry-run first to preview
  - Syntax checking before/after
  - Easily reversible with git
"""

import ast
import difflib
import re
import sys
from pathlib import Path
from typing import Optional

# Target models that need version field added
TARGET_MODELS = {
    "ModelActionConfigParameter",
    "ModelAggregationFunction",
    "ModelAggregationParameter",
    "ModelAggregationPerformance",
    "ModelAggregationSubcontract",
    "ModelBaseHeaderTransformation",
    "ModelCacheDistribution",
    "ModelCacheInvalidation",
    "ModelCacheKeyStrategy",
    "ModelCachePerformance",
    "ModelCachingSubcontract",
    "ModelCircuitBreakerSubcontract",
    "ModelComponentHealth",
    "ModelComponentHealthCollection",
    "ModelComponentHealthDetail",
    "ModelConfigurationSource",
    "ModelConfigurationSubcontract",
    "ModelConfigurationValidation",
    "ModelCoordinationResult",
    "ModelCoordinationRules",
    "ModelDataGrouping",
    "ModelDependencyHealth",
    "ModelDiscoverySubcontract",
    "ModelEnvironmentValidationRule",
    "ModelEnvironmentValidationRules",
    "ModelEventBusSubcontract",
    "ModelEventDefinition",
    "ModelEventHandlingSubcontract",
    "ModelEventMappingRule",
    "ModelEventPersistence",
    "ModelEventRouting",
    "ModelEventTransformation",
    "ModelEventTypeSubcontract",
    "ModelEventrouting",
    "ModelExecutionGraph",
    "ModelFSMOperation",
    "ModelFSMStateDefinition",
    "ModelFSMStateTransition",
    "ModelFSMSubcontract",
    "ModelFSMTransitionAction",
    "ModelFsmtransitionaction",
    "ModelHeaderTransformation",
    "ModelHealthCheckSubcontract",
    "ModelHealthCheckSubcontractResult",
    "ModelIntrospectionSubcontract",
    "ModelLifecycleSubcontract",
    "ModelLoadBalancing",
    "ModelLogLevelOverride",
    "ModelLoggingSubcontract",
    "ModelMetricsSubcontract",
    "ModelNodeAssignment",
    "ModelNodeHealthStatus",
    "ModelNodeProgress",
    "ModelObservabilitySubcontract",
    "ModelProgressStatus",
    "ModelQueryParameterRule",
    "ModelRequestTransformation",
    "ModelResourceUsageMetric",
    "ModelResponseHeaderRule",
    "ModelRetrySubcontract",
    "ModelRouteDefinition",
    "ModelRoutingMetrics",
    "ModelRoutingSubcontract",
    "ModelSecuritySubcontract",
    "ModelSerializationSubcontract",
    "ModelStateManagementSubcontract",
    "ModelStatePersistence",
    "ModelStateSynchronization",
    "ModelStateValidation",
    "ModelStateVersioning",
    "ModelStatisticalComputation",
    "ModelSynchronizationPoint",
    "ModelToolExecutionSubcontract",
    "ModelValidationSchemaRule",
    "ModelValidationSubcontract",
    "ModelWindowing Strategy",
    "ModelWorkflowCoordinationSubcontract",
    "ModelWorkflowDefinition",
    "ModelWorkflowDefinitionMetadata",
    "ModelWorkflowInstance",
    "ModelWorkflowNode",
}


class CallInfo:
    """Information about a Call node that needs fixing."""

    def __init__(
        self,
        func_name: str,
        lineno: int,
        col_offset: int,
        end_lineno: Optional[int] = None,
        end_col_offset: Optional[int] = None,
    ):
        self.func_name = func_name
        self.lineno = lineno
        self.col_offset = col_offset
        self.end_lineno = end_lineno or lineno
        self.end_col_offset = end_col_offset


class VersionFieldVisitor(ast.NodeVisitor):
    """AST visitor to find Call nodes that need version field."""

    def __init__(self, source: str, filename: str):
        self.source = source
        self.filename = filename
        self.lines = source.splitlines(keepends=True)
        self.calls_to_fix: list[CallInfo] = []

    def visit_Call(self, node: ast.Call) -> None:
        """Visit Call nodes and identify those needing version field."""
        func_name = self._get_func_name(node)

        if func_name in TARGET_MODELS:
            # Check if already has version kwarg
            has_version = any(kw.arg == "version" for kw in node.keywords)

            if not has_version and (node.args or node.keywords):
                # Only fix if has existing args/kwargs (Pattern 2)
                # Pattern 1 (empty calls) are handled by sed
                self.calls_to_fix.append(
                    CallInfo(
                        func_name,
                        node.lineno,
                        node.col_offset,
                        node.end_lineno,
                        node.end_col_offset,
                    )
                )

        self.generic_visit(node)

    def _get_func_name(self, node: ast.Call) -> Optional[str]:
        """Extract function name from Call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            # Handle chained calls like obj.ModelXxx()
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return parts[-1] if parts else None
        return None


def find_closing_paren(line: str, start_pos: int) -> int:
    """Find matching closing parenthesis, handling nested parens."""
    depth = 0
    in_string = False
    string_char = None
    escape = False

    for i in range(start_pos, len(line)):
        char = line[i]

        if escape:
            escape = False
            continue

        if char == "\\":
            escape = True
            continue

        if char in ('"', "'"):
            if not in_string:
                in_string = True
                string_char = char
            elif char == string_char:
                in_string = False
                string_char = None
            continue

        if not in_string:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    return i

    return -1


def fix_version_field_in_file(
    file_path: Path, dry_run: bool = False, verbose: bool = False
) -> tuple[bool, str, int]:
    """
    Fix version field in a single Python test file.

    Returns:
        Tuple of (was_modified, output_message, num_fixes)
    """
    try:
        source = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"ERROR: Could not read {file_path}: {e}", 0

    # Try to parse
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return False, f"SKIP: Syntax error in {file_path}: {e}", 0

    # Find all calls that need fixing
    visitor = VersionFieldVisitor(source, str(file_path))
    visitor.visit(tree)

    if not visitor.calls_to_fix:
        return False, f"OK: {file_path.name} - No changes needed", 0

    # Sort in reverse order to maintain line numbers when applying fixes
    visitor.calls_to_fix.sort(key=lambda x: (x.lineno, x.col_offset), reverse=True)

    # Apply fixes
    lines = source.splitlines(keepends=True)
    fixes_applied = 0

    for call in visitor.calls_to_fix:
        # Get line containing the opening paren
        line_idx = call.lineno - 1  # Convert to 0-indexed

        if line_idx >= len(lines):
            continue

        line = lines[line_idx]

        # Find the closing paren of this call
        # Start search from where the call begins
        search_start = call.col_offset
        close_paren_pos = find_closing_paren(line, search_start)

        if close_paren_pos == -1:
            # Multi-line call - search in subsequent lines
            for search_line_idx in range(line_idx, min(line_idx + 20, len(lines))):
                search_line = lines[search_line_idx]
                close_paren_pos = find_closing_paren(search_line, 0)
                if close_paren_pos != -1:
                    line_idx = search_line_idx
                    line = search_line
                    break

        if close_paren_pos == -1:
            # Could not find closing paren, skip
            if verbose:
                print(f"  WARNING: Could not find closing paren for {call.func_name}")
            continue

        # Check if there's content before the closing paren
        before_close = line[:close_paren_pos].strip()

        # Determine if we need a comma
        needs_comma = len(before_close) > 0 and not before_close.endswith("(")

        # Build the new version parameter
        if line_idx == call.lineno - 1:
            # Single-line call
            if needs_comma:
                new_content = (
                    line[:close_paren_pos]
                    + ", version=ModelSemVer(1, 0, 0)"
                    + line[close_paren_pos:]
                )
            else:
                new_content = (
                    line[:close_paren_pos]
                    + "version=ModelSemVer(1, 0, 0)"
                    + line[close_paren_pos:]
                )
            lines[line_idx] = new_content
        else:
            # Multi-line call
            # Add version on new line before closing paren
            indent = len(line) - len(line.lstrip())
            version_line = " " * indent + "version=ModelSemVer(1, 0, 0),\n"

            # Insert before the closing paren line
            if needs_comma:
                lines[line_idx] = (
                    line[:close_paren_pos]
                    + ",\n"
                    + version_line
                    + line[close_paren_pos:]
                )
            else:
                lines[line_idx] = (
                    line[:close_paren_pos]
                    + "\n"
                    + version_line
                    + line[close_paren_pos:]
                )

        fixes_applied += 1

    new_source = "".join(lines)

    # Verify syntax is still valid
    try:
        ast.parse(new_source)
    except SyntaxError as e:
        return (
            False,
            f"ERROR: Syntax error after fix in {file_path}: {e}\n"
            f"Changes NOT applied - manual fix required",
            0,
        )

    if new_source == source:
        return False, f"OK: {file_path.name} - No changes needed", 0

    # Generate diff for review
    diff = "".join(
        difflib.unified_diff(
            source.splitlines(keepends=True),
            new_source.splitlines(keepends=True),
            fromfile=f"a/{file_path.name}",
            tofile=f"b/{file_path.name}",
            lineterm="",
        )
    )

    if dry_run:
        output = f"DRY RUN: {file_path.name} ({fixes_applied} changes)\n"
        if verbose and diff:
            output += (
                "\nDiff:\n" + diff[:500] + ("...(truncated)" if len(diff) > 500 else "")
            )
        return False, output, fixes_applied

    # Apply changes
    file_path.write_text(new_source, encoding="utf-8")
    output = f"FIXED: {file_path.name} ({fixes_applied} calls updated)"
    if verbose and diff:
        output += "\nDiff (first 500 chars):\n" + diff[:500]

    return True, output, fixes_applied


def main():
    """Main entry point."""
    dry_run = "--dry-run" in sys.argv
    verbose = "-v" in sys.argv or "--verbose" in sys.argv

    # Find all test files in subcontracts directory
    test_dir = Path("tests/unit/models/contracts/subcontracts")
    if not test_dir.exists():
        print(f"ERROR: Test directory not found: {test_dir}")
        sys.exit(1)

    test_files = sorted(test_dir.glob("test_model_*.py"))

    print("=" * 80)
    print("Phase 2: Pattern 2 Automation (Complex Case Fixes)")
    print("=" * 80)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"Verbose: {verbose}")
    print(f"Test files: {len(test_files)}")
    print()

    modified_count = 0
    total_fixes = 0
    skipped_count = 0

    for test_file in test_files:
        was_modified, output, num_fixes = fix_version_field_in_file(
            test_file, dry_run=dry_run, verbose=verbose
        )

        if was_modified:
            print(f"✓ {output}")
            modified_count += 1
            total_fixes += num_fixes
        elif "SKIP:" in output or "ERROR:" in output:
            print(f"⚠ {output}")
            skipped_count += 1
        elif verbose or "FIXED:" in output or "DRY RUN:" in output:
            print(f"  {output}")

    print()
    print("=" * 80)
    print("Phase 2 Summary")
    print("=" * 80)
    print(f"Files modified: {modified_count}")
    print(f"Total fixes applied: {total_fixes}")
    print(f"Files skipped: {skipped_count}")
    print()

    if dry_run:
        print("DRY RUN MODE: No files were actually modified")
        print("To apply changes, run: python scripts/fix_version_field_pattern2.py")
        print()

    print("Next Steps:")
    print("1. Review changes (if any)")
    print(
        "2. Run tests: poetry run pytest tests/unit/models/contracts/subcontracts/ -x"
    )
    print(
        "3. If issues, rollback: git checkout tests/unit/models/contracts/subcontracts/"
    )
    print("4. Proceed to Phase 3: Manual fixes for remaining failures")
    print()


if __name__ == "__main__":
    main()
