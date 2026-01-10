"""
ValidatorNamingConvention - Contract-driven naming convention validator.

This module provides the ValidatorNamingConvention class for validating
file, class, and function naming conventions in Python source code.

The validator uses:
- Directory-based file name prefix rules (e.g., model_*.py in models/)
- AST analysis for class naming (PascalCase, anti-pattern detection)
- AST analysis for function naming (snake_case)

Exemptions are respected via:
- Allowed files (__init__.py, conftest.py, py.typed)
- Allowed prefixes (private modules starting with _)
- Inline suppression comments from contract configuration

Usage Examples:
    Programmatic usage::

        from pathlib import Path
        from omnibase_core.validation import ValidatorNamingConvention

        validator = ValidatorNamingConvention()
        result = validator.validate(Path("src/"))
        if not result.is_valid:
            for issue in result.issues:
                print(f"{issue.file_path}:{issue.line_number}: {issue.message}")

    CLI usage::

        python -m omnibase_core.validation.validator_naming_convention src/

Thread Safety:
    ValidatorNamingConvention instances are NOT thread-safe. Create separate
    instances for concurrent use or protect with external synchronization.

Schema Version:
    v1.0.0 - Initial version (OMN-1291)

See Also:
    - ValidatorBase: Base class for contract-driven validators
    - ModelValidatorSubcontract: Contract model for validator configuration
    - checker_naming_convention: Original implementation with backward compat exports
"""

import ast
import sys
from pathlib import Path
from typing import ClassVar

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_validation_severity import EnumValidationSeverity
from omnibase_core.errors.exception_groups import FILE_IO_ERRORS, YAML_PARSING_ERRORS
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.validation.checker_naming_convention import (
    ALLOWED_FILE_PREFIXES,
    ALLOWED_FILES,
    DIRECTORY_PREFIX_RULES,
    NamingConventionChecker,
    check_file_name,
)
from omnibase_core.validation.validator_base import ValidatorBase

# Rule identifiers for issue tracking
RULE_FILE_NAMING = "file_naming"
RULE_CLASS_NAMING = "class_naming"
RULE_FUNCTION_NAMING = "function_naming"


