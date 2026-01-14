"""
Unified CLI interface for all omnibase_core validation tools.

This module provides a single entry point for all validation tools,
making it easy for other repositories to use validation functionality.

Usage:
    python -m omnibase_core.validation.cli --help
    python -m omnibase_core.validation.cli architecture
    python -m omnibase_core.validation.cli union-usage --strict
    python -m omnibase_core.validation.cli all
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Import ServiceValidationSuite DIRECTLY from the module file (not from services/__init__.py)
# to avoid circular imports. The services package imports from models which imports from
# validation, creating a circular dependency. Direct module imports avoid this.
# (OMN-1071: Service-prefixed classes should be in services/)
from omnibase_core.services.service_validation_suite import ServiceValidationSuite

from .validator_utils import ModelValidationResult


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        description="Unified validation CLI for omnibase_core",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available validation types:
  architecture    - Validate ONEX one-model-per-file architecture
  union-usage     - Validate Union type usage patterns
  contracts       - Validate YAML contract files
  patterns        - Validate code patterns and conventions
  all             - Run all validations

Examples:
  python -m omnibase_core.validation.cli architecture src/
  python -m omnibase_core.validation.cli union-usage --max-unions 50
  python -m omnibase_core.validation.cli patterns --strict
  python -m omnibase_core.validation.cli all
        """,
    )

    parser.add_argument(
        "validation_type",
        choices=[
            "architecture",
            "union-usage",
            "contracts",
            "patterns",
            "all",
            "list",
        ],
        help="Type of validation to run",
    )

    parser.add_argument(
        "directories",
        nargs="*",
        default=["src/"],
        help="Directories to validate (default: src/)",
    )

    # Common arguments
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict validation mode",
    )

    # ModelArchitecture-specific arguments
    parser.add_argument(
        "--max-violations",
        type=int,
        default=0,
        help="Maximum allowed violations for architecture validation",
    )

    # Union-specific arguments
    parser.add_argument(
        "--max-unions",
        type=int,
        default=100,
        help="Maximum allowed Union types",
    )

    # Output options
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Quiet output (errors only)",
    )

    parser.add_argument(
        "--exit-zero",
        action="store_true",
        help="Always exit with code 0 (useful for CI)",
    )

    return parser


def format_result(
    validation_type: str,
    result: ModelValidationResult[None],
    verbose: bool = False,
) -> None:
    """Format and print validation results."""
    status = "✅ PASSED" if result.is_valid else "❌ FAILED"
    print(f"\n{validation_type.upper()}: {status}")

    if verbose or not result.is_valid:
        files_checked = result.metadata.files_processed if result.metadata else 0
        print(f"  📁 Files checked: {files_checked}")
        print(f"  ⚠️  Issues found: {len(result.errors)}")

        if result.metadata:
            metadata = result.metadata
            if hasattr(metadata, "total_unions") and metadata.total_unions is not None:
                print(f"  🔗 Total unions: {metadata.total_unions}")
            if metadata.violations_found is not None:
                print(f"  🚨 Violations: {metadata.violations_found}")

        if result.errors and (verbose or len(result.errors) <= 10):
            print("  📋 Issues:")
            for error in result.errors[:10]:
                print(f"     • {error}")
            if len(result.errors) > 10:
                print(f"     ... and {len(result.errors) - 10} more issues")


def run_validation_cli() -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    suite = ServiceValidationSuite()

    # Handle special commands
    if args.validation_type == "list":
        suite.list_validators()
        return 0

    # Determine directories to validate
    directories = []
    for dir_path in args.directories:
        path = Path(dir_path)
        if not path.exists():
            if not args.quiet:
                print(f"❌ Directory not found: {dir_path}")
            if not args.exit_zero:
                return 1
            continue
        directories.append(path)

    if not directories:
        if not args.quiet:
            print("❌ No valid directories to validate")
        return 1 if not args.exit_zero else 0

    # Prepare validation parameters
    validation_kwargs = {
        "strict": args.strict,
        "max_violations": args.max_violations,
        "max_unions": args.max_unions,
    }

    # Run validations
    overall_success = True

    for directory in directories:
        if not args.quiet:
            print(f"🔍 Validating {directory}")
            print("=" * 50)

        if args.validation_type == "all":
            # Run all validations
            results = suite.run_all_validations(directory, **validation_kwargs)

            for validation_type, result in results.items():
                overall_success = overall_success and result.is_valid
                if not args.quiet:
                    format_result(validation_type, result, args.verbose)

        else:
            # Run specific validation
            result = suite.run_validation(
                args.validation_type,
                directory,
                **validation_kwargs,
            )
            overall_success = overall_success and result.is_valid

            if not args.quiet:
                format_result(args.validation_type, result, args.verbose)

    # Final summary
    if not args.quiet:
        print("\n" + "=" * 50)
        status = (
            "✅ ALL VALIDATIONS PASSED"
            if overall_success
            else "❌ VALIDATION FAILURES DETECTED"
        )
        print(f"🎯 Final Result: {status}")

    if args.exit_zero:
        return 0

    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(run_validation_cli())
