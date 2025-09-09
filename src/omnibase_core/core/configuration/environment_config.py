#!/usr/bin/env python3
"""
Environment-based configuration management system for ONEX.

Provides a unified approach to environment variable configuration with
validation, type conversion, and hierarchical override support.
"""

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, TypeVar, Union, get_type_hints

from pydantic import BaseModel, Field, ValidationError

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)


class ModelEnvironmentVariable(BaseModel):
    """Metadata for environment variable configuration."""

    key: str = Field(..., description="Environment variable key")
    default_value: Any = Field(None, description="Default value if not set")
    required: bool = Field(False, description="Whether variable is required")
    description: str = Field("", description="Description of the variable")
    sensitive: bool = Field(False, description="Whether to mask in logs")
    validation_pattern: str | None = Field(
        None,
        description="Regex pattern for validation",
    )
    min_value: int | float | None = Field(
        None,
        description="Minimum numeric value",
    )
    max_value: int | float | None = Field(
        None,
        description="Maximum numeric value",
    )
    allowed_values: list[str] | None = Field(
        None,
        description="List of allowed values",
    )


class ModelEnvironmentPrefix(BaseModel):
    """Environment variable prefix configuration."""

    prefix: str = Field(..., description="Prefix for environment variables")
    separator: str = Field("_", description="Separator character")
    case_sensitive: bool = Field(False, description="Whether keys are case-sensitive")

    def format_key(self, key: str) -> str:
        """Format a key with the prefix."""
        formatted = f"{self.prefix}{self.separator}{key}"
        return formatted if self.case_sensitive else formatted.upper()


class ModelEnvironmentConfig(BaseModel):
    """Base configuration model with environment variable support."""

    _env_prefix: ModelEnvironmentPrefix | None = None
    _env_variables: dict[str, ModelEnvironmentVariable] = {}

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True
        extra = "forbid"

    @classmethod
    def from_environment(
        cls: type[T],
        prefix: str | None = None,
        env_file: Path | None = None,
        strict: bool = True,
        **overrides: Any,
    ) -> T:
        """
        Create configuration from environment variables.

        Args:
            prefix: Environment variable prefix (e.g., 'OMNIBASE')
            env_file: Optional .env file to load
            strict: Whether to fail on missing required variables
            **overrides: Direct value overrides

        Returns:
            Configured instance

        Raises:
            ValidationError: If validation fails and strict=True
        """
        # Load from .env file if provided
        if env_file and env_file.exists():
            cls._load_env_file(env_file)

        # Set up prefix
        if prefix:
            cls._env_prefix = ModelEnvironmentPrefix(prefix=prefix)
        elif not cls._env_prefix:
            cls._env_prefix = ModelEnvironmentPrefix(prefix=cls.__name__.upper())

        # Extract values from environment
        env_values = cls._extract_env_values()

        # Merge with overrides (overrides take precedence)
        config_values = {**env_values, **overrides}

        try:
            return cls(**config_values)
        except ValidationError as e:
            if strict:
                raise
            logger.warning(f"Configuration validation failed: {e}")
            # Return with available values, missing will use defaults
            return cls(
                **{k: v for k, v in config_values.items() if k in cls.model_fields},
            )

    @classmethod
    def _load_env_file(cls, env_file: Path) -> None:
        """Load environment variables from file."""
        try:
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip().strip("\"'")
        except Exception as e:
            logger.warning(f"Failed to load env file {env_file}: {e}")

    @classmethod
    def _extract_env_values(cls) -> dict[str, Any]:
        """Extract configuration values from environment variables."""
        values = {}
        type_hints = get_type_hints(cls)

        for field_name, field_info in cls.model_fields.items():
            # Try multiple environment key formats
            env_keys = cls._generate_env_keys(field_name)

            for env_key in env_keys:
                env_value = os.getenv(env_key)
                if env_value is not None:
                    # Convert string value to appropriate type
                    target_type = type_hints.get(field_name)
                    converted_value = cls._convert_env_value(env_value, target_type)
                    values[field_name] = converted_value
                    break

        return values

    @classmethod
    def _generate_env_keys(cls, field_name: str) -> list[str]:
        """Generate possible environment variable keys for a field."""
        keys = []

        if cls._env_prefix:
            # With prefix: PREFIX_FIELD_NAME
            keys.append(cls._env_prefix.format_key(field_name))
            # With prefix, camelCase to snake_case: PREFIX_FIELD_NAME
            snake_case = cls._camel_to_snake(field_name)
            if snake_case != field_name:
                keys.append(cls._env_prefix.format_key(snake_case))

        # Without prefix: FIELD_NAME
        keys.append(field_name.upper())
        keys.append(cls._camel_to_snake(field_name).upper())

        return keys

    @staticmethod
    def _camel_to_snake(name: str) -> str:
        """Convert camelCase to snake_case."""
        import re

        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", name).lower()

    @staticmethod
    def _convert_env_value(value: str, target_type: type | None) -> Any:
        """Convert string environment value to target type."""
        if target_type is None:
            return value

        # Handle Union types (like Optional[str] = Union[str, None])
        if hasattr(target_type, "__origin__"):
            if target_type.__origin__ is Union:
                # Get first non-None type from Union
                args = target_type.__args__
                non_none_types = [arg for arg in args if arg is not type(None)]
                if non_none_types:
                    target_type = non_none_types[0]
                else:
                    return value

        # Type conversion
        if target_type == bool:
            return value.lower() in ("true", "1", "yes", "on")
        if target_type == int:
            return int(value)
        if target_type == float:
            return float(value)
        if target_type == list or (
            hasattr(target_type, "__origin__") and target_type.__origin__ is list
        ):
            return [item.strip() for item in value.split(",")]
        if target_type == dict:
            # Simple key=value,key2=value2 format
            pairs = value.split(",")
            return {
                k.strip(): v.strip()
                for k, v in [pair.split("=", 1) for pair in pairs if "=" in pair]
            }
        return value

    def get_env_summary(self, mask_sensitive: bool = True) -> dict[str, Any]:
        """Get summary of environment configuration."""
        summary = {}

        for field_name, field_value in self.model_dump().items():
            env_var = self._env_variables.get(field_name)

            if env_var and env_var.sensitive and mask_sensitive:
                summary[field_name] = "***MASKED***"
            else:
                summary[field_name] = field_value

        return summary

    @classmethod
    def get_env_documentation(cls) -> list[dict[str, Any]]:
        """Get documentation for all environment variables."""
        docs = []

        for field_name, field_info in cls.model_fields.items():
            env_keys = cls._generate_env_keys(field_name)
            env_var = cls._env_variables.get(
                field_name,
                ModelEnvironmentVariable(key=env_keys[0] if env_keys else field_name),
            )

            docs.append(
                {
                    "field": field_name,
                    "env_keys": env_keys,
                    "description": env_var.description or field_info.description,
                    "default": field_info.default,
                    "required": env_var.required,
                    "type": (
                        field_info.annotation.__name__
                        if field_info.annotation
                        else "Any"
                    ),
                },
            )

        return docs


