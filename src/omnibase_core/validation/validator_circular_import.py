"""
Circular Import Validator

Validates Python modules for circular import issues.
Can be used as a standalone validator or integrated into other tools.
"""

import importlib
import sys
from collections.abc import Callable
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_import_status import EnumImportStatus
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.validation.model_import_validation_result import (
    ModelImportValidationResult,
)
from omnibase_core.models.validation.model_module_import_result import (
    ModelModuleImportResult,
)


class CircularImportValidator:
    """
    Validator for detecting circular imports in Python codebases.

    Scans Python files, attempts to import them, and detects circular
    import issues along with other import errors.

    Example:
        >>> validator = CircularImportValidator(source_path="/path/to/src")
        >>> result = validator.validate()
        >>> if result.has_circular_imports:
        ...     print(f"Found {len(result.circular_imports)} circular imports")
    """

    def __init__(
        self,
        source_path: str | Path,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        verbose: bool = False,
        progress_callback: Callable[[str], None] | None = None,
    ):
        """
        Initialize the circular import validator.

        Args:
            source_path: Root path containing Python modules to validate
            include_patterns: Optional list of glob patterns to include (e.g., ["*.py"])
            exclude_patterns: Optional list of patterns to exclude (e.g., ["*test*.py", "__pycache__"])
            verbose: If True, print detailed progress information
            progress_callback: Optional callback function for progress updates
        """
        self.source_path = Path(source_path)
        self.include_patterns = include_patterns or ["*.py"]
        self.exclude_patterns = exclude_patterns or ["__pycache__", "archived"]
        self.verbose = verbose
        self.progress_callback = progress_callback

        if not self.source_path.exists():
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Source path does not exist: {self.source_path}",
            )

    def _should_exclude(self, file_path: Path) -> bool:
        """Check if a file should be excluded based on exclude patterns."""
        file_str = str(file_path)
        return any(pattern in file_str for pattern in self.exclude_patterns)

    def _discover_python_files(self) -> list[Path]:
        """
        Discover all Python files in the source path.

        Returns:
            List of Python file paths to validate
        """
        python_files = []

        for pattern in self.include_patterns:
            for file_path in self.source_path.rglob(pattern):
                if not self._should_exclude(file_path):
                    python_files.append(file_path)

        return python_files

    def _path_to_module_name(self, file_path: Path) -> str | None:
        """
        Convert a file path to a Python module name.

        Args:
            file_path: Path to the Python file

        Returns:
            Module name (e.g., "omnibase_core.validation.validator_circular_import")
            or None if the path cannot be converted
        """
        try:
            relative_path = file_path.relative_to(self.source_path)
            # Use removesuffix to only remove .py from the end, not from the middle of the path
            # This prevents "logging/pydantic" from becoming "loggingdantic" after "/" -> "." replacement
            module_name = str(relative_path).replace("/", ".").removesuffix(".py")

            # Handle __init__.py files
            if module_name.endswith(".__init__"):
                module_name = module_name[:-9]  # Remove .__init__

            # Skip if module name is empty or just __init__
            if not module_name or module_name == "__init__":
                return None

            return module_name

        except ValueError:
            return None

    def _test_import(
        self, module_name: str, file_path: Path
    ) -> ModelModuleImportResult:
        """
        Test importing a single module.

        Args:
            module_name: Name of the module to import
            file_path: Path to the module file

        Returns:
            ModelModuleImportResult with the import attempt status and details
        """
        try:
            # Clear any previously imported modules to get a fresh test
            if module_name in sys.modules:
                del sys.modules[module_name]

            # Attempt to import
            importlib.import_module(module_name)

            return ModelModuleImportResult(
                module_name=module_name,
                status=EnumImportStatus.SUCCESS,
                file_path=str(file_path),
            )

        except ImportError as e:
            error_msg = str(e)
            # Check if it's a circular import
            if "circular import" in error_msg.lower():
                return ModelModuleImportResult(
                    module_name=module_name,
                    status=EnumImportStatus.CIRCULAR_IMPORT,
                    error_message=error_msg,
                    file_path=str(file_path),
                )
            else:
                # Other import errors (missing dependencies, etc.)
                return ModelModuleImportResult(
                    module_name=module_name,
                    status=EnumImportStatus.IMPORT_ERROR,
                    error_message=error_msg,
                    file_path=str(file_path),
                )

        except Exception as e:  # fallback-ok: Import testing requires catching all exceptions to classify import failures
            # Unexpected errors
            return ModelModuleImportResult(
                module_name=module_name,
                status=EnumImportStatus.UNEXPECTED_ERROR,
                error_message=repr(e),
                file_path=str(file_path),
            )

    def _log(self, message: str) -> None:
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    def _notify_progress(self, message: str) -> None:
        """Notify progress via callback if provided."""
        if self.progress_callback:
            self.progress_callback(message)

    def validate(self) -> ModelImportValidationResult:
        """
        Validate all Python modules for circular imports.

        Returns:
            ModelImportValidationResult containing detailed results of the validation

        Example:
            >>> validator = CircularImportValidator("/path/to/src")
            >>> result = validator.validate()
            >>> print(f"Success rate: {result.success_rate:.1f}%")
        """
        # Discover Python files
        python_files = self._discover_python_files()
        self._log(f"Found {len(python_files)} Python files to test")
        self._log("=" * 80)

        # Initialize result
        result = ModelImportValidationResult(total_files=len(python_files))

        # Test each file
        for file_path in python_files:
            module_name = self._path_to_module_name(file_path)

            if module_name is None:
                # Skip this file
                skip_result = ModelModuleImportResult(
                    module_name=str(file_path),
                    status=EnumImportStatus.SKIPPED,
                    error_message="Could not convert path to module name",
                    file_path=str(file_path),
                )
                result.add_result(skip_result)
                self._log(f"⊘ {file_path} (skipped)")
                continue

            # Test the import
            import_result = self._test_import(module_name, file_path)
            result.add_result(import_result)

            # Log the result
            if import_result.status == EnumImportStatus.SUCCESS:
                self._log(f"✓ {module_name}")
            elif import_result.status == EnumImportStatus.CIRCULAR_IMPORT:
                self._log(f"✗ {module_name}")
                self._log(f"  Circular import detected: {import_result.error_message}")
            elif import_result.status == EnumImportStatus.IMPORT_ERROR:
                self._log(f"⚠ {module_name}")
                error_msg = import_result.error_message or "Unknown error"
                self._log(f"  Import error (non-circular): {error_msg[:100]}")
            elif import_result.status == EnumImportStatus.UNEXPECTED_ERROR:
                self._log(f"⚠ {module_name}")
                self._log(f"  Unexpected error: {import_result.error_message}")

            # Notify progress
            self._notify_progress(f"Tested {module_name}: {import_result.status.value}")

        return result

    def validate_and_report(self) -> int:
        """
        Validate and print a detailed report.

        Returns:
            Exit code (0 for success, 1 if circular imports detected)

        Example:
            >>> validator = CircularImportValidator("/path/to/src", verbose=True)
            >>> exit_code = validator.validate_and_report()
        """
        print("Testing for circular imports...")
        print(f"Source path: {self.source_path}")
        print("")

        result = self.validate()

        print("")
        print("=" * 80)
        print("RESULTS")
        print("=" * 80)
        summary = result.get_summary()
        print(f"Total files: {summary['total_files']}")
        print(f"✓ Successful imports: {summary['successful']}")
        print(f"✗ Circular imports detected: {summary['circular_imports']}")
        print(f"⚠ Other import errors: {summary['import_errors']}")
        print(f"⚠ Unexpected errors: {summary['unexpected_errors']}")
        print(f"⊘ Skipped: {summary['skipped']}")
        print(f"Success rate: {result.success_rate:.1f}%")

        if result.circular_imports:
            print("")
            print("CIRCULAR IMPORT FAILURES:")
            print("-" * 80)
            for import_result in result.circular_imports:
                print(f"  • {import_result.module_name}")
                print(f"    {import_result.error_message}")
            print("")
            return 1

        print("")
        print("🎉 No circular imports detected!")
        return 0
