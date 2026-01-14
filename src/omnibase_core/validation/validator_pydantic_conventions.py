"""
ValidatorPydanticConventions - AST-based validator for Pydantic model conventions.

This module provides the ValidatorPydanticConventions class for analyzing Python
source code to detect Pydantic model configuration issues that violate ONEX
conventions.

The validator uses AST analysis to find:
- Models inheriting from BaseModel without model_config
- Empty ConfigDict() declarations
- frozen=True without from_attributes=True
- Contract models missing explicit extra= policy
- Unnecessary Field(default=None) patterns

Exemptions are respected via:
- Known base models that provide their own configuration
- Inline suppression comments from contract configuration

Usage Examples:
    Programmatic usage::

        from pathlib import Path
        from omnibase_core.validation import ValidatorPydanticConventions

        validator = ValidatorPydanticConventions()
        result = validator.validate(Path("src/"))
        if not result.is_valid:
            for issue in result.issues:
                print(f"{issue.file_path}:{issue.line_number}: {issue.message}")

    CLI usage::

        python -m omnibase_core.validation.validator_pydantic_conventions src/

Thread Safety:
    ValidatorPydanticConventions instances are NOT thread-safe. Create separate
    instances for concurrent use or protect with external synchronization.

Schema Version:
    v1.0.0 - Initial version (OMN-1314)

See Also:
    - ValidatorBase: Base class for contract-driven validators
    - ModelValidatorSubcontract: Contract model for validator configuration
    - CLAUDE.md: Pydantic Model Configuration Standards section
"""

import ast
import logging
from pathlib import Path
from typing import ClassVar

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.validator_base import ValidatorBase

# Configure logger for this module
logger = logging.getLogger(__name__)

# Rule identifiers for issue tracking
RULE_MISSING_CONFIG = "missing-config"
RULE_EMPTY_CONFIG = "empty-config"
RULE_FROZEN_WITHOUT_FROM_ATTRIBUTES = "frozen-without-from-attributes"
RULE_CONTRACT_MISSING_EXTRA = "contract-missing-extra"
RULE_UNNECESSARY_FIELD_DEFAULT_NONE = "unnecessary-field-default-none"

# Known base models that provide their own model_config.
# Subclasses of these don't need their own model_config declaration.
KNOWN_BASE_MODELS: frozenset[str] = frozenset(
    {
        "ModelIntentPayloadBase",
        "ModelActionPayloadBase",
        "ModelOnexEvent",
        "ModelRuntimeEventBase",
        "ModelDirectivePayloadBase",
        "ModelContractValidationEventBase",
        "ModelContractBase",
        "ModelComputationInputBase",
        "ModelComputationOutputBase",
        "ModelCoreIntent",
        "ModelBaseHeaderTransformation",
        "ModelFieldAccessor",
        "ModelBaseCollection",
        "ModelBaseFactory",
        "ModelServiceBaseProcessor",
    }
)