class ValidatorNamingConvention(ValidatorBase):
    """Validator for naming conventions in Python code.

    This validator uses file inspection and AST analysis to detect naming
    convention violations, including:
    - File names not following directory-specific prefix rules
    - Class names not using PascalCase
    - Class names using anti-pattern terms (Manager, Handler, etc.)
    - Function names not using snake_case

    The validator respects exemptions via:
    - Allowed files (__init__.py, conftest.py, py.typed)
    - Private modules (files starting with _)
    - Inline suppression comments

    Attributes:
        validator_id: Unique identifier for this validator ("naming_convention").

    Usage Example:
        >>> from pathlib import Path
        >>> from omnibase_core.validation.validator_naming_convention import (
        ...     ValidatorNamingConvention
        ... )
        >>> validator = ValidatorNamingConvention()
        >>> result = validator.validate(Path("src/"))
        >>> print(f"Valid: {result.is_valid}, Issues: {len(result.issues)}")
    """

    # ONEX_EXCLUDE: string_id - human-readable validator identifier
    validator_id: ClassVar[str] = "naming_convention"

    def _load_contract(self) -> ModelValidatorSubcontract:
        """Load contract from YAML, handling nested 'validation:' structure.

        The contract YAML has the structure:
            contract_kind: validation_subcontract
            validation:
                version: ...
                validator_id: ...
                ...

        This method extracts the nested 'validation' section.

        Returns:
            Loaded ModelValidatorSubcontract instance.

        Raises:
            ModelOnexError: If contract file not found or invalid.
        """
        contract_path = self._get_contract_path()

        if not contract_path.exists():
            raise ModelOnexError(
                message=f"Validator contract not found: {contract_path}",
                error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
                context={
                    "validator_id": self.validator_id,
                    "contract_path": str(contract_path),
                },
            )

        try:
            content = contract_path.read_text(encoding="utf-8")
            # ONEX_EXCLUDE: manual_yaml - validator contract loading requires raw YAML
            data = yaml.safe_load(content)

            if not isinstance(data, dict):
                raise ModelOnexError(
                    message="Contract must be a YAML mapping",
                    error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
                    context={
                        "validator_id": self.validator_id,
                        "contract_path": str(contract_path),
                    },
                )

            # Handle nested 'validation:' structure
            if "validation" in data and isinstance(data["validation"], dict):
                data = data["validation"]

            return ModelValidatorSubcontract.model_validate(data)

        except FILE_IO_ERRORS as e:
            # boundary-ok: convert file I/O errors to structured error
            raise ModelOnexError(
                message=f"Cannot read contract file: {e}",
                error_code=EnumCoreErrorCode.FILE_READ_ERROR,
                context={
                    "validator_id": self.validator_id,
                    "contract_path": str(contract_path),
                    "error": str(e),
                },
            ) from e
        except YAML_PARSING_ERRORS as e:
            # boundary-ok: convert YAML parsing errors to structured error
            raise ModelOnexError(
                message=f"Invalid YAML in contract file: {e}",
                error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
                context={
                    "validator_id": self.validator_id,
                    "contract_path": str(contract_path),
                    "yaml_error": str(e),
                },
            ) from e

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        """Validate a single Python file for naming convention violations.

        Checks:
        1. File name follows directory-specific prefix conventions
        2. Class names use PascalCase and avoid anti-patterns
        3. Function names use snake_case

        Args:
            path: Path to the Python file to validate.
            contract: Validator contract with configuration.

        Returns:
            Tuple of ModelValidationIssue instances for violations found.
        """
        issues: list[ModelValidationIssue] = []

        # Get rule enablement from contract
        rules_enabled = {rule.rule_id: rule.enabled for rule in contract.rules}
        rules_severity = {rule.rule_id: rule.severity for rule in contract.rules}

        # Default to enabled if rule not in contract
        file_naming_enabled = rules_enabled.get(RULE_FILE_NAMING, True)
        class_naming_enabled = rules_enabled.get(RULE_CLASS_NAMING, True)
        function_naming_enabled = rules_enabled.get(RULE_FUNCTION_NAMING, True)

        # Get severities (default to contract's severity_default)
        file_naming_severity = rules_severity.get(
            RULE_FILE_NAMING, contract.severity_default
        )
        class_naming_severity = rules_severity.get(
            RULE_CLASS_NAMING, contract.severity_default
        )
        function_naming_severity = rules_severity.get(
            RULE_FUNCTION_NAMING, contract.severity_default
        )

        # 1. Check file naming (line 0 = file-level issue)
        if file_naming_enabled:
            error = check_file_name(path)
            if error:
                issues.append(
                    ModelValidationIssue(
                        severity=file_naming_severity,
                        message=error,
                        code=RULE_FILE_NAMING,
                        file_path=path,
                        line_number=1,  # File-level issue at line 1
                        rule_name=RULE_FILE_NAMING,
                        suggestion=self._get_file_naming_suggestion(path),
                    )
                )

        # 2 & 3. Check class and function naming via AST
        if class_naming_enabled or function_naming_enabled:
            ast_issues = self._validate_ast(
                path=path,
                class_naming_enabled=class_naming_enabled,
                function_naming_enabled=function_naming_enabled,
                class_naming_severity=class_naming_severity,
                function_naming_severity=function_naming_severity,
            )
            issues.extend(ast_issues)

        return tuple(issues)

    def _validate_ast(
        self,
        path: Path,
        class_naming_enabled: bool,
        function_naming_enabled: bool,
        class_naming_severity: EnumValidationSeverity,
        function_naming_severity: EnumValidationSeverity,
    ) -> list[ModelValidationIssue]:
        """Run AST-based validation for class and function naming.

        Args:
            path: Path to Python file to analyze.
            class_naming_enabled: Whether to check class naming.
            function_naming_enabled: Whether to check function naming.
            class_naming_severity: Severity for class naming issues.
            function_naming_severity: Severity for function naming issues.

        Returns:
            List of ModelValidationIssue instances for AST-based violations.
        """
        issues: list[ModelValidationIssue] = []

        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            # File read error - skip silently
            return issues

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            # Syntax error - skip silently (not a valid Python file for AST analysis)
            return issues

        # Use the existing NamingConventionChecker from checker_naming_convention
        checker = NamingConventionChecker(str(path))
        checker.visit(tree)

        # Convert checker issues to ModelValidationIssue
        for issue_str in checker.issues:
            # Parse the issue string format: "Line {lineno}: {message}"
            line_number = 1  # Default
            message = issue_str

            if issue_str.startswith("Line "):
                try:
                    # Extract line number from "Line {lineno}: {message}"
                    parts = issue_str.split(":", 1)
                    if len(parts) >= 2:
                        line_part = parts[0]  # "Line {lineno}"
                        line_number = int(line_part.replace("Line ", "").strip())
                        message = parts[1].strip()
                except (ValueError, IndexError):
                    pass

            # Determine rule type and severity based on message content
            if "Class name" in issue_str:
                if not class_naming_enabled:
                    continue
                severity = class_naming_severity
                rule_name = RULE_CLASS_NAMING
                code = RULE_CLASS_NAMING
            elif "Function name" in issue_str or "Async function name" in issue_str:
                if not function_naming_enabled:
                    continue
                severity = function_naming_severity
                rule_name = RULE_FUNCTION_NAMING
                code = RULE_FUNCTION_NAMING
            else:
                # Unknown issue type - default to class naming
                if not class_naming_enabled:
                    continue
                severity = class_naming_severity
                rule_name = RULE_CLASS_NAMING
                code = RULE_CLASS_NAMING

            issues.append(
                ModelValidationIssue(
                    severity=severity,
                    message=message,
                    code=code,
                    file_path=path,
                    line_number=line_number,
                    rule_name=rule_name,
                )
            )

        return issues

    def _get_file_naming_suggestion(self, path: Path) -> str | None:
        """Generate a suggestion for fixing file naming violations.

        Args:
            path: Path to the file with naming violation.

        Returns:
            Suggestion string or None if no suggestion can be generated.
        """
        file_name = path.name

        # Skip non-Python files and allowed files
        if not file_name.endswith(".py"):
            return None
        if file_name in ALLOWED_FILES:
            return None
        if any(file_name.startswith(prefix) for prefix in ALLOWED_FILE_PREFIXES):
            return None

        # Find the relevant directory rule
        parts = path.parts
        try:
            omnibase_idx = parts.index("omnibase_core")
            if omnibase_idx + 1 < len(parts) - 1:
                relevant_dir = parts[omnibase_idx + 1]
                if relevant_dir in DIRECTORY_PREFIX_RULES:
                    prefixes = DIRECTORY_PREFIX_RULES[relevant_dir]
                    suggested_prefix = prefixes[0]  # Use first prefix as suggestion
                    base_name = file_name[:-3]  # Remove .py
                    return f"Consider renaming to '{suggested_prefix}{base_name}.py'"
        except ValueError:
            pass

        return None


# CLI entry point
if __name__ == "__main__":
    sys.exit(ValidatorNamingConvention.main())


__all__ = [
    "RULE_CLASS_NAMING",
    "RULE_FILE_NAMING",
    "RULE_FUNCTION_NAMING",
    "ValidatorNamingConvention",
]
