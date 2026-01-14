"""
ValidatorArchitecture - AST-based validator for ONEX one-model-per-file architecture.

This module provides the ValidatorArchitecture class for analyzing Python source
code to enforce ONEX architectural principles:
- One model per file validation
- One enum per file validation
- One protocol per file validation
- No mixing of models, enums, and protocols

The validator uses AST analysis via the ModelCounter visitor to count
models, enums, and protocols in each file.

Usage Examples:
    Programmatic usage::

        from pathlib import Path
        from omnibase_core.validation import ValidatorArchitecture

        validator = ValidatorArchitecture()
        result = validator.validate(Path("src/"))
        if not result.is_valid:
            for issue in result.issues:
                print(f"{issue.file_path}:{issue.line_number}: {issue.message}")

    CLI usage::

        python -m omnibase_core.validation.validator_architecture src/

Thread Safety:
    ValidatorArchitecture instances are NOT thread-safe. Create separate instances
    for concurrent use or protect with external synchronization.

Schema Version:
    v1.0.0 - Initial version (OMN-1291)

See Also:
    - ValidatorBase: Base class for contract-driven validators
    - ModelValidatorSubcontract: Contract model for validator configuration
    - ModelCounter: AST visitor for counting models, enums, and protocols
"""

import ast
import logging
import sys
import urllib.parse
from pathlib import Path
from typing import ClassVar

