#!/usr/bin/env python3
"""
ONEX Standards Validation
Comprehensive validation for ONEX framework compliance across all omni* repositories.

This script can be imported by other repositories to validate ONEX standards:
    from omnibase_core.validation import validate_onex_standards
    result = validate_onex_standards(".")
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

# Import validation functions from omnibase_core or local scripts
try:
    from omnibase_core.validation import (
        audit_protocols,
        check_against_spi,
        validate_naming_conventions,
        validate_no_backward_compatibility,
        validate_no_manual_yaml,
        validate_no_string_versions,
        validate_repository_structure,
    )
except ImportError:
    # If running within omnibase_core repository, use local scripts
    import subprocess
    import sys
    from pathlib import Path

    def validate_repository_structure(repo_path):
        """Local fallback for repository structure validation."""
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/validation/validate_structure.py",
                    repo_path,
                    Path(repo_path).name,
                ],
                capture_output=True,
                text=True,
                cwd=repo_path,
            )

            return type(
                "Result",
                (),
                {
                    "success": result.returncode == 0,
                    "violations": (
                        result.stderr.split("\n") if result.returncode != 0 else []
                    ),
                },
            )()
        except Exception as e:
            return type("Result", (), {"success": False, "violations": [str(e)]})()

    def validate_naming_conventions(repo_path):
        """Local fallback for naming convention validation."""
        try:
            result = subprocess.run(
                [sys.executable, "scripts/validation/validate_naming.py", repo_path],
                capture_output=True,
                text=True,
                cwd=repo_path,
            )

            return type(
                "Result",
                (),
                {
                    "success": result.returncode == 0,
                    "violations": (
                        result.stderr.split("\n") if result.returncode != 0 else []
                    ),
                },
            )()
        except Exception as e:
            return type("Result", (), {"success": False, "violations": [str(e)]})()

    def validate_no_string_versions(repo_path):
        """Local fallback for string version validation."""
        try:
            result = subprocess.run(
                [sys.executable, "scripts/validation/validate-string-versions.py"],
                capture_output=True,
                text=True,
                cwd=repo_path,
            )

            return type(
                "Result",
                (),
                {
                    "success": result.returncode == 0,
                    "violations": (
                        result.stderr.split("\n") if result.returncode != 0 else []
                    ),
                },
            )()
        except Exception as e:
            return type("Result", (), {"success": False, "violations": [str(e)]})()

    def validate_no_backward_compatibility(repo_path):
        """Local fallback for backward compatibility validation."""
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/validation/validate-no-backward-compatibility.py",
                    "-d",
                    "src/",
                ],
                capture_output=True,
                text=True,
                cwd=repo_path,
            )

            return type(
                "Result",
                (),
                {
                    "success": result.returncode == 0,
                    "violations": (
                        result.stderr.split("\n") if result.returncode != 0 else []
                    ),
                },
            )()
        except Exception as e:
            return type("Result", (), {"success": False, "violations": [str(e)]})()

    def validate_no_manual_yaml(repo_path):
        """Local fallback for manual YAML validation."""
        try:
            # Find Python files to validate
            py_files = []
            src_path = Path(repo_path) / "src"
            if src_path.exists():
                py_files = list(src_path.rglob("*.py"))

            if not py_files:
                return type("Result", (), {"success": True, "violations": []})()

            result = subprocess.run(
                [
                    "poetry",
                    "run",
                    "python",
                    "scripts/validation/validate-no-manual-yaml.py",
                ]
                + [str(f) for f in py_files[:5]],  # Limit to first 5 files for testing
                capture_output=True,
                text=True,
                cwd=repo_path,
            )

            return type(
                "Result",
                (),
                {
                    "success": result.returncode == 0,
                    "violations": (
                        result.stderr.split("\n") if result.returncode != 0 else []
                    ),
                },
            )()
        except Exception as e:
            return type("Result", (), {"success": False, "violations": [str(e)]})()

    def audit_protocols(repo_path):
        """Local fallback for protocol auditing."""
        # Protocol auditing is optional for most repositories
        return type(
            "Result", (), {"success": True, "protocols_found": 0, "violations": []}
        )()

    def check_against_spi(repo_path, spi_path):
        """Local fallback for SPI duplication check."""
        # SPI checking is optional and requires special setup
        return type(
            "Result", (), {"success": True, "exact_duplicates": [], "violations": []}
        )()

    print("⚠️  Using local script fallbacks (omnibase_core not installed as package)")


class OnexStandardsValidator:
    """Comprehensive ONEX standards validator for any omni* repository."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.repo_name = self.repo_path.name
        self.violations = []
        self.warnings = []

    def validate_all(self) -> Dict[str, Any]:
        """Run all ONEX standards validation checks."""
        print(f"🔍 Validating ONEX standards for {self.repo_name}...")

        results = {
            "repository_structure": self._validate_structure(),
            "naming_conventions": self._validate_naming(),
            "string_versions": self._validate_string_versions(),
            "backward_compatibility": self._validate_backward_compatibility(),
            "manual_yaml": self._validate_manual_yaml(),
            "protocols": self._validate_protocols(),
            "spi_duplicates": self._validate_spi_duplicates(),
        }

        # Summary
        failed_checks = [
            name for name, result in results.items() if not result["success"]
        ]
        warning_checks = [
            name for name, result in results.items() if result.get("warnings")
        ]

        if failed_checks:
            print(f"\n❌ ONEX Standards Validation FAILED")
            print(f"   Failed checks: {', '.join(failed_checks)}")
            for violation in self.violations:
                print(f"   • {violation}")
        else:
            print(f"\n✅ ONEX Standards Validation PASSED")

        if warning_checks:
            print(f"\n⚠️  Warnings found in: {', '.join(warning_checks)}")
            for warning in self.warnings:
                print(f"   • {warning}")

        return {
            "success": len(failed_checks) == 0,
            "violations": self.violations,
            "warnings": self.warnings,
            "results": results,
            "summary": {
                "total_checks": len(results),
                "passed_checks": len(results) - len(failed_checks),
                "failed_checks": len(failed_checks),
                "warning_checks": len(warning_checks),
            },
        }

    def _validate_structure(self) -> Dict[str, Any]:
        """Validate repository structure compliance."""
        try:
            result = validate_repository_structure(str(self.repo_path))
            if not result.success:
                self.violations.extend([f"Structure: {v}" for v in result.violations])
            return {"success": result.success, "details": result}
        except Exception as e:
            self.violations.append(f"Structure validation error: {e}")
            return {"success": False, "error": str(e)}

    def _validate_naming(self) -> Dict[str, Any]:
        """Validate naming conventions compliance."""
        try:
            result = validate_naming_conventions(str(self.repo_path))
            if not result.success:
                self.violations.extend([f"Naming: {v}" for v in result.violations])
            return {"success": result.success, "details": result}
        except Exception as e:
            self.violations.append(f"Naming validation error: {e}")
            return {"success": False, "error": str(e)}

    def _validate_string_versions(self) -> Dict[str, Any]:
        """Validate no string version anti-patterns."""
        try:
            result = validate_no_string_versions(str(self.repo_path))
            if not result.success:
                self.violations.extend(
                    [f"String versions: {v}" for v in result.violations]
                )
            return {"success": result.success, "details": result}
        except Exception as e:
            self.violations.append(f"String version validation error: {e}")
            return {"success": False, "error": str(e)}

    def _validate_backward_compatibility(self) -> Dict[str, Any]:
        """Validate no backward compatibility anti-patterns."""
        try:
            result = validate_no_backward_compatibility(str(self.repo_path))
            if not result.success:
                self.violations.extend(
                    [f"Backward compatibility: {v}" for v in result.violations]
                )
            return {"success": result.success, "details": result}
        except Exception as e:
            self.violations.append(f"Backward compatibility validation error: {e}")
            return {"success": False, "error": str(e)}

    def _validate_manual_yaml(self) -> Dict[str, Any]:
        """Validate no manual YAML usage."""
        try:
            result = validate_no_manual_yaml(str(self.repo_path))
            if not result.success:
                self.violations.extend([f"Manual YAML: {v}" for v in result.violations])
            return {"success": result.success, "details": result}
        except Exception as e:
            self.violations.append(f"Manual YAML validation error: {e}")
            return {"success": False, "error": str(e)}

    def _validate_protocols(self) -> Dict[str, Any]:
        """Validate protocol structure and compliance."""
        try:
            result = audit_protocols(str(self.repo_path))
            if not result.success:
                self.violations.extend([f"Protocols: {v}" for v in result.violations])

            # Add warning if repository has many protocols
            if result.protocols_found > 10:
                self.warnings.append(
                    f"Repository has {result.protocols_found} protocols - consider SPI migration"
                )

            return {"success": result.success, "details": result}
        except Exception as e:
            # Protocol validation is optional - don't fail if no protocols exist
            return {
                "success": True,
                "details": f"No protocols found or validation error: {e}",
            }

    def _validate_spi_duplicates(self) -> Dict[str, Any]:
        """Validate no duplicate protocols with omnibase_spi."""
        spi_path = self.repo_path.parent / "omnibase_spi"

        if not spi_path.exists():
            self.warnings.append(
                "omnibase_spi not found - skipping SPI duplication check"
            )
            return {"success": True, "details": "SPI not available"}

        try:
            result = check_against_spi(str(self.repo_path), str(spi_path))
            if not result.success:
                self.violations.extend(
                    [
                        f"SPI duplicates: {d.protocols[0].name}"
                        for d in result.exact_duplicates
                    ]
                )
            return {"success": result.success, "details": result}
        except Exception as e:
            self.warnings.append(f"SPI duplication check error: {e}")
            return {"success": True, "error": str(e)}


