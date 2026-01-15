#!/usr/bin/env python3
"""Naming convention validation for omni* ecosystem.

This script validates that Python classes follow the ONEX naming conventions
across the codebase. It enforces consistent naming patterns for:

- Models: Must start with 'Model' (e.g., ModelUserAuth)
- Protocols: Must start with 'Protocol' (e.g., ProtocolEventBus)
- Enums: Must start with 'Enum' (e.g., EnumWorkflowType)
- Services: Must start with 'Service' (e.g., ServiceAuth)
- Mixins: Must start with 'Mixin' (e.g., MixinHealthCheck)
- Nodes: Must start with 'Node' (e.g., NodeEffectUserData)
- TypedDicts: Must start with 'TypedDict' (e.g., TypedDictUserParams)

Usage:
    poetry run python scripts/validation/validate_naming.py /path/to/repo
    poetry run python scripts/validation/validate_naming.py . --verbose
    poetry run python scripts/validation/validate_naming.py . --fail-on-warnings

Examples:
    # Validate current repository
    poetry run python scripts/validation/validate_naming.py .

    # Validate with verbose output
    poetry run python scripts/validation/validate_naming.py . -v

    # Fail on warnings (for CI)
    poetry run python scripts/validation/validate_naming.py . --fail-on-warnings

Exit Codes:
    0 - All naming conventions are compliant
    1 - Naming violations detected (errors, or warnings with --fail-on-warnings)
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class NamingViolation:
    """Represents a single naming convention violation.

    Attributes:
        file_path: Absolute path to the file containing the violation.
        line_number: Line number where the violation occurs.
        class_name: Name of the class that violates the convention.
        expected_pattern: The regex pattern or description of expected naming.
        description: Human-readable description of the naming rule.
        severity: Violation severity ('error' or 'warning').
    """

    file_path: str
    line_number: int
    class_name: str
    expected_pattern: str
    description: str
    severity: str = "error"


class NamingConventionValidator:
    """Validates naming conventions across Python codebase."""

    NAMING_PATTERNS: dict[str, dict[str, str | None]] = {
        "models": {
            "pattern": r"^Model[A-Z][A-Za-z0-9]*$",
            "file_prefix": "model_",
            "description": "Models must start with 'Model' (e.g., ModelUserAuth)",
            "directory": "models",
        },
        "protocols": {
            "pattern": r"^Protocol[A-Z][A-Za-z0-9]*$",
            "file_prefix": "protocol_",
            "description": "Protocols must start with 'Protocol' (e.g., ProtocolEventBus)",
            "directory": "protocol",
        },
        "enums": {
            "pattern": r"^Enum[A-Z][A-Za-z0-9]*$",
            "file_prefix": "enum_",
            "description": "Enums must start with 'Enum' (e.g., EnumWorkflowType)",
            "directory": "enums",
        },
        "services": {
            "pattern": r"^Service[A-Z][A-Za-z0-9]*$",
            "file_prefix": "service_",
            "description": "Services must start with 'Service' (e.g., ServiceAuth)",
            "directory": "services",
        },
        "mixins": {
            "pattern": r"^Mixin[A-Z][A-Za-z0-9]*$",
            "file_prefix": "mixin_",
            "description": "Mixins must start with 'Mixin' (e.g., MixinHealthCheck)",
            "directory": "mixins",
        },
        "nodes": {
            "pattern": r"^Node[A-Z][A-Za-z0-9]*$",
            "file_prefix": "node_",
            "description": "Nodes must start with 'Node' (e.g., NodeEffectUserData)",
            "directory": "nodes",
        },
        "typeddicts": {
            "pattern": r"^TypedDict[A-Z][A-Za-z0-9]*$",
            "file_prefix": None,  # TypedDict can be in any file
            "description": "TypedDict classes must start with 'TypedDict' (e.g., TypedDictUserParams)",
            "directory": None,  # TypedDict can be in any directory
        },
    }

    # Exception patterns - classes that don't need to follow strict naming
    EXCEPTION_PATTERNS = [
        r"^_.*",  # Private classes
        r"^Checker.*",  # Checker/validator utility classes (e.g., CheckerEnumMemberCasing)
        r".*Test$",  # Test classes
        r".*TestCase$",  # Test case classes
        r"^Test.*",  # Test classes
        r"^Exception[A-Z].*",  # Exception classes (omnibase pattern - start with Exception)
        r".*Error$",  # Exception classes (end with Error)
        r".*Exception$",  # Exception classes (end with Exception)
    ]

    # Architectural exemptions - intentional design decisions where naming deviates from standard conventions
    # These are documented, justified architectural patterns that serve specific purposes
    ARCHITECTURAL_EXEMPTIONS = {
        # INFRASTRUCTURE BASE CLASSES: Abstract base classes (archetypes, not implementations)
        # Location: infrastructure/ - Core infrastructure patterns
        # Rationale: NodeBase and NodeCoreBase are abstract archetypes, not concrete node implementations
        #            Concrete nodes (NodeComputeCache, NodeEffectAuth, etc.) live in nodes/ and follow Node* naming
        "infrastructure/": [
            "NodeBase",  # Abstract base for all nodes
            "NodeCoreBase",  # Abstract core base with DI support
        ],
        # CONTAINER INFRASTRUCTURE: Service registry and DI infrastructure
        # Location: container/ - Dependency injection infrastructure
        # Rationale: ServiceRegistry is infrastructure, not a domain service implementation
        "container/": [
            "ServiceRegistry",  # DI service registry infrastructure
        ],
        # VALIDATION UTILITY CLASSES: Data classes and utilities for validation framework
        # Location: models/validation/ - Validation-specific utility classes
        # Rationale: These are utility/data classes (dataclass, not Pydantic), not business models
        #            They support validation infrastructure and don't need Model* prefix
        "models/validation/": [
            "DuplicationInfo",  # Dataclass for duplication tracking
            "ProtocolSignatureExtractor",  # AST visitor for protocol extraction
            "ValidationResult",  # Dataclass for validation results
        ],
        # MIXIN DATA CLASSES: Data classes stored in models/mixins
        # Location: models/mixins/ - Mixin-related data structures
        # Rationale: Dataclass for service registry, follows Mixin* naming appropriate to its purpose
        "models/mixins/": [
            "MixinServiceRegistryEntry",  # Dataclass for service registry entries
        ],
        # CONTRACT INFRASTRUCTURE: Contract utilities and registries
        # Location: contracts/ - Contract management infrastructure
        # Rationale: These are stateful service/utility classes for contract management,
        #            not Protocols or Models. Similar to ServiceRegistry in container/.
        "contracts/": [
            "ContractHashRegistry",  # Registry service for contract hash management
            "ContractDiffComputer",  # Utility class for computing contract diffs (OMN-1148)
        ],
        # REPLAY INFRASTRUCTURE: Replay executor and session for deterministic replay
        # Location: pipeline/replay/ - Replay infrastructure utilities
        # Rationale: ExecutorReplay and ReplaySession are replay infrastructure classes.
        #            They coordinate replay execution, not Node implementations.
        #            Note: ServiceEffectRecorder is now in services/replay/ (OMN-1298)
        "pipeline/replay/": [
            # ExecutorReplay, ReplaySession - no exemptions needed (correct naming)
        ],
        # HANDLER INFRASTRUCTURE: Handler implementations for ONEX runtime and pipeline
        # Location: runtime/handlers/ and pipeline/handlers/ - Handler implementations
        # Rationale: Handlers implement ProtocolHandler and use Handler* prefix (e.g., HandlerLocal, HandlerHttp)
        #            They are not "Services" in the ONEX architecture but runtime execution units.
        #            Pipeline handlers (HandlerCapabilityCaching, HandlerCapabilityMetrics) provide
        #            reusable pipeline capabilities following the same Handler* naming pattern.
        "runtime/handlers/": [
            "Handler*",  # All Handler* classes in handlers/ directory
        ],
        "pipeline/handlers/": [
            "Handler*",  # All Handler* classes (HandlerCapabilityCaching, HandlerCapabilityMetrics)
        ],
        # UTILITY CLASSES: Utility/helper classes in utils/
        # Location: utils/ - Utility functions and helper classes
        # Rationale: Utility classes use Util* prefix (e.g., UtilContractLoader, UtilSecurity)
        #            These are helper classes, not Protocols, even if they have "contract" in the name.
        #            The heuristic flags "contract" as a Protocol indicator, but UtilContractLoader
        #            is a utility that LOADS contracts, not a Protocol interface.
        "utils/": [
            "Util*",  # All Util* classes in utils/ directory
        ],
        # FACTORY CLASSES: Contract profile factory for creating default contracts
        # Location: factories/ - Factory pattern implementations
        # Rationale: ContractProfileFactory creates contract profiles, not a Protocol interface.
        #            The heuristic flags "contract" as a Protocol indicator, but this is a factory
        #            that PRODUCES contracts, not a Protocol interface.
        "factories/": [
            "ContractProfileFactory",  # Factory for creating default contract profiles
        ],
        # VALIDATION INFRASTRUCTURE: Validators and checkers for ONEX contracts and workflows
        # Location: validation/ - Validation framework implementations
        # Rationale: ContractPatchValidator validates contract patches, not a Protocol interface.
        #            The heuristic flags "contract" as a Protocol indicator, but this is a
        #            validator that VALIDATES patches, not a Protocol interface.
        #            The Protocol interface for this is ProtocolPatchValidator in validator_protocol_patch.py
        #            ContractValidationInvariantChecker is a concrete implementation (OMN-1146),
        #            not a Protocol. The Protocol interface is ProtocolContractValidationInvariantChecker.
        #            Validator* classes (ValidatorAnyType, ValidatorContractLinter, etc.) are
        #            concrete validator implementations in the validation framework (OMN-1291).
        #            *Visitor classes (AnyTypeVisitor, etc.) are AST visitors for code analysis.
        #            The heuristics flag "type" as Enum indicator and "contract" as Protocol
        #            indicator, but these are validation infrastructure classes.
        "validation/": [
            "ContractPatchValidator",  # Validator for contract patches (OMN-1126)
            "ContractValidationInvariantChecker",  # Invariant checker implementation (OMN-1146)
            "ContractValidationPipeline",  # Validation pipeline orchestrator (OMN-1128)
            "ExpandedContractValidator",  # Expanded contract validator (OMN-1128)
            "ExpandedContractGraphValidator",  # Multi-contract graph validator (OMN-1128)
            "MergeValidator",  # Merge phase validator (OMN-1128)
            "Validator*",  # All Validator* classes (ValidatorAnyType, ValidatorContractLinter, etc.) (OMN-1291)
            "Checker*",  # All Checker* classes (CheckerEnumMemberCasing, etc.) for AST analysis (OMN-1311)
            "*Visitor",  # All *Visitor classes (AnyTypeVisitor, etc.) for AST analysis (OMN-1291)
            "Checker*",  # All Checker* classes (CheckerEnumMemberCasing, etc.) for code analysis (OMN-1308)
        ],
        # MERGE INFRASTRUCTURE: Contract merge engine for typed contract merging
        # Location: merge/ - Contract merge framework implementations
        # Rationale: ContractMergeEngine merges contract patches with base profiles (OMN-1127).
        #            The heuristic flags "contract" as a Protocol indicator, but this is a
        #            merge engine implementation, not a Protocol interface.
        #            The Protocol interface is ProtocolMergeEngine in protocols/merge/.
        "merge/": [
            "ContractMergeEngine",  # Merge engine for typed contract merging (OMN-1127)
        ],
        # REPLAY INFRASTRUCTURE: Deterministic replay utilities for testing and debugging
        # Location: services/replay/ - Replay infrastructure services (injectors/recorders)
        # Rationale: These classes provide deterministic replay capabilities (OMN-1116, OMN-1205).
        #            ServiceEffectRecorder, ServiceTimeInjector, ServiceRNGInjector follow the
        #            Service* prefix convention and no longer require exemptions.
        #            Note: Empty list kept for documentation purposes.
        "services/replay/": [
            # No exemptions needed - all classes now use Service* prefix (OMN-1298)
        ],
        # Note: Duplicate "pipeline/replay/" entry removed - consolidated above (OMN-1298)
        # ExecutorReplay and ReplaySession follow correct naming patterns and don't need exemptions.
    }

    @staticmethod
    def _matches_architectural_exemption(class_name: str, file_path: Path) -> bool:
        """Check if a class matches documented architectural exemptions.

        Architectural exemptions are intentional design decisions where classes
        are placed outside their typical naming convention directory for valid
        architectural reasons (e.g., utilities, primitives, infrastructure).

        Args:
            class_name: Name of the class to check.
            file_path: Path to the file containing the class.

        Returns:
            True if class is architecturally exempt from standard naming rules.
        """
        for (
            directory,
            exempted_patterns,
        ) in NamingConventionValidator.ARCHITECTURAL_EXEMPTIONS.items():
            # Check if file is in the exempted directory
            if directory not in str(file_path):
                continue

            # Check if class matches any exempted pattern
            for pattern in exempted_patterns:
                if pattern.endswith("*"):
                    # Prefix wildcard pattern (e.g., "Model*")
                    prefix = pattern[:-1]
                    if class_name.startswith(prefix):
                        return True
                elif pattern.startswith("*"):
                    # Suffix wildcard pattern (e.g., "*Visitor")
                    suffix = pattern[1:]
                    if class_name.endswith(suffix):
                        return True
                elif class_name == pattern:
                    # Exact match
                    return True

        return False

    def __init__(self, repo_path: Path) -> None:
        """Initialize the naming convention validator.

        Args:
            repo_path: Path to the repository root directory to validate.
        """
        self.repo_path = repo_path
        self.violations: list[NamingViolation] = []

    def validate_naming_conventions(self) -> bool:
        """Validate all naming conventions across the repository.

        Scans the repository for Python files and validates that class names
        follow the ONEX naming conventions based on their category and location.

        Returns:
            True if no errors were found, False otherwise.
        """
        for category, rules in self.NAMING_PATTERNS.items():
            self._validate_category_files(category, rules)

        return len([v for v in self.violations if v.severity == "error"]) == 0

    def _validate_category_files(
        self, category: str, rules: dict[str, str | None]
    ) -> None:
        """Validate naming conventions for a specific category.

        Args:
            category: The category to validate (e.g., 'models', 'enums').
            rules: Dictionary containing validation rules including:
                - pattern: Regex pattern for valid class names
                - file_prefix: Expected file name prefix
                - description: Human-readable rule description
                - directory: Expected directory for this category
        """
        # Special handling for TypedDict - scan all Python files
        if category == "typeddicts":
            for file_path in self.repo_path.rglob("*.py"):
                if "__pycache__" in str(file_path) or "/archived/" in str(file_path):
                    continue
                self._validate_typeddict_in_file(file_path, category, rules)
            return

        # Find all files matching the prefix pattern
        file_prefix = rules["file_prefix"]
        if file_prefix:
            for file_path in self.repo_path.rglob(f"{file_prefix}*.py"):
                # Skip __pycache__, archived directories, and similar
                if "__pycache__" in str(file_path) or "/archived/" in str(file_path):
                    continue

                self._validate_file_naming(file_path, category, rules)

        # Also check files in the expected directory structure
        directory = rules["directory"]
        if not directory:
            return
        for file_path in self.repo_path.rglob(f"*/{directory}/*.py"):
            if file_path.name == "__init__.py":
                continue
            if "__pycache__" in str(file_path) or "/archived/" in str(file_path):
                continue

            # CRITICAL FIX: Files in /models/ directories should follow Model naming rules,
            # not the naming rules for their subdirectory name
            if "/models/" in str(file_path) and category != "models":
                continue

            # CRITICAL FIX: Files in /enums/ directories should follow Enum naming rules,
            # not the naming rules for their subdirectory name
            if "/enums/" in str(file_path) and category != "enums":
                continue

            self._validate_file_naming(file_path, category, rules)

        # Also scan all Python files to catch violations regardless of file location
        # This enables detection of violations in test fixtures and misplaced files
        for file_path in self.repo_path.rglob("*.py"):
            if file_path.name == "__init__.py":
                continue
            if "__pycache__" in str(file_path) or "/archived/" in str(file_path):
                continue

            # Skip files we've already processed to avoid duplicate violations
            file_prefix = rules["file_prefix"]
            already_processed = (
                file_prefix and file_path.name.startswith(file_prefix)
            ) or (directory and directory in str(file_path))
            if not already_processed:
                self._validate_all_classes_in_file(file_path, category, rules)

    def _validate_file_naming(
        self, file_path: Path, category: str, rules: dict[str, str | None]
    ) -> None:
        """Validate naming conventions in a specific file.

        Parses the Python file and checks all class definitions against
        the naming conventions for the specified category.

        Args:
            file_path: Path to the Python file to validate.
            category: The category being validated.
            rules: Dictionary containing validation rules.
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Check if file name follows convention
            expected_prefix = rules["file_prefix"]
            pattern = rules["pattern"]
            if (
                expected_prefix
                and not file_path.name.startswith(expected_prefix)
                and file_path.name != "__init__.py"
            ):
                # Only flag this for files that contain classes matching the pattern
                if pattern and self._contains_relevant_classes(content, pattern):
                    self.violations.append(
                        NamingViolation(
                            file_path=str(file_path),
                            line_number=1,
                            class_name="(file name)",
                            expected_pattern=f"{expected_prefix}*.py",
                            description=f"File containing {category} should be named '{expected_prefix}*.py'",
                            severity="warning",
                        )
                    )

            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self._check_class_naming(file_path, node, category, rules)

        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"Warning: Could not parse {file_path}: {e}")

    def _validate_typeddict_in_file(
        self, file_path: Path, category: str, rules: dict[str, str | None]
    ) -> None:
        """Validate TypedDict classes in any file.

        TypedDict classes can appear in any Python file, so this method
        scans all files for TypedDict subclasses and validates their naming.

        Args:
            file_path: Path to the Python file to validate.
            category: The category being validated (should be 'typeddicts').
            rules: Dictionary containing validation rules.
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if this is a TypedDict class
                    if self._is_typeddict_class(node):
                        self._check_class_naming(file_path, node, category, rules)

        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"Warning: Could not parse {file_path}: {e}")

    def _validate_all_classes_in_file(
        self, file_path: Path, category: str, rules: dict[str, str | None]
    ) -> None:
        """Validate classes in any file that should match the category pattern.

        Scans files that haven't been processed by category-specific validation
        to catch misplaced classes or violations in unexpected locations.

        Args:
            file_path: Path to the Python file to validate.
            category: The category being validated.
            rules: Dictionary containing validation rules.
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Only check classes that should match this category's pattern
                    # AND don't already match any other valid pattern
                    if self._should_match_pattern(
                        node.name, category
                    ) and not self._matches_any_valid_pattern(node.name):
                        self._check_class_naming(file_path, node, category, rules)

        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"Warning: Could not parse {file_path}: {e}")

    def _is_typeddict_class(self, node: ast.ClassDef) -> bool:
        """Check if a class definition inherits from TypedDict.

        Args:
            node: AST class definition node to check.

        Returns:
            True if the class inherits from TypedDict.
        """
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "TypedDict":
                return True
            # Handle cases like typing.TypedDict
            if isinstance(base, ast.Attribute) and base.attr == "TypedDict":
                return True
        return False

    def _is_basemodel_class(self, node: ast.ClassDef) -> bool:
        """Check if a class definition inherits from Pydantic BaseModel.

        Args:
            node: AST class definition node to check.

        Returns:
            True if the class inherits from Pydantic BaseModel.
        """
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "BaseModel":
                return True
            # Handle cases like pydantic.BaseModel
            if isinstance(base, ast.Attribute) and base.attr == "BaseModel":
                return True
        return False

    def _is_enum_class(self, node: ast.ClassDef) -> bool:
        """Check if a class definition inherits from Enum.

        Args:
            node: AST class definition node to check.

        Returns:
            True if the class inherits from Enum.
        """
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "Enum":
                return True
            # Handle cases like enum.Enum
            if isinstance(base, ast.Attribute) and base.attr == "Enum":
                return True
        return False

    def _is_protocol_class(self, node: ast.ClassDef) -> bool:
        """Check if a class definition inherits from Protocol.

        Args:
            node: AST class definition node to check.

        Returns:
            True if the class inherits from Protocol.
        """
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "Protocol":
                return True
            # Handle cases like typing.Protocol
            if isinstance(base, ast.Attribute) and base.attr == "Protocol":
                return True
        return False

    def _contains_relevant_classes(self, content: str, pattern: str) -> bool:
        """Check if file contains classes that should match the pattern.

        Args:
            content: Python source code content.
            pattern: Regex pattern to check against.

        Returns:
            True if file contains classes that should follow the pattern.
        """
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if class should follow the pattern
                    if not self._is_exception_class(node.name):
                        # If it looks like it should match but doesn't, file naming is relevant
                        return True
        except Exception:
            pass
        return False

    def _check_class_naming(
        self,
        file_path: Path,
        node: ast.ClassDef,
        category: str,
        rules: dict[str, str | None],
    ) -> None:
        """Check if class name follows conventions.

        Validates the class name against the category's naming pattern and
        adds violations to the violations list if rules are not followed.

        Args:
            file_path: Path to the file containing the class.
            node: AST class definition node.
            category: The category being validated.
            rules: Dictionary containing validation rules.
        """
        class_name = node.name
        pattern = rules["pattern"]
        description = rules["description"]

        # Skip if no pattern defined
        if not pattern:
            return

        # Skip exception patterns
        if self._is_exception_class(class_name):
            return

        # Skip TypedDict classes when validating other categories
        # They should only be validated in the typeddicts category
        if category != "typeddicts" and self._is_typeddict_class(node):
            return

        # Skip BaseModel classes when validating nodes category
        # BaseModel subclasses are data models and should use "Model" prefix
        # even if they're located in infrastructure/ alongside node classes
        if category == "nodes" and self._is_basemodel_class(node):
            return

        # Skip Model* prefixed classes when validating nodes category
        # Per ONEX standards: "only nodes need node prefixes, otherwise they are models"
        # Helper models in nodes/ directory (ModelEffectTransaction, ModelLoadBalancer, etc.)
        # are correctly named with Model* prefix and should not be required to use Node* prefix
        if category == "nodes" and class_name.startswith("Model"):
            return

        # Skip Enum classes when validating non-enum categories
        # Enum classes should only be validated in the enums category
        if category != "enums" and self._is_enum_class(node):
            return

        # Skip Protocol classes when validating non-protocol categories
        # Protocol classes should only be validated in the protocols category
        if category != "protocols" and self._is_protocol_class(node):
            return

        # Check if this file is in the right directory for this category
        expected_dir = rules["directory"]

        # Check architectural exemptions FIRST - these override standard directory rules
        if self._matches_architectural_exemption(class_name, file_path):
            # This class is architecturally exempt - skip all directory validation
            return

        # Special handling for Model* classes - allow in models/, infrastructure/, and container/
        # These directories can contain Model* classes that are not Pydantic data models:
        # - models/: Primary location for Pydantic data models
        # - infrastructure/: Infrastructure classes (ModelCircuitBreaker, ModelComputeCache, etc.)
        # - container/: DI container classes (ModelONEXContainer)
        if category == "models" and class_name.startswith("Model"):
            ALLOWED_MODEL_DIRECTORIES = ["models/", "infrastructure/", "container/"]
            in_correct_directory = any(
                allowed_dir in str(file_path)
                for allowed_dir in ALLOWED_MODEL_DIRECTORIES
            )
        else:
            in_correct_directory = expected_dir is None or expected_dir in str(
                file_path
            )

        # If class matches pattern but file is in wrong place
        if re.match(pattern, class_name) and not in_correct_directory:
            self.violations.append(
                NamingViolation(
                    file_path=str(file_path),
                    line_number=node.lineno,
                    class_name=class_name,
                    expected_pattern=f"Should be in /{expected_dir}/ directory",
                    description=f"{class_name} should be in {expected_dir}/ directory",
                    severity="warning",
                )
            )

        # If class doesn't match pattern but seems like it should
        elif not re.match(pattern, class_name) and (
            self._should_match_pattern(class_name, category)
            or self._is_in_category_directory(file_path, expected_dir)
        ):
            self.violations.append(
                NamingViolation(
                    file_path=str(file_path),
                    line_number=node.lineno,
                    class_name=class_name,
                    expected_pattern=pattern,
                    description=description
                    or f"Must follow {category} naming conventions",
                    severity="error",
                )
            )

    def _is_exception_class(self, class_name: str) -> bool:
        """Check if class name matches exception patterns.

        Exception patterns include private classes, test classes, and
        exception/error classes that don't need to follow standard naming.

        Args:
            class_name: Name of the class to check.

        Returns:
            True if class matches an exception pattern.
        """
        return any(re.match(pattern, class_name) for pattern in self.EXCEPTION_PATTERNS)

    def _is_in_category_directory(
        self, file_path: Path, expected_dir: str | None
    ) -> bool:
        """Check if file is in the expected category directory.

        Args:
            file_path: Path to the file to check.
            expected_dir: Expected directory name for the category.

        Returns:
            True if file is in the expected directory.
        """
        if expected_dir is None:
            return False
        return expected_dir in str(file_path)

    def _should_match_pattern(self, class_name: str, category: str) -> bool:
        """Determine if a class should match the pattern for a category.

        Uses heuristics based on keywords in the class name to determine
        if it should follow the naming conventions for a specific category.

        Args:
            class_name: Name of the class to check.
            category: The category to check against.

        Returns:
            True if the class name suggests it should follow the category's pattern.
        """
        # Heuristics to determine if a class should follow naming conventions

        category_indicators = {
            "models": ["model", "data", "schema", "entity"],
            "protocols": ["protocol", "interface", "contract"],
            "enums": ["enum", "choice", "status", "type", "kind"],
            "services": ["service", "manager", "handler", "processor"],
            "mixins": ["mixin", "mix"],
            "nodes": ["node", "effect", "compute", "reducer", "orchestrator"],
            "typeddicts": ["params", "kwargs", "dict", "config", "options"],
        }

        indicators = category_indicators.get(category, [])
        class_lower = class_name.lower()

        # Check if class name contains category indicators
        return any(indicator in class_lower for indicator in indicators)

    def _matches_any_valid_pattern(self, class_name: str) -> bool:
        """Check if a class name matches any valid naming pattern.

        Args:
            class_name: Name of the class to check.

        Returns:
            True if class name matches any of the defined naming patterns.
        """
        for category, rules in self.NAMING_PATTERNS.items():
            pattern = rules["pattern"]
            if pattern and re.match(pattern, class_name):
                return True
        return False

    def generate_report(self) -> str:
        """Generate naming convention validation report.

        Creates a human-readable report of all violations found during
        validation, grouped by severity (errors and warnings).

        Returns:
            Formatted string report with violation details and naming reference.
        """
        if not self.violations:
            return "✅ All naming conventions are compliant!"

        errors = [v for v in self.violations if v.severity == "error"]
        warnings = [v for v in self.violations if v.severity == "warning"]

        report = "🚨 Naming Convention Validation Report\n"
        report += "=" * 40 + "\n\n"

        report += f"Summary: {len(errors)} errors, {len(warnings)} warnings\n\n"

        if errors:
            report += "🔴 NAMING ERRORS (Must Fix):\n"
            report += "=" * 30 + "\n"
            for violation in errors:
                report += f"🔴 {violation.class_name} (Line {violation.line_number})\n"
                report += f"   File: {violation.file_path}\n"
                report += f"   Expected Pattern: {violation.expected_pattern}\n"
                report += f"   Rule: {violation.description}\n\n"

        if warnings:
            report += "🟡 NAMING WARNINGS (Should Fix):\n"
            report += "=" * 32 + "\n"
            for violation in warnings:
                report += f"🟡 {violation.class_name} (Line {violation.line_number})\n"
                report += f"   File: {violation.file_path}\n"
                report += f"   Issue: {violation.description}\n\n"

        # Add quick reference
        report += "📚 NAMING CONVENTION REFERENCE:\n"
        report += "=" * 33 + "\n"
        for category, rules in self.NAMING_PATTERNS.items():
            description = (
                rules["description"] or f"{category.title()} naming convention"
            )
            file_prefix = rules["file_prefix"]
            pattern = rules["pattern"] or "N/A"
            report += f"• {category.title()}: {description}\n"
            if file_prefix:
                report += f"  File Pattern: {file_prefix}*.py\n"
            else:
                report += "  File Pattern: Any .py file\n"
            report += f"  Class Pattern: {pattern}\n\n"

        return report


