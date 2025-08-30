"""Utility for loading and validating ONEX policy files.

This utility provides type-safe loading of policy files with validation
and caching for performance.
"""

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.exceptions import OnexError
from omnibase_core.model.policy.model_coding_standards_policy import \
    ModelCodingStandardsPolicyWrapper
from omnibase_core.model.policy.model_debug_logging_policy import \
    ModelDebugLoggingPolicyWrapper
from omnibase_core.model.policy.model_logging_policy import \
    ModelLoggingPolicyWrapper

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class UtilityPolicyLoader:
    """Utility for loading and validating ONEX policy files."""

    def __init__(self, policies_dir: Optional[Path] = None):
        """Initialize policy loader with policies directory."""
        self.policies_dir = policies_dir or Path("config/policies")
        self._policy_cache: Dict[str, Any] = {}

    @lru_cache(maxsize=32)
    def load_logging_policy(self) -> ModelLoggingPolicyWrapper:
        """Load and validate the logging policy.

        Returns:
            ModelLoggingPolicyWrapper: Validated logging policy model

        Raises:
            OnexError: If policy file cannot be loaded or validated
        """
        return self._load_policy_file("logging_policy.yaml", ModelLoggingPolicyWrapper)

    @lru_cache(maxsize=32)
    def load_coding_standards_policy(self) -> ModelCodingStandardsPolicyWrapper:
        """Load and validate the coding standards policy.

        Returns:
            ModelCodingStandardsPolicyWrapper: Validated coding standards policy model

        Raises:
            OnexError: If policy file cannot be loaded or validated
        """
        return self._load_policy_file(
            "coding_standards_policy.yaml", ModelCodingStandardsPolicyWrapper
        )

    @lru_cache(maxsize=32)
    def load_debug_logging_policy(self) -> ModelDebugLoggingPolicyWrapper:
        """Load and validate the debug logging policy.

        Returns:
            ModelDebugLoggingPolicyWrapper: Validated debug logging policy model

        Raises:
            OnexError: If policy file cannot be loaded or validated
        """
        return self._load_policy_file(
            "debug_logging_policy.yaml", ModelDebugLoggingPolicyWrapper
        )

    def _load_policy_file(self, filename: str, model_class: Type[T]) -> T:
        """Load and validate a policy file against its Pydantic model.

        Args:
            filename: Policy file name
            model_class: Pydantic model class for validation

        Returns:
            Validated policy model instance

        Raises:
            OnexError: If policy file cannot be loaded or validated
        """
        policy_path = self.policies_dir / filename

        try:
            # Check if file exists
            if not policy_path.exists():
                raise OnexError(
                    error_code=CoreErrorCode.FILE_NOT_FOUND,
                    message=f"Policy file not found: {policy_path}",
                    context={"filename": filename, "path": str(policy_path)},
                )

            # Load YAML content
            logger.debug(
                "function_entry",
                extra={
                    "function": "_load_policy_file",
                    "module": __name__,
                    "sanitized_args": {
                        "filename": filename,
                        "model_class": model_class.__name__,
                    },
                },
            )

            with open(policy_path, "r", encoding="utf-8") as f:
                policy_data = yaml.safe_load(f)

            if not policy_data:
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_ERROR,
                    message=f"Empty policy file: {filename}",
                    context={"filename": filename},
                )

            # Validate against Pydantic model
            try:
                validated_policy = model_class(**policy_data)

                logger.debug(
                    "function_return",
                    extra={
                        "function": "_load_policy_file",
                        "return_type": model_class.__name__,
                        "return_summary": f"loaded policy version {getattr(validated_policy, 'version', 'unknown')}",
                    },
                )

                return validated_policy

            except ValidationError as e:
                logger.error(
                    "exception_occurred",
                    extra={
                        "function": "_load_policy_file",
                        "error_code": "POLICY_VALIDATION_ERROR",
                        "error_message": str(e),
                        "error_context": {
                            "filename": filename,
                            "validation_errors": e.errors(),
                        },
                    },
                    exc_info=True,
                )

                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_ERROR,
                    message=f"Policy validation failed for {filename}",
                    context={"filename": filename, "validation_errors": e.errors()},
                ) from e

        except yaml.YAMLError as e:
            logger.error(
                "exception_occurred",
                extra={
                    "function": "_load_policy_file",
                    "error_code": "YAML_PARSE_ERROR",
                    "error_message": str(e),
                    "error_context": {"filename": filename},
                },
                exc_info=True,
            )

            raise OnexError(
                error_code=CoreErrorCode.PARSING_ERROR,
                message=f"Failed to parse YAML policy file: {filename}",
                context={"filename": filename, "yaml_error": str(e)},
            ) from e

        except Exception as e:
            logger.error(
                "exception_occurred",
                extra={
                    "function": "_load_policy_file",
                    "error_code": "UNKNOWN_ERROR",
                    "error_message": str(e),
                    "error_context": {"filename": filename},
                },
                exc_info=True,
            )

            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"Unexpected error loading policy file: {filename}",
                context={"filename": filename, "error": str(e)},
            ) from e

    def validate_policy_compatibility(
        self, policy_version: str, required_version: str
    ) -> bool:
        """Validate that a policy version is compatible with requirements.

        Args:
            policy_version: Current policy version (semver)
            required_version: Required policy version (semver)

        Returns:
            bool: True if compatible, False otherwise
        """
        try:
            logging_policy = self.load_logging_policy()
            return logging_policy.logging_policy.is_compatible_with_version(
                required_version
            )

        except Exception as e:
            logger.error(
                "exception_occurred",
                extra={
                    "function": "validate_policy_compatibility",
                    "error_code": "COMPATIBILITY_CHECK_FAILED",
                    "error_message": str(e),
                    "error_context": {
                        "policy_version": policy_version,
                        "required_version": required_version,
                    },
                },
                exc_info=True,
            )
            return False

    def get_policy_version(self, policy_name: str) -> Optional[str]:
        """Get the version of a specific policy.

        Args:
            policy_name: Name of the policy file (without .yaml extension)

        Returns:
            Policy version string if found, None otherwise
        """
        try:
            if policy_name == "logging_policy":
                policy = self.load_logging_policy()
                return policy.logging_policy.version
            elif policy_name == "coding_standards_policy":
                policy = self.load_coding_standards_policy()
                return policy.coding_standards_policy.version
            elif policy_name == "debug_logging_policy":
                policy = self.load_debug_logging_policy()
                return policy.debug_logging_policy.version
            # Add other policy types as they are implemented
            return None

        except Exception as e:
            logger.error(
                "exception_occurred",
                extra={
                    "function": "get_policy_version",
                    "error_code": "VERSION_LOOKUP_FAILED",
                    "error_message": str(e),
                    "error_context": {"policy_name": policy_name},
                },
                exc_info=True,
            )
            return None

    def clear_cache(self):
        """Clear the policy cache to force reload on next access."""
        self._policy_cache.clear()
        # Clear the lru_cache as well
        self.load_logging_policy.cache_clear()
        self.load_coding_standards_policy.cache_clear()
        self.load_debug_logging_policy.cache_clear()

        logger.info(
            "Policy cache cleared",
            extra={
                "operation": "clear_policy_cache",
                "cache_size_before": len(self._policy_cache),
            },
        )


