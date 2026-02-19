# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI for cross-repo conformance validation.

Usage:
    python -m omnibase_core.validation.cross_repo --policy policy.yaml [directory]
    python -m omnibase_core.validation.cross_repo --policy policy.yaml --format json
    python -m omnibase_core.validation.cross_repo --policy policy.yaml --baseline-write baseline.yaml
    python -m omnibase_core.validation.cross_repo --policy policy.yaml --baseline-enforce baseline.yaml

Related ticket: OMN-1771
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.validation.model_violation_baseline import (
    ModelBaselineGenerator,
    ModelBaselineViolation,
    ModelViolationBaseline,
)
from omnibase_core.validation.cross_repo.baseline_io import (
    read_baseline,
    write_baseline,
)
from omnibase_core.validation.cross_repo.engine import (
    CrossRepoValidationEngine,
    run_cross_repo_validation,
)
from omnibase_core.validation.cross_repo.policy_loader import load_policy
from omnibase_core.validation.cross_repo.util_fingerprint import generate_fingerprint

# Tool version for baseline generator metadata
CROSS_REPO_VALIDATOR_VERSION = "0.5.0"


def _make_relative_path(file_path: Path | None, base_directory: Path) -> str:
    """Convert file path to relative string, falling back to absolute if not under base.

    Args:
        file_path: The file path to normalize, or None.
        base_directory: The base directory for relative path computation.

    Returns:
        Relative path string, absolute path string, or empty string if file_path is None.
    """
    if file_path is None:
        return ""
    try:
        return str(file_path.relative_to(base_directory))
    except ValueError:
        return str(file_path)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Cross-repo conformance validation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Validate current directory with a policy file
    python -m omnibase_core.validation.cross_repo --policy onex_validation_policy.yaml

    # Validate specific directory with JSON output
    python -m omnibase_core.validation.cross_repo --policy policy.yaml --format json src/

    # Run only specific rules
    python -m omnibase_core.validation.cross_repo --policy policy.yaml --rules repo_boundaries

    # Write violations to a baseline file for incremental adoption
    python -m omnibase_core.validation.cross_repo --policy policy.yaml --baseline-write baseline.yaml

    # Enforce against baseline (suppressed violations don't fail)
    python -m omnibase_core.validation.cross_repo --policy policy.yaml --baseline-enforce baseline.yaml