def main() -> int:
    """Main entry point for the naming convention validator.

    Parses command line arguments, runs validation, and prints the report.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    parser = argparse.ArgumentParser(description="Validate omni* naming conventions")
    parser.add_argument("repo_path", help="Path to repository root")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="Exit with error code if warnings are found (in addition to errors)",
    )

    args = parser.parse_args()

    repo_path = Path(args.repo_path).resolve()
    if not repo_path.exists():
        print(f"Error: Repository path does not exist: {repo_path}")
        sys.exit(1)

    validator = NamingConventionValidator(repo_path)
    is_valid = validator.validate_naming_conventions()

    print(validator.generate_report())

    errors = len([v for v in validator.violations if v.severity == "error"])
    warnings = len([v for v in validator.violations if v.severity == "warning"])

    # Exit with error if we have errors, or if we have warnings and --fail-on-warnings is set
    has_failures = errors > 0 or (args.fail_on_warnings and warnings > 0)

    if not has_failures:
        print("\n✅ SUCCESS: All naming conventions are compliant!")
        sys.exit(0)
    else:
        if args.fail_on_warnings and warnings > 0:
            print(
                f"\n❌ FAILURE: {errors} error(s) and {warnings} warning(s) must be fixed!"
            )
            print("   (--fail-on-warnings flag is set)")
        else:
            print(f"\n❌ FAILURE: {errors} naming violations must be fixed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
