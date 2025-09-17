"""Base protocol for all pre-commit checker tools."""

from abc import abstractmethod
from pathlib import Path
from typing import Protocol

from omnibase_core.models.precommit.model_check_result import ModelCheckResult


class ProtocolPrecommitChecker(Protocol):
    """Base protocol for pre-commit checker tools.

    All pre-commit checkers follow this interface to provide
    consistent checking behavior across different validation types.
    """

    @abstractmethod
    def check_files(self, file_paths: list[Path]) -> ModelCheckResult:
        """Check files for violations.

        Args:
            file_paths: List of file paths to check

        Returns:
            ModelCheckResult with violations and summary
        """
        ...

    @abstractmethod
    def check_single_file(self, file_path: Path) -> ModelCheckResult:
        """Check a single file for violations.

        Args:
            file_path: Path to file to check

        Returns:
            ModelCheckResult with violations found
        """
        ...
