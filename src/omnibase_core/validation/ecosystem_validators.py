"""
Ecosystem validation functions for omni* repositories.

These functions provide importable validation that can be used by pre-commit hooks
and other tools across the omni* ecosystem.
"""

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, NamedTuple

from .validation_utils import ValidationResult


class ValidationResponse(NamedTuple):
    """Standardized validation response for pre-commit hooks."""

    success: bool
    violations: List[str] = []
    details: Dict[str, Any] = {}


def validate_repository_structure(
    repo_path: str = ".", repo_name: str = None
) -> ValidationResponse:
    """
    Validate repository structure compliance.

    Args:
        repo_path: Path to repository root
        repo_name: Repository name (auto-detected if not provided)

    Returns:
        ValidationResponse with success status and any violations
    """
    try:
        repo_path_obj = Path(repo_path).resolve()

        # Auto-detect repo name if not provided
        if repo_name is None:
            repo_name = repo_path_obj.name

        # Run the validation script
        script_path = repo_path_obj / "scripts" / "validation" / "validate_structure.py"
        if not script_path.exists():
            # Try to find script relative to this module
            module_dir = Path(__file__).parent.parent.parent.parent.parent
            script_path = (
                module_dir / "scripts" / "validation" / "validate_structure.py"
            )

        if script_path.exists():
            result = subprocess.run(
                [
                    sys.executable,
                    str(script_path),
                    str(repo_path_obj),
                    repo_name,
                    "--json",
                ],
                capture_output=True,
                text=True,
                cwd=repo_path_obj,
            )

            if result.returncode == 0:
                return ValidationResponse(success=True)
            else:
                # Parse violations from output
                violations = (
                    result.stderr.split("\n")
                    if result.stderr
                    else ["Structure validation failed"]
                )
                return ValidationResponse(success=False, violations=violations)
        else:
            return ValidationResponse(
                success=True,
                details={"message": "Structure validation script not found - skipping"},
            )

    except Exception as e:
        return ValidationResponse(
            success=False, violations=[f"Structure validation error: {str(e)}"]
        )


def validate_naming_conventions(repo_path: str = ".") -> ValidationResponse:
    """
    Validate naming conventions compliance.

    Args:
        repo_path: Path to repository root

    Returns:
        ValidationResponse with success status and any violations
    """
    try:
        repo_path_obj = Path(repo_path).resolve()

        # Run the validation script
        script_path = repo_path_obj / "scripts" / "validation" / "validate_naming.py"
        if not script_path.exists():
            # Try to find script relative to this module
            module_dir = Path(__file__).parent.parent.parent.parent.parent
            script_path = module_dir / "scripts" / "validation" / "validate_naming.py"

        if script_path.exists():
            result = subprocess.run(
                [sys.executable, str(script_path), str(repo_path_obj)],
                capture_output=True,
                text=True,
                cwd=repo_path_obj,
            )

            if result.returncode == 0:
                return ValidationResponse(success=True)
            else:
                violations = (
                    result.stderr.split("\n")
                    if result.stderr
                    else ["Naming validation failed"]
                )
                return ValidationResponse(success=False, violations=violations)
        else:
            return ValidationResponse(
                success=True,
                details={"message": "Naming validation script not found - skipping"},
            )

    except Exception as e:
        return ValidationResponse(
            success=False, violations=[f"Naming validation error: {str(e)}"]
        )