# Global instance for easy access
policy_loader = UtilityPolicyLoader()


def get_logging_policy() -> ModelLoggingPolicyWrapper:
    """Convenience function to get the current logging policy.

    Returns:
        ModelLoggingPolicyWrapper: Current logging policy
    """
    return policy_loader.load_logging_policy()


def get_coding_standards_policy() -> ModelCodingStandardsPolicyWrapper:
    """Convenience function to get the current coding standards policy.

    Returns:
        ModelCodingStandardsPolicyWrapper: Current coding standards policy
    """
    return policy_loader.load_coding_standards_policy()


def get_debug_logging_policy() -> ModelDebugLoggingPolicyWrapper:
    """Convenience function to get the current debug logging policy.

    Returns:
        ModelDebugLoggingPolicyWrapper: Current debug logging policy
    """
    return policy_loader.load_debug_logging_policy()


def validate_logging_pattern(pattern_name: str, subsystem: str = "default") -> bool:
    """Validate that a logging pattern exists and is properly configured.

    Args:
        pattern_name: Name of the logging pattern
        subsystem: Subsystem name for override lookup

    Returns:
        bool: True if pattern is valid, False otherwise
    """
    try:
        policy = get_logging_policy()
        pattern = policy.logging_policy.get_pattern_for_subsystem(
            pattern_name, subsystem
        )
        return pattern is not None

    except Exception as e:
        logger.error(
            "exception_occurred",
            extra={
                "function": "validate_logging_pattern",
                "error_code": "PATTERN_VALIDATION_FAILED",
                "error_message": str(e),
                "error_context": {"pattern_name": pattern_name, "subsystem": subsystem},
            },
            exc_info=True,
        )
        return False