Exit Codes:
    0 - Validation passed (no unsuppressed violations)
    1 - Validation failed (unsuppressed violations found)
    2 - Configuration error (policy not found, invalid YAML, baseline not found, etc.)
        """,
    )

    parser.add_argument(
        "--policy",
        type=Path,
        required=True,
        help="Path to the validation policy YAML file",
    )

    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    parser.add_argument(
        "--rules",
        nargs="*",
        help="Specific rule IDs to run (default: all enabled)",
    )

    # Baseline options - mutually exclusive
    baseline_group = parser.add_mutually_exclusive_group()

    baseline_group.add_argument(
        "--baseline-write",
        type=Path,
        metavar="PATH",
        help="Write violations to a baseline file (YAML format)",
    )

    baseline_group.add_argument(
        "--baseline-enforce",
        type=Path,
        metavar="PATH",
        help="Enforce against a baseline file. Baselined violations are suppressed (INFO severity), new violations fail.",
    )

    parser.add_argument(
        "directory",
        type=Path,
        nargs="?",
        default=Path.cwd(),
        help="Directory to validate (default: current directory)",
    )

    return parser


def build_baseline_from_result(
    result: ModelValidationResult[None],
    policy_id: str,  # string-id-ok: human-readable policy identifier
    directory: Path,
) -> ModelViolationBaseline:
    """Convert validation result to a baseline.

    Args:
        result: The validation result containing issues.
        policy_id: The policy ID for the baseline.
        directory: Root directory being validated (for relative paths).

    Returns:
        A ModelViolationBaseline containing all violations.
    """
    violations: list[ModelBaselineViolation] = []
    now = datetime.now(UTC)

    for issue in result.issues:
        # Extract fingerprint from context if available, otherwise generate it
        fingerprint = None
        symbol = ""

        if issue.context:
            fingerprint = issue.context.get("fingerprint")
            symbol = issue.context.get("symbol", "")
            if not symbol:
                symbol = issue.context.get("import", "")

        # Generate fingerprint if not in context
        if not fingerprint and issue.file_path:
            file_path_str = _make_relative_path(issue.file_path, directory)
            rule_id = issue.rule_name or "unknown"
            fingerprint = generate_fingerprint(rule_id, file_path_str, symbol)

        if fingerprint:
            # Compute relative file path for baseline
            file_path_str = _make_relative_path(issue.file_path, directory)

            violations.append(
                ModelBaselineViolation(
                    fingerprint=fingerprint,
                    rule_id=issue.rule_name or "unknown",
                    file_path=file_path_str,
                    symbol=symbol,
                    message=issue.message,
                    first_seen=now,
                )
            )

    return ModelViolationBaseline(
        schema_version="1.0",
        created_at=now,
        policy_id=policy_id,
        generator=ModelBaselineGenerator(
            tool="cross-repo-validator",
            version=CROSS_REPO_VALIDATOR_VERSION,
        ),
        violations=violations,
    )


# Module-level alias to engine's static method (single implementation)
_is_suppressed = CrossRepoValidationEngine._is_suppressed


def print_text_report(
    result: ModelValidationResult[None],
    policy_id: str,  # string-id-ok: human-readable policy identifier
) -> None:
    """Print a human-readable validation report."""
    print(f"\n{'=' * 60}")
    print("Cross-Repo Validation Report")
    print(f"Policy: {policy_id}")
    print(f"{'=' * 60}\n")

    if result.is_valid:
        print("[PASS] Validation PASSED\n")
    else:
        print("[FAIL] Validation FAILED\n")

    # Group issues by severity
    by_severity: dict[EnumSeverity, list] = {}  # type: ignore[type-arg]
    for issue in result.issues:
        by_severity.setdefault(issue.severity, []).append(issue)

    # Print issues by severity (most severe first)
    severity_order = [
        EnumSeverity.FATAL,
        EnumSeverity.CRITICAL,
        EnumSeverity.ERROR,
        EnumSeverity.WARNING,
        EnumSeverity.INFO,
    ]

    for severity in severity_order:
        issues = by_severity.get(severity, [])
        if not issues:
            continue

        print(f"\n{severity.value.upper()} ({len(issues)}):")
        print("-" * 40)

        for issue in issues:
            location = ""
            if issue.file_path:
                location = str(issue.file_path)
                if issue.line_number:
                    location += f":{issue.line_number}"

            # Mark suppressed issues
            suppressed_marker = "[SUPPRESSED] " if _is_suppressed(issue) else ""

            print(f"  {suppressed_marker}[{issue.code or 'UNKNOWN'}] {location}")
            print(f"    {issue.message}")
            if issue.suggestion:
                print(f"    Suggestion: {issue.suggestion}")
            print()

    # Counts by severity and rule
    counts_by_severity: dict[str, int] = {}
    counts_by_rule: dict[str, int] = {}
    suppressed_count = 0
    unsuppressed_count = 0

    for issue in result.issues:
        sev_key = issue.severity.value
        counts_by_severity[sev_key] = counts_by_severity.get(sev_key, 0) + 1

        rule_key = issue.rule_name or "unknown"
        counts_by_rule[rule_key] = counts_by_rule.get(rule_key, 0) + 1

        if _is_suppressed(issue):
            suppressed_count += 1
        else:
            unsuppressed_count += 1

    total_count = len(result.issues)

    # Summary
    print(f"\n{'=' * 60}")
    print("Summary:")
    if result.metadata:
        print(f"  Files scanned: {result.metadata.files_processed}")
        print(f"  Rules applied: {result.metadata.rules_applied}")
        print(f"  Duration: {result.metadata.duration_ms}ms")

    print(f"\n  Total issues: {total_count}")
    print(f"  Suppressed: {suppressed_count}")
    print(f"  Unsuppressed: {unsuppressed_count}")

    if counts_by_severity:
        print("\n  By severity:")
        for sev, count in sorted(counts_by_severity.items()):
            print(f"    {sev}: {count}")

    if counts_by_rule:
        print("\n  By rule:")
        for rule, count in sorted(counts_by_rule.items()):
            print(f"    {rule}: {count}")

    print(f"{'=' * 60}\n")


def print_json_report(
    result: ModelValidationResult[None],
    policy_id: str,  # string-id-ok: human-readable policy identifier
) -> None:
    """Print a JSON validation report."""
    # Calculate counts by severity, rule, and suppression status
    counts_by_severity: dict[str, int] = {}
    counts_by_rule: dict[str, int] = {}
    suppressed_count = 0
    unsuppressed_count = 0

    for issue in result.issues:
        sev_key = issue.severity.value
        counts_by_severity[sev_key] = counts_by_severity.get(sev_key, 0) + 1

        rule_key = issue.rule_name or "unknown"
        counts_by_rule[rule_key] = counts_by_rule.get(rule_key, 0) + 1

        if _is_suppressed(issue):
            suppressed_count += 1
        else:
            unsuppressed_count += 1

    total_count = len(result.issues)

    output = {
        "is_valid": result.is_valid,
        "policy_id": policy_id,
        "counts": {
            "total": total_count,
            "suppressed": suppressed_count,
            "unsuppressed": unsuppressed_count,
            "by_severity": counts_by_severity,
            "by_rule": counts_by_rule,
        },
        "issues": [
            {
                "severity": issue.severity.value,
                "message": issue.message,
                "code": issue.code,
                "file_path": str(issue.file_path) if issue.file_path else None,
                "line_number": issue.line_number,
                "rule_name": issue.rule_name,
                "suggestion": issue.suggestion,
                "suppressed": _is_suppressed(issue),
            }
            for issue in result.issues
        ],
        "summary": {
            "files_scanned": result.metadata.files_processed if result.metadata else 0,
            "rules_applied": result.metadata.rules_applied if result.metadata else 0,
            "issues_found": total_count,
            "duration_ms": result.metadata.duration_ms if result.metadata else 0,
        },
    }

    print(json.dumps(output, indent=2))


def main() -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        # Load policy
        policy = load_policy(args.policy)

        # Load baseline if enforcement requested
        baseline = None
        if args.baseline_enforce:
            baseline = read_baseline(args.baseline_enforce)

        # Run validation
        result = run_cross_repo_validation(
            directory=args.directory,
            policy=policy,
            rules=args.rules,
            baseline=baseline,
        )

        # Output results
        if args.format == "json":
            print_json_report(result, policy.policy_id)
        else:
            print_text_report(result, policy.policy_id)

        # Write baseline if requested
        if args.baseline_write:
            baseline = build_baseline_from_result(
                result, policy.policy_id, args.directory
            )
            write_baseline(args.baseline_write, baseline)
            if args.format == "text":
                print(f"Baseline written to: {args.baseline_write}")
                print(f"  Violations captured: {baseline.violation_count()}")

        # Return exit code
        return 0 if result.is_valid else 1

    except (
        Exception
    ) as e:  # fallback-ok: CLI boundary must return clean error, not crash
        if args.format == "json":
            print(json.dumps({"error": str(e), "is_valid": False}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
