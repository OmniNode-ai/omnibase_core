"""CLI for cross-repo conformance validation.

Usage:
    python -m omnibase_core.validation.cross_repo --policy policy.yaml [directory]
    python -m omnibase_core.validation.cross_repo --policy policy.yaml --format json

Related ticket: OMN-1771
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.validation.cross_repo.engine import run_cross_repo_validation
from omnibase_core.validation.cross_repo.policy_loader import load_policy


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

    parser.add_argument(
        "directory",
        type=Path,
        nargs="?",
        default=Path.cwd(),
        help="Directory to validate (default: current directory)",
    )

    return parser


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

            print(f"  [{issue.code or 'UNKNOWN'}] {location}")
            print(f"    {issue.message}")
            if issue.suggestion:
                print(f"    Suggestion: {issue.suggestion}")
            print()

    # Summary
    if result.metadata:
        print(f"\n{'=' * 60}")
        print("Summary:")
        print(f"  Files scanned: {result.metadata.files_processed}")
        print(f"  Rules applied: {result.metadata.rules_applied}")
        print(f"  Issues found: {result.metadata.violations_found}")
        print(f"  Duration: {result.metadata.duration_ms}ms")
        print(f"{'=' * 60}\n")


def print_json_report(
    result: ModelValidationResult[None],
    policy_id: str,  # string-id-ok: human-readable policy identifier
) -> None:
    """Print a JSON validation report."""
    output = {
        "is_valid": result.is_valid,
        "policy_id": policy_id,
        "issues": [
            {
                "severity": issue.severity.value,
                "message": issue.message,
                "code": issue.code,
                "file_path": str(issue.file_path) if issue.file_path else None,
                "line_number": issue.line_number,
                "rule_name": issue.rule_name,
                "suggestion": issue.suggestion,
            }
            for issue in result.issues
        ],
        "summary": {
            "files_scanned": result.metadata.files_processed if result.metadata else 0,
            "rules_applied": result.metadata.rules_applied if result.metadata else 0,
            "issues_found": len(result.issues),
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

        # Run validation
        result = run_cross_repo_validation(
            directory=args.directory,
            policy=policy,
            rules=args.rules,
        )

        # Output results
        if args.format == "json":
            print_json_report(result, policy.policy_id)
        else:
            print_text_report(result, policy.policy_id)

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