from omnibase_core.enums import EnumSeverity
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.exception_groups import FILE_IO_ERRORS
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.common.model_validation_metadata import (
    ModelValidationMetadata,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.validation.validator_base import ValidatorBase
from omnibase_core.validation.validator_utils import ModelValidationResult

# Configure logger for this module
logger = logging.getLogger(__name__)

# Rule IDs
RULE_SINGLE_MODEL = "single_model"
RULE_SINGLE_ENUM = "single_enum"
RULE_SINGLE_PROTOCOL = "single_protocol"
RULE_NO_MIXED_TYPES = "no_mixed_types"


class ModelCounter(ast.NodeVisitor):
    """Count models, enums, and protocols in a Python file.

    AST visitor that categorizes class definitions by examining their base classes
    and naming conventions.

    Attributes:
        models: List of class names that inherit from BaseModel.
        enums: List of class names that inherit from Enum.
        protocols: List of class names that inherit from Protocol.
        type_aliases: List of type alias names (TypeAlias annotations).
    """

    def __init__(self) -> None:
        """Initialize the counter with empty lists."""
        self.models: list[str] = []
        self.enums: list[str] = []
        self.protocols: list[str] = []
        self.type_aliases: list[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions and categorize them.

        Args:
            node: AST node for class definition.
        """
        class_name = node.name

        # Check base classes to determine type
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_name = base.id
                if base_name == "BaseModel":
                    self.models.append(class_name)
                    break
                if base_name == "Enum":
                    self.enums.append(class_name)
                    break
                if base_name == "Protocol":
                    self.protocols.append(class_name)
                    break
            elif isinstance(base, ast.Attribute):
                # Handle pydantic.BaseModel or typing.Protocol
                if (
                    isinstance(base.value, ast.Name)
                    and base.value.id == "pydantic"
                    and base.attr == "BaseModel"
                ):
                    self.models.append(class_name)
                    break

        # Check for model naming patterns
        if class_name.startswith("Model") and class_name not in self.models:
            self.models.append(class_name)
        elif class_name.startswith("Enum") and class_name not in self.enums:
            self.enums.append(class_name)

        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Visit type alias assignments.

        Args:
            node: AST node for annotated assignment.
        """
        if isinstance(node.target, ast.Name):
            # Check for TypeAlias pattern
            if (
                isinstance(node.annotation, ast.Name)
                and node.annotation.id == "TypeAlias"
            ):
                self.type_aliases.append(node.target.id)
        self.generic_visit(node)


class ValidatorArchitecture(ValidatorBase):
    """Validator for ONEX one-model-per-file architecture.

    This validator uses AST analysis via ModelCounter to enforce:
    - Single model per file (no multiple BaseModel subclasses)
    - Single enum per file (no multiple Enum subclasses)
    - Single protocol per file (no multiple Protocol definitions)
    - No mixing of models, enums, and protocols in the same file

    The validator respects exemptions via:
    - Inline suppression comments

    Rule configuration is precomputed at initialization for O(1) lookups
    during validation, avoiding repeated iteration over contract rules.

    Thread Safety:
        ValidatorArchitecture instances are NOT thread-safe due to internal
        mutable state. Specifically:

        - ``_file_line_cache`` (inherited from ValidatorBase): Caches file
          contents during validation. Concurrent access from multiple threads
          could cause cache corruption or stale reads.

        - ``_rule_config_cache``: Lazily built dictionary mapping rule IDs to
          configurations. While the lazy initialization is mostly safe due to
          Python's GIL, concurrent first-access from multiple threads could
          cause redundant computation.

        **When using parallel execution (e.g., pytest-xdist workers or
        ThreadPoolExecutor), create separate validator instances per worker.**

        The contract (ModelValidatorSubcontract) is immutable (frozen=True)
        and safe to share across threads.

        For more details, see the Threading Guide:
        ``docs/guides/THREADING.md``

    Attributes:
        validator_id: Unique identifier for this validator ("architecture").

    Usage Example:
        >>> from pathlib import Path
        >>> from omnibase_core.validation.validator_architecture import ValidatorArchitecture
        >>> validator = ValidatorArchitecture()
        >>> result = validator.validate(Path("src/"))
        >>> print(f"Valid: {result.is_valid}, Issues: {len(result.issues)}")
    """

    # ONEX_EXCLUDE: string_id - human-readable validator identifier
    validator_id: ClassVar[str] = "architecture"

    @classmethod
    def main(cls) -> int:
        """CLI entry point with emoji-rich output format.

        Provides rich CLI output including:
        - Header with emoji branding
        - Per-directory validation results
        - Summary statistics
        - Help messages for failures

        Security: All user-provided paths are validated for path traversal
        attacks before use. Paths containing ".." or "//" are rejected.

        Returns:
            Exit code: 0 for success, 1 for failure.
        """
        import argparse

        parser = argparse.ArgumentParser(
            description="ONEX One-Model-Per-File Architecture Validator",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "targets",
            nargs="*",
            type=Path,
            default=[Path("src/")],
            help="Files or directories to validate (default: src/)",
        )
        parser.add_argument(
            "--max-violations",
            type=int,
            default=0,
            help="Maximum allowed violations before failing (default: 0)",
        )
        parser.add_argument(
            "-v",
            "--verbose",
            action="store_true",
            help="Print detailed output",
        )

        args = parser.parse_args()

        # Security: Validate all user-provided target paths for path traversal
        validated_targets: list[Path] = []
        for target in args.targets:
            validated = cls._validate_cli_path(target, "target path")
            if validated is None:
                return 1
            validated_targets.append(validated)

        # Print header
        print("🔍 ONEX One-Model-Per-File Validation")
        print("📋 Enforcing architectural separation")
        print()

        # Track overall stats
        total_files_checked = 0
        total_violations = 0
        all_issues: list[ModelValidationIssue] = []
        has_nonexistent = False

        # Process each target (using validated paths)
        for target in validated_targets:
            if not target.exists():
                print(f"Directory not found: {target}")
                has_nonexistent = True
                continue

            print(f"Checking: {target}")

            # Create validator and run validation
            validator = cls()

            # Override max_violations in contract if specified
            if args.max_violations > 0:
                # Create a modified contract with new max_violations
                contract = validator.contract
                # Use model_copy to update max_violations
                validator._contract = contract.model_copy(
                    update={"max_violations": args.max_violations}
                )

            result = validator.validate(target)

            # Accumulate stats
            if result.metadata:
                total_files_checked += result.metadata.files_processed or 0
                total_violations += result.metadata.violations_found or 0

            all_issues.extend(result.issues)

        print()

        # Print summary header
        print("📊 One-Model-Per-File Validation Summary")
        print("-" * 40)
        print(f"Files checked: {total_files_checked}")
        print(f"Total violations: {total_violations}")

        # Determine pass/fail based on max_violations
        effective_max_violations = args.max_violations
        is_passing = (
            total_violations <= effective_max_violations and not has_nonexistent
        )

        print()

        if is_passing and total_violations == 0:
            print("✅ PASSED - All files comply with one-model-per-file principle")
            return 0
        elif is_passing:
            print(
                f"✅ PASSED - {total_violations} violations within allowed limit "
                f"({effective_max_violations})"
            )
            return 0
        else:
            print("❌ FAILURE - ARCHITECTURAL VIOLATIONS DETECTED")
            print()

            # Print violations
            if all_issues:
                print("ARCHITECTURAL VIOLATIONS:")
                for issue in all_issues:
                    location = ""
                    if issue.file_path:
                        location = str(issue.file_path)
                        if issue.line_number:
                            location += f":{issue.line_number}"
                        location += ": "
                    print(f"  {location}{issue.message}")

            print()
            print("💡 How to fix:")
            print(
                "  - Split files with multiple models/enums/protocols into separate files"
            )
            print(
                "  - Follow the one-model-per-file principle for better maintainability"
            )
            print("  - Each file should contain only one model, enum, or protocol")

            return 1

    @classmethod
    def _validate_cli_path(cls, path: Path, context: str) -> Path | None:
        """Validate CLI-provided path with enhanced security checks.

        Extends the base class validation with additional checks for:
        - URL-encoded path traversal sequences (%2e%2e, %2f)
        - Double URL-encoded traversal (%252e%252e)
        - Null byte injection (\\x00)
        - Windows-style path traversal (..\\\\)
        - Mixed encoding attacks

        Args:
            path: User-provided path to validate.
            context: Description of the path for error messages.

        Returns:
            Resolved path if valid, None if security check fails.

        Security:
            This method provides defense-in-depth against path traversal attacks.
            It complements the base class checks with additional patterns that
            could bypass simple string matching.
        """
        path_str = str(path)

        # Security: Check for null byte injection (can truncate paths in some systems)
        if "\x00" in path_str:
            print(
                f"Security error: Null byte detected in {context}: {path}",
                file=sys.stderr,
            )
            return None

        # Security: Check for URL-encoded traversal sequences
        # Decode once to catch %2e%2e (encoded ..) and %2f (encoded /)
        try:
            decoded_once = urllib.parse.unquote(path_str)
        except (UnicodeDecodeError, ValueError):
            # If decoding fails, treat as suspicious
            print(
                f"Security error: Invalid encoding in {context}: {path}",
                file=sys.stderr,
            )
            return None

        # Check decoded path for traversal
        if ".." in decoded_once:
            print(
                f"Security error: URL-encoded path traversal detected in {context}: {path}",
                file=sys.stderr,
            )
            return None

        # Security: Check for double URL-encoding (%252e = %2e after first decode)
        try:
            decoded_twice = urllib.parse.unquote(decoded_once)
        except (UnicodeDecodeError, ValueError):
            # If second decode fails, proceed with single decode check
            pass
        else:
            if ".." in decoded_twice:
                print(
                    f"Security error: Double URL-encoded path traversal detected in {context}: {path}",
                    file=sys.stderr,
                )
                return None

        # Security: Check for Windows-style path traversal (explicit check for clarity)
        if "..\\" in path_str or "..\\\\" in path_str:
            print(
                f"Security error: Windows-style path traversal detected in {context}: {path}",
                file=sys.stderr,
            )
            return None

        # Security: Check for mixed forward/back slash attacks
        # Normalize and check for traversal attempts
        normalized = path_str.replace("\\", "/")
        if ".." in normalized:
            print(
                f"Security error: Path traversal detected in {context}: {path}",
                file=sys.stderr,
            )
            return None

        # Security: Reject paths with double slashes (bypass attempts)
        if "//" in path_str or "\\\\" in path_str:
            print(
                f"Security error: Invalid path format in {context}: {path}",
                file=sys.stderr,
            )
            return None

        # Delegate to base class for additional validation
        return super()._validate_cli_path(path, context)

    def _get_rule_config(
        self,
        rule_id: str | None,
        contract: ModelValidatorSubcontract,
    ) -> tuple[bool, EnumSeverity]:
        """Get rule enabled state and severity with contract-driven defaults.

        Overrides base class to ensure rules not explicitly defined in the
        contract are DISABLED by default. This enforces strict contract-driven
        validation where only explicitly configured rules are applied.

        Args:
            rule_id: The rule identifier to look up. If None, returns defaults.
            contract: Validator contract with rule configurations.

        Returns:
            Tuple of (enabled, severity) for the rule. If rule is not in
            contract or rule_id is None, returns (False, default_severity).
        """
        if rule_id is None:
            logger.debug(
                "Rule ID is None, using default severity: %s",
                contract.severity_default,
            )
            return (True, contract.severity_default)

        # Lazily build cache on first access
        if self._rule_config_cache is None:
            self._rule_config_cache = self._build_rule_config_cache(contract)

        # O(1) lookup from cache
        if rule_id in self._rule_config_cache:
            return self._rule_config_cache[rule_id]

        # Contract-driven behavior: rules NOT in contract are DISABLED
        # This ensures only explicitly configured rules are applied
        logger.debug(
            "Rule %s not in contract, disabling (contract-driven behavior)",
            rule_id,
        )
        return (False, contract.severity_default)

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        """Validate a single Python file for architecture compliance.

        Uses AST analysis via ModelCounter to detect architecture violations
        and returns issues for each violation found.

        Args:
            path: Path to the Python file to validate.
            contract: Validator contract with configuration.

        Returns:
            Tuple of ModelValidationIssue instances for violations found.
        """
        try:
            source = path.read_text(encoding="utf-8")
        except FILE_IO_ERRORS as e:
            # fallback-ok: log warning and skip file on read errors
            logger.warning("Cannot read file %s: %s", path, e)
            return ()

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as e:
            # fallback-ok: log warning and skip file with syntax errors
            logger.warning(
                "Skipping file with syntax error: path=%s, line=%s, error=%s",
                path,
                e.lineno,
                e.msg,
            )
            return ()

        # Run AST visitor
        counter = ModelCounter()
        counter.visit(tree)

        issues: list[ModelValidationIssue] = []

        # Check for multiple models (only if rule is enabled)
        enabled, severity = self._get_rule_config(RULE_SINGLE_MODEL, contract)
        if enabled and len(counter.models) > 1:
            issues.append(
                ModelValidationIssue(
                    severity=severity,
                    message=f"{len(counter.models)} models in one file: {', '.join(counter.models)}",
                    code=RULE_SINGLE_MODEL,
                    file_path=path,
                    line_number=1,
                    rule_name=RULE_SINGLE_MODEL,
                    suggestion="Split this file into separate files, one model per file",
                )
            )

        # Check for multiple enums (only if rule is enabled)
        enabled, severity = self._get_rule_config(RULE_SINGLE_ENUM, contract)
        if enabled and len(counter.enums) > 1:
            issues.append(
                ModelValidationIssue(
                    severity=severity,
                    message=f"{len(counter.enums)} enums in one file: {', '.join(counter.enums)}",
                    code=RULE_SINGLE_ENUM,
                    file_path=path,
                    line_number=1,
                    rule_name=RULE_SINGLE_ENUM,
                    suggestion="Split this file into separate files, one enum per file",
                )
            )

        # Check for multiple protocols (only if rule is enabled)
        enabled, severity = self._get_rule_config(RULE_SINGLE_PROTOCOL, contract)
        if enabled and len(counter.protocols) > 1:
            issues.append(
                ModelValidationIssue(
                    severity=severity,
                    message=f"{len(counter.protocols)} protocols in one file: {', '.join(counter.protocols)}",
                    code=RULE_SINGLE_PROTOCOL,
                    file_path=path,
                    line_number=1,
                    rule_name=RULE_SINGLE_PROTOCOL,
                    suggestion="Split this file into separate files, one protocol per file",
                )
            )

        # Check for mixed types (models + enums + protocols) - only if rule is enabled
        enabled, severity = self._get_rule_config(RULE_NO_MIXED_TYPES, contract)
        if enabled:
            type_categories: list[str] = []
            if counter.models:
                type_categories.append("models")
            if counter.enums:
                type_categories.append("enums")
            if counter.protocols:
                type_categories.append("protocols")

            if len(type_categories) > 1:
                issues.append(
                    ModelValidationIssue(
                        severity=severity,
                        message=f"Mixed types in one file: {', '.join(type_categories)}",
                        code=RULE_NO_MIXED_TYPES,
                        file_path=path,
                        line_number=1,
                        rule_name=RULE_NO_MIXED_TYPES,
                        suggestion="Separate models, enums, and protocols into different files",
                    )
                )

        return tuple(issues)


# Legacy API functions


def validate_one_model_per_file(file_path: Path) -> list[str]:
    """Validate a single Python file for one-model-per-file compliance.

    Note: For new code, consider using ValidatorArchitecture.validate_file() instead.

    Args:
        file_path: Path to the Python file to validate.

    Returns:
        List of error message strings (empty if valid).
    """
    errors: list[str] = []

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
        counter = ModelCounter()
        counter.visit(tree)

        # Check for multiple models
        if len(counter.models) > 1:
            errors.append(
                f"{len(counter.models)} models in one file: {', '.join(counter.models)}"
            )

        # Check for multiple enums
        if len(counter.enums) > 1:
            errors.append(
                f"{len(counter.enums)} enums in one file: {', '.join(counter.enums)}"
            )

        # Check for multiple protocols
        if len(counter.protocols) > 1:
            errors.append(
                f"{len(counter.protocols)} protocols in one file: {', '.join(counter.protocols)}"
            )

        # Check for mixed types (models + enums + protocols)
        type_categories = []
        if counter.models:
            type_categories.append("models")
        if counter.enums:
            type_categories.append("enums")
        if counter.protocols:
            type_categories.append("protocols")

        if len(type_categories) > 1:
            errors.append(f"Mixed types in one file: {', '.join(type_categories)}")

    except SyntaxError as e:
        # Wrap in ModelOnexError for consistent error handling
        wrapped_error = ModelOnexError(
            error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
            message=f"Syntax error in {file_path}: {e}",
            context={
                "file_path": str(file_path),
                "exception_type": type(e).__name__,
                "line_number": str(e.lineno) if e.lineno else "unknown",
                "offset": str(e.offset) if e.offset else "unknown",
            },
        )
        logger.exception(f"Syntax error: {wrapped_error.message}")
        errors.append(wrapped_error.message)
    except (UnicodeDecodeError, ValueError) as e:
        # Handle content parsing errors: invalid source content, encoding issues
        wrapped_error = ModelOnexError(
            error_code=EnumCoreErrorCode.FILE_READ_ERROR,
            message=f"Parse error in {file_path}: {e}",
            context={
                "file_path": str(file_path),
                "exception_type": type(e).__name__,
            },
        )
        logger.exception(f"Parse error: {wrapped_error.message}")
        errors.append(wrapped_error.message)
    except OSError as e:
        # Handle file system errors: permission denied, file not found
        wrapped_error = ModelOnexError(
            error_code=EnumCoreErrorCode.FILE_READ_ERROR,
            message=f"File read error for {file_path}: {e}",
            context={
                "file_path": str(file_path),
                "exception_type": type(e).__name__,
            },
        )
        logger.exception(f"File read error: {wrapped_error.message}")
        errors.append(wrapped_error.message)
    except TypeError as e:
        # Handle malformed AST input (e.g., wrong type passed to ast.parse)
        wrapped_error = ModelOnexError(
            error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
            message=f"Type error parsing {file_path}: {e}",
            context={
                "file_path": str(file_path),
                "exception_type": type(e).__name__,
            },
        )
        logger.exception(f"Type error: {wrapped_error.message}")
        errors.append(wrapped_error.message)
    except RecursionError:
        # Handle deeply nested code that exceeds Python's recursion limit
        wrapped_error = ModelOnexError(
            error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
            message=f"Recursion limit exceeded parsing {file_path}",
            context={
                "file_path": str(file_path),
                "exception_type": "RecursionError",
            },
        )
        logger.exception(f"Recursion error: {wrapped_error.message}")
        errors.append(wrapped_error.message)
    except MemoryError:
        # Handle extremely large files that exhaust memory during AST parsing
        wrapped_error = ModelOnexError(
            error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
            message=f"Memory exhausted parsing {file_path}",
            context={
                "file_path": str(file_path),
                "exception_type": "MemoryError",
            },
        )
        logger.exception(f"Memory error: {wrapped_error.message}")
        errors.append(wrapped_error.message)

    return errors


def validate_architecture_directory(
    directory: Path, max_violations: int = 0
) -> ModelValidationResult[None]:
    """Validate ONEX architecture for a directory.

    Note: For new code, consider using ValidatorArchitecture.validate() instead.

    Args:
        directory: Directory to validate.
        max_violations: Maximum allowed violations (default: 0).

    Returns:
        ModelValidationResult with validation outcome.
    """
    python_files = []

    for file_path in directory.rglob("*.py"):
        # Skip excluded directories and files
        if any(
            part in str(file_path)
            for part in [
                "__pycache__",
                ".git",
                "archived",
                "tests/fixtures",
                "__init__.py",  # Skip __init__.py files
            ]
        ):
            continue

        python_files.append(file_path)

    total_violations = 0
    files_with_violations: list[str] = []
    all_errors: list[str] = []

    for file_path in python_files:
        errors = validate_one_model_per_file(file_path)

        if errors:
            total_violations += len(errors)
            files_with_violations.append(str(file_path))
            all_errors.extend([f"{file_path}: {error}" for error in errors])

    is_valid = total_violations <= max_violations

    return ModelValidationResult(
        is_valid=is_valid,
        errors=all_errors,
        metadata=ModelValidationMetadata(
            validation_type="architecture",
            files_processed=len(python_files),
            max_violations=max_violations,
            violations_found=total_violations,
            files_with_violations_count=len(files_with_violations),
            files_with_violations=files_with_violations,
        ),
    )


def validate_architecture_cli() -> int:
    """CLI interface for architecture validation.

    Note: For new code, consider using ValidatorArchitecture.main() instead.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    # Delegate to the new ValidatorArchitecture.main() implementation
    return ValidatorArchitecture.main()


# CLI entry point
if __name__ == "__main__":
    sys.exit(ValidatorArchitecture.main())


__all__ = [
    "ModelCounter",
    "RULE_NO_MIXED_TYPES",
    "RULE_SINGLE_ENUM",
    "RULE_SINGLE_MODEL",
    "RULE_SINGLE_PROTOCOL",
    "ValidatorArchitecture",
    "validate_architecture_cli",
    "validate_architecture_directory",
    "validate_one_model_per_file",
]