# Global configuration registry for easy access
class EnvironmentConfigRegistry:
    """Registry for managing environment-based configurations."""

    _configs: dict[str, ModelEnvironmentConfig] = {}

    @classmethod
    def register(cls, name: str, config: ModelEnvironmentConfig) -> None:
        """Register a configuration instance."""
        cls._configs[name] = config
        logger.info(f"Registered configuration: {name}")

    @classmethod
    def get(cls, name: str) -> ModelEnvironmentConfig | None:
        """Get a registered configuration."""
        return cls._configs.get(name)

    @classmethod
    def list_configs(cls) -> list[str]:
        """List all registered configuration names."""
        return list(cls._configs.keys())

    @classmethod
    def reload_all(cls) -> None:
        """Reload all configurations from environment."""
        for name, config in cls._configs.items():
            try:
                # Reload configuration
                new_config = config.__class__.from_environment()
                cls._configs[name] = new_config
                logger.info(f"Reloaded configuration: {name}")
            except Exception as e:
                logger.error(f"Failed to reload configuration {name}: {e}")


# Global registry instance
config_registry = EnvironmentConfigRegistry()


def register_config(
    name: str,
    config_class: type[ModelEnvironmentConfig],
    **kwargs,
) -> ModelEnvironmentConfig:
    """
    Helper to register and create configuration from environment.

    Args:
        name: Configuration name for registry
        config_class: Configuration class to instantiate
        **kwargs: Additional arguments for from_environment()

    Returns:
        Created configuration instance
    """
    config = config_class.from_environment(**kwargs)
    config_registry.register(name, config)
    return config


@lru_cache(maxsize=128)
def get_env_bool(key: str, default: bool = False) -> bool:
    """Get boolean value from environment with caching."""
    value = os.getenv(key, str(default)).lower()
    return value in ("true", "1", "yes", "on")


@lru_cache(maxsize=128)
def get_env_int(key: str, default: int = 0) -> int:
    """Get integer value from environment with caching."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        logger.warning(f"Invalid integer for {key}, using default: {default}")
        return default


@lru_cache(maxsize=128)
def get_env_float(key: str, default: float = 0.0) -> float:
    """Get float value from environment with caching."""
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        logger.warning(f"Invalid float for {key}, using default: {default}")
        return default


def get_env_list(
    key: str,
    default: list[str] = None,
    separator: str = ",",
) -> list[str]:
    """Get list value from environment."""
    if default is None:
        default = []

    value = os.getenv(key)
    if not value:
        return default

    return [item.strip() for item in value.split(separator) if item.strip()]


def is_production_environment() -> bool:
    """Check if running in production environment."""
    env = os.getenv("ENVIRONMENT", "").lower()
    node_env = os.getenv("NODE_ENV", "").lower()

    return (
        env in ("production", "prod")
        or node_env in ("production", "prod")
        or (not get_env_bool("DEBUG", False) and not get_env_bool("DEV_MODE", False))
    )


def is_development_environment() -> bool:
    """Check if running in development environment."""
    return not is_production_environment()