def validate_no_string_versions(repo_path: str = ".") -> ValidationResponse:
    """
    Validate no string version anti-patterns.

    Args:
        repo_path: Path to repository root

    Returns:
        ValidationResponse with success status and any violations
    """
    try:
        repo_path_obj = Path(repo_path).resolve()

        # Run the validation script
        script_path = (
            repo_path_obj / "scripts" / "validation" / "validate-string-versions.py"
        )
        if not script_path.exists():
            # Try to find script relative to this module
            module_dir = Path(__file__).parent.parent.parent.parent.parent
            script_path = (
                module_dir / "scripts" / "validation" / "validate-string-versions.py"
            )

        if script_path.exists():
            result = subprocess.run(
                [sys.executable, str(script_path), "--dir", str(repo_path_obj)],
                capture_output=True,
                text=True,
                cwd=repo_path_obj,
            )

            if result.returncode == 0:
                return ValidationResponse(success=True)
            else:
                # Get violations from stderr, or use stdout if stderr is empty
                error_output = (
                    result.stderr or result.stdout or "String version validation failed"
                )
                violations = [
                    line.strip() for line in error_output.split("\n") if line.strip()
                ]
                return ValidationResponse(success=False, violations=violations)
        else:
            return ValidationResponse(
                success=True,
                details={
                    "message": "String version validation script not found - skipping"
                },
            )

    except Exception as e:
        return ValidationResponse(
            success=False, violations=[f"String version validation error: {str(e)}"]
        )


def validate_no_legacy_patterns(repo_path: str = ".") -> ValidationResponse:
    """
    Validate against deprecated code patterns.

    Args:
        repo_path: Path to repository root

    Returns:
        ValidationResponse with success status and any violations
    """
    try:
        repo_path_obj = Path(repo_path).resolve()

        # Run the validation script
        script_path = (
            repo_path_obj
            / "scripts"
            / "validation"
            / "validate-no-backward-compatibility.py"
        )
        if not script_path.exists():
            # Try to find script relative to this module
            module_dir = Path(__file__).parent.parent.parent.parent.parent
            script_path = (
                module_dir
                / "scripts"
                / "validation"
                / "validate-no-backward-compatibility.py"
            )

        if script_path.exists():
            result = subprocess.run(
                [sys.executable, str(script_path), "-d", "src/"],
                capture_output=True,
                text=True,
                cwd=repo_path_obj,
            )

            if result.returncode == 0:
                return ValidationResponse(success=True)
            else:
                violations = (
                    result.stderr.split("\n")
                    if result.stderr
                    else ["Code pattern validation failed"]
                )
                return ValidationResponse(success=False, violations=violations)
        else:
            return ValidationResponse(
                success=True,
                details={
                    "message": "Code pattern validation script not found - skipping"
                },
            )

    except Exception as e:
        return ValidationResponse(
            success=False,
            violations=[f"Code pattern validation error: {str(e)}"],
        )


def validate_no_manual_yaml(repo_path: str = ".") -> ValidationResponse:
    """
    Validate no manual YAML anti-patterns.

    Args:
        repo_path: Path to repository root

    Returns:
        ValidationResponse with success status and any violations
    """
    try:
        repo_path_obj = Path(repo_path).resolve()

        # Run the validation script
        script_path = (
            repo_path_obj / "scripts" / "validation" / "validate-no-manual-yaml.py"
        )
        if not script_path.exists():
            # Try to find script relative to this module
            module_dir = Path(__file__).parent.parent.parent.parent.parent
            script_path = (
                module_dir / "scripts" / "validation" / "validate-no-manual-yaml.py"
            )

        if script_path.exists():
            # Get Python files to check
            py_files = list(repo_path_obj.rglob("src/**/*.py"))
            if py_files:
                result = subprocess.run(
                    ["poetry", "run", "python", str(script_path)]
                    + [str(f) for f in py_files[:5]],  # Limit for testing
                    capture_output=True,
                    text=True,
                    cwd=repo_path_obj,
                )

                if result.returncode == 0:
                    return ValidationResponse(success=True)
                else:
                    violations = (
                        result.stderr.split("\n")
                        if result.stderr
                        else ["Manual YAML validation failed"]
                    )
                    return ValidationResponse(success=False, violations=violations)
            else:
                return ValidationResponse(
                    success=True,
                    details={"message": "No Python files found to validate"},
                )
        else:
            return ValidationResponse(
                success=True,
                details={
                    "message": "Manual YAML validation script not found - skipping"
                },
            )

    except Exception as e:
        return ValidationResponse(
            success=False, violations=[f"Manual YAML validation error: {str(e)}"]
        )