class ValidatorPydanticConventions(ValidatorBase):
    """Validator for Pydantic model configuration conventions.

    This validator uses AST analysis to detect Pydantic model configuration
    issues, including:
    - Models inheriting from BaseModel without model_config
    - Legacy class Config: style configuration (Pydantic v1)
    - Empty ConfigDict() declarations with no explicit policy
    - frozen=True without from_attributes=True (pytest-xdist compatibility)
    - Contract models missing explicit extra= policy
    - Unnecessary Field(default=None) patterns

    The validator respects exemptions via:
    - Known base models that provide their own configuration
    - Inline suppression comments

    Rule configuration is precomputed at initialization for O(1) lookups
    during validation, avoiding repeated iteration over contract rules.

    Thread Safety:
        ValidatorPydanticConventions instances are NOT thread-safe due to
        internal mutable state inherited from ValidatorBase. Specifically:

        - ``_file_line_cache`` (inherited from ValidatorBase): Caches file
          contents during validation. Concurrent access from multiple threads
          could cause cache corruption or stale reads.

        - ``_rule_config_cache`` (inherited from ValidatorBase): Lazily built
          dictionary mapping rule IDs to configurations. While the lazy
          initialization is mostly safe due to Python's GIL, concurrent
          first-access from multiple threads could cause redundant computation.

        **When using parallel execution (e.g., pytest-xdist workers or
        ThreadPoolExecutor), create separate validator instances per worker.**

        The contract (ModelValidatorSubcontract) is immutable (frozen=True)
        and safe to share across threads.

        For more details, see the Threading Guide:
        ``docs/guides/THREADING.md``

    Attributes:
        validator_id: Unique identifier for this validator ("pydantic_conventions").

    Usage Example:
        >>> from pathlib import Path
        >>> from omnibase_core.validation.validator_pydantic_conventions import (
        ...     ValidatorPydanticConventions
        ... )
        >>> validator = ValidatorPydanticConventions()
        >>> result = validator.validate(Path("src/"))
        >>> print(f"Valid: {result.is_valid}, Issues: {len(result.issues)}")
    """

    # ONEX_EXCLUDE: string_id - human-readable validator identifier
    validator_id: ClassVar[str] = "pydantic_conventions"

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        """Validate a single Python file for Pydantic convention violations.

        Uses AST analysis to detect Pydantic model configuration issues
        and returns issues for each violation found. Applies per-rule
        enablement and severity overrides from the contract.

        Args:
            path: Path to the Python file to validate.
            contract: Validator contract with configuration.

        Returns:
            Tuple of ModelValidationIssue instances for violations found.
        """
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as e:
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

        issues: list[ModelValidationIssue] = []

        # Get rule configurations from precomputed cache (O(1) lookups)
        default_severity = contract.severity_default or EnumSeverity.WARNING

        missing_config_enabled, missing_config_severity = self._get_rule_config(
            RULE_MISSING_CONFIG, contract
        )
        empty_config_enabled, empty_config_severity = self._get_rule_config(
            RULE_EMPTY_CONFIG, contract
        )
        frozen_enabled, frozen_severity = self._get_rule_config(
            RULE_FROZEN_WITHOUT_FROM_ATTRIBUTES, contract
        )
        contract_extra_enabled, contract_extra_severity = self._get_rule_config(
            RULE_CONTRACT_MISSING_EXTRA, contract
        )
        field_default_enabled, field_default_severity = self._get_rule_config(
            RULE_UNNECESSARY_FIELD_DEFAULT_NONE, contract
        )

        # Walk AST to find class definitions
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            # Check if this is a Pydantic model
            if not self._is_pydantic_model(node):
                continue

            # Skip known base models that don't need their own config
            if self._inherits_known_base(node):
                continue

            class_name = node.name
            class_line = node.lineno

            # Rule: missing-config
            if missing_config_enabled:
                if not self._has_model_config(node):
                    issues.append(
                        ModelValidationIssue(
                            severity=missing_config_severity or default_severity,
                            message=(
                                f"Class '{class_name}' inherits from BaseModel "
                                "but has no model_config"
                            ),
                            code=RULE_MISSING_CONFIG,
                            file_path=path,
                            line_number=class_line,
                            rule_name=RULE_MISSING_CONFIG,
                            suggestion=(
                                "Add `model_config = ConfigDict(...)` to class"
                            ),
                        )
                    )
                elif self._has_legacy_config_class(node):
                    config_line = self._get_legacy_config_line(node)
                    issues.append(
                        ModelValidationIssue(
                            severity=missing_config_severity or default_severity,
                            message=(
                                f"Class '{class_name}' uses legacy 'class Config:' "
                                "style (Pydantic v1)"
                            ),
                            code=RULE_MISSING_CONFIG,
                            file_path=path,
                            line_number=config_line or class_line,
                            rule_name=RULE_MISSING_CONFIG,
                            suggestion=(
                                "Replace 'class Config:' with "
                                "'model_config = ConfigDict(...)'"
                            ),
                        )
                    )

            # Get ConfigDict call for remaining checks
            config_call = self._get_config_dict_call(node)

            # Rule: empty-config
            if empty_config_enabled and config_call is not None:
                if self._is_empty_config_dict(config_call):
                    issues.append(
                        ModelValidationIssue(
                            severity=empty_config_severity or default_severity,
                            message=(
                                f"Class '{class_name}' has empty ConfigDict() "
                                "with no arguments"
                            ),
                            code=RULE_EMPTY_CONFIG,
                            file_path=path,
                            line_number=config_call.lineno,
                            rule_name=RULE_EMPTY_CONFIG,
                            suggestion=(
                                "Add at least one option to ConfigDict, "
                                'e.g., `extra="forbid"`'
                            ),
                        )
                    )

            # Rule: frozen-without-from-attributes
            if frozen_enabled and config_call is not None:
                if self._has_frozen_without_from_attributes(config_call):
                    issues.append(
                        ModelValidationIssue(
                            severity=frozen_severity or default_severity,
                            message=(
                                f"Class '{class_name}' has frozen=True without "
                                "from_attributes=True"
                            ),
                            code=RULE_FROZEN_WITHOUT_FROM_ATTRIBUTES,
                            file_path=path,
                            line_number=config_call.lineno,
                            rule_name=RULE_FROZEN_WITHOUT_FROM_ATTRIBUTES,
                            suggestion=(
                                "Add `from_attributes=True` when using `frozen=True`"
                            ),
                        )
                    )

            # Rule: contract-missing-extra
            if contract_extra_enabled and config_call is not None:
                if self._is_contract_model(path):
                    if self._config_missing_extra(config_call):
                        issues.append(
                            ModelValidationIssue(
                                severity=contract_extra_severity or default_severity,
                                message=(
                                    f"Contract model '{class_name}' has ConfigDict "
                                    "without explicit extra= policy"
                                ),
                                code=RULE_CONTRACT_MISSING_EXTRA,
                                file_path=path,
                                line_number=config_call.lineno,
                                rule_name=RULE_CONTRACT_MISSING_EXTRA,
                                suggestion=(
                                    "Add explicit `extra=` policy "
                                    '(e.g., `extra="forbid"`)'
                                ),
                            )
                        )

            # Rule: unnecessary-field-default-none
            if field_default_enabled:
                field_issues = self._find_unnecessary_field_defaults(node)
                for line_num, field_name in field_issues:
                    issues.append(
                        ModelValidationIssue(
                            severity=field_default_severity or default_severity,
                            message=(
                                f"Field '{field_name}' uses unnecessary "
                                "Field(default=None) with no other kwargs"
                            ),
                            code=RULE_UNNECESSARY_FIELD_DEFAULT_NONE,
                            file_path=path,
                            line_number=line_num,
                            rule_name=RULE_UNNECESSARY_FIELD_DEFAULT_NONE,
                            suggestion=(
                                f"Simplify to `{field_name}: Type | None = None`"
                            ),
                        )
                    )

        return tuple(issues)

    def _is_pydantic_model(self, node: ast.ClassDef) -> bool:
        """Check if class inherits from BaseModel.

        Looks for 'BaseModel' in the class's base classes. This is a
        simple string-based check that works for most common patterns.

        Args:
            node: AST ClassDef node to check.

        Returns:
            True if the class inherits from BaseModel, False otherwise.
        """
        for base in node.bases:
            base_name = self._get_name_from_node(base)
            if base_name == "BaseModel":
                return True
        return False

    def _inherits_known_base(self, node: ast.ClassDef) -> bool:
        """Check if class inherits from a known base model.

        Known base models provide their own model_config, so subclasses
        don't need to redeclare it.

        Args:
            node: AST ClassDef node to check.

        Returns:
            True if the class inherits from a known base model.
        """
        for base in node.bases:
            base_name = self._get_name_from_node(base)
            if base_name in KNOWN_BASE_MODELS:
                return True
        return False

    def _has_model_config(self, node: ast.ClassDef) -> bool:
        """Check if class has a model_config assignment.

        Looks for 'model_config = ...' in the class body.

        Args:
            node: AST ClassDef node to check.

        Returns:
            True if model_config is assigned, False otherwise.
        """
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "model_config":
                        return True
            elif isinstance(item, ast.AnnAssign):
                if isinstance(item.target, ast.Name):
                    if item.target.id == "model_config":
                        return True
        return False

    def _has_legacy_config_class(self, node: ast.ClassDef) -> bool:
        """Check if class has a legacy 'class Config:' inner class.

        This is the Pydantic v1 style that should be migrated to
        model_config = ConfigDict(...).

        Args:
            node: AST ClassDef node to check.

        Returns:
            True if a 'class Config:' inner class exists.
        """
        for item in node.body:
            if isinstance(item, ast.ClassDef) and item.name == "Config":
                return True
        return False

    def _get_legacy_config_line(self, node: ast.ClassDef) -> int | None:
        """Get the line number of the legacy Config class.

        Args:
            node: AST ClassDef node to check.

        Returns:
            Line number of 'class Config:', or None if not found.
        """
        for item in node.body:
            if isinstance(item, ast.ClassDef) and item.name == "Config":
                return item.lineno
        return None

    def _get_config_dict_call(self, node: ast.ClassDef) -> ast.Call | None:
        """Get the ConfigDict() call from model_config assignment.

        Looks for 'model_config = ConfigDict(...)' and returns the
        Call node for ConfigDict().

        Args:
            node: AST ClassDef node to check.

        Returns:
            The ast.Call node for ConfigDict(), or None if not found.
        """
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "model_config":
                        if isinstance(item.value, ast.Call):
                            func_name = self._get_name_from_node(item.value.func)
                            if func_name == "ConfigDict":
                                return item.value
            elif isinstance(item, ast.AnnAssign):
                if isinstance(item.target, ast.Name):
                    if item.target.id == "model_config" and item.value is not None:
                        if isinstance(item.value, ast.Call):
                            func_name = self._get_name_from_node(item.value.func)
                            if func_name == "ConfigDict":
                                return item.value
        return None

    def _is_empty_config_dict(self, call: ast.Call) -> bool:
        """Check if ConfigDict() call has no arguments.

        Args:
            call: AST Call node for ConfigDict().

        Returns:
            True if ConfigDict has no args and no kwargs.
        """
        return len(call.args) == 0 and len(call.keywords) == 0

    def _has_frozen_without_from_attributes(self, call: ast.Call) -> bool:
        """Check if ConfigDict has frozen=True without from_attributes=True.

        This combination causes issues with pytest-xdist where workers
        may have different class identities.

        Args:
            call: AST Call node for ConfigDict().

        Returns:
            True if frozen=True is present without from_attributes=True.
        """
        has_frozen = False
        has_from_attributes = False

        for keyword in call.keywords:
            if keyword.arg == "frozen":
                # Check if value is True
                if isinstance(keyword.value, ast.Constant):
                    has_frozen = keyword.value.value is True
            elif keyword.arg == "from_attributes":
                if isinstance(keyword.value, ast.Constant):
                    has_from_attributes = keyword.value.value is True

        return has_frozen and not has_from_attributes

    def _is_contract_model(self, path: Path) -> bool:
        """Check if file is in a contracts directory.

        Contract models require explicit extra= policy.

        Args:
            path: Path to the file.

        Returns:
            True if path contains '/models/contracts/' or '/contracts/'.
        """
        path_str = path.as_posix()
        return "/models/contracts/" in path_str or "/contracts/" in path_str

    def _config_missing_extra(self, call: ast.Call) -> bool:
        """Check if ConfigDict is missing an explicit extra= argument.

        Args:
            call: AST Call node for ConfigDict().

        Returns:
            True if 'extra' keyword is not present.
        """
        for keyword in call.keywords:
            if keyword.arg == "extra":
                return False
        return True

    def _find_unnecessary_field_defaults(
        self, node: ast.ClassDef
    ) -> list[tuple[int, str]]:
        """Find Field() calls with only default=None and no other kwargs.

        These patterns are unnecessary and can be simplified to
        `field_name: Type | None = None`.

        Args:
            node: AST ClassDef node to check.

        Returns:
            List of (line_number, field_name) tuples for violations.
        """
        issues: list[tuple[int, str]] = []

        for item in node.body:
            if not isinstance(item, ast.AnnAssign):
                continue

            # Get field name
            if not isinstance(item.target, ast.Name):
                continue
            field_name = item.target.id

            # Check if value is a Field() call
            if item.value is None:
                continue
            if not isinstance(item.value, ast.Call):
                continue

            func_name = self._get_name_from_node(item.value.func)
            if func_name != "Field":
                continue

            call = item.value

            # Check for Field(None) - single positional arg that is None
            if len(call.args) == 1 and len(call.keywords) == 0:
                if isinstance(call.args[0], ast.Constant):
                    if call.args[0].value is None:
                        issues.append((item.lineno, field_name))
                        continue

            # Check for Field(default=None) with no other kwargs
            if len(call.args) == 0 and len(call.keywords) == 1:
                kw = call.keywords[0]
                if kw.arg == "default":
                    if isinstance(kw.value, ast.Constant):
                        if kw.value.value is None:
                            issues.append((item.lineno, field_name))

        return issues

    def _get_name_from_node(self, node: ast.expr) -> str | None:
        """Extract name string from AST node.

        Handles Name nodes and Attribute nodes (e.g., pydantic.BaseModel).

        Args:
            node: AST expression node.

        Returns:
            The name string, or None if cannot be extracted.
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return None


# CLI entry point
if __name__ == "__main__":
    raise SystemExit(  # error-ok: CLI exit code pattern
        ValidatorPydanticConventions.main()
    )


__all__ = [
    "KNOWN_BASE_MODELS",
    "RULE_CONTRACT_MISSING_EXTRA",
    "RULE_EMPTY_CONFIG",
    "RULE_FROZEN_WITHOUT_FROM_ATTRIBUTES",
    "RULE_MISSING_CONFIG",
    "RULE_UNNECESSARY_FIELD_DEFAULT_NONE",
    "ValidatorPydanticConventions",
]