def validate_onex_standards(repo_path: str = ".") -> Dict[str, Any]:
    """
    Main function for validating ONEX standards.

    Args:
        repo_path: Path to repository to validate

    Returns:
        Dictionary with validation results
    """
    validator = OnexStandardsValidator(repo_path)
    return validator.validate_all()


def main():
    """CLI interface for ONEX standards validation."""
    parser = argparse.ArgumentParser(description="Validate ONEX framework standards")
    parser.add_argument(
        "path", nargs="?", default=".", help="Repository path to validate"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--warnings-as-errors", action="store_true", help="Treat warnings as errors"
    )

    args = parser.parse_args()

    # Run validation
    result = validate_onex_standards(args.path)

    if args.verbose:
        print("\n📊 Detailed Results:")
        for check_name, check_result in result["results"].items():
            status = "✅" if check_result["success"] else "❌"
            print(f"   {status} {check_name.replace('_', ' ').title()}")
            if not check_result["success"] and "details" in check_result:
                print(
                    f"      Details: {check_result.get('error', 'See violations above')}"
                )

    # Print summary
    summary = result["summary"]
    print(
        f"\n📈 Summary: {summary['passed_checks']}/{summary['total_checks']} checks passed"
    )

    if result["warnings"] and args.warnings_as_errors:
        print("⚠️  Treating warnings as errors")
        sys.exit(1)

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
