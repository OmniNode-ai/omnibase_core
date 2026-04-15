# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

from .model_api_config import ModelAPIConfig
from .model_database_config import ModelDatabaseConfig
from .model_monitoring_config import ModelMonitoringConfig
from .model_output_config import ModelOutputConfig
from .model_tier_config import ModelTierConfig

__all__ = [
    "ModelAPIConfig",
    "ModelCLIConfig",
    "ModelDatabaseConfig",
    "ModelMonitoringConfig",
    "ModelOutputConfig",
    "ModelTierConfig",
]


class ModelCLIConfig(BaseModel):
    """
    Complete CLI configuration with production settings.

    Supports environment variable overrides and validation for all
    configuration sections used by the production CLI.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    # Core configuration sections
    tiers: ModelTierConfig = Field(default_factory=ModelTierConfig)
    output: ModelOutputConfig = Field(default_factory=ModelOutputConfig)
    api: ModelAPIConfig | None = Field(default=None)
    database: ModelDatabaseConfig | None = Field(default=None)
    monitoring: ModelMonitoringConfig = Field(default_factory=ModelMonitoringConfig)

    # Global settings
    config_dir: Path = Field(
        default=Path.home() / ".onex",
        description="Config directory",
    )
    data_dir: Path = Field(
        default=Path.home() / ".onex" / "data",
        description="Data directory",
    )
    cache_dir: Path = Field(
        default=Path.home() / ".onex" / "cache",
        description="Cache directory",
    )

    # Environment overrides
    debug: bool = Field(default=False, description="Enable debug mode")
    verbose: bool = Field(default=False, description="Enable verbose output")

    def model_post_init(self, __context: object) -> None:
        """Initialize configuration after model creation."""
        self.ensure_directories_exist()

    def ensure_directories_exist(self) -> None:
        """Create configuration directories if they don't exist."""
        for directory in [self.config_dir, self.data_dir, self.cache_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_file(cls, config_path: Path) -> ModelCLIConfig:
        """Load configuration from a YAML file."""
        if not config_path.exists():
            raise ModelOnexError(
                message=f"Configuration file not found: {config_path}",
                error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
            )
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ModelOnexError(
                message=f"Configuration file must contain a YAML mapping: {config_path}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return cls.model_validate(raw)

    def save_to_file(self, config_path: Path) -> None:
        """Save configuration to a YAML file."""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        data = self.model_dump(mode="json", exclude_none=True)
        config_path.write_text(
            yaml.dump(data, default_flow_style=False), encoding="utf-8"
        )

    @classmethod
    def get_default_config_path(cls) -> Path:
        """Get the default configuration file path."""
        return Path.home() / ".onex" / "config.yaml"

    @classmethod
    def load_or_create_default(cls) -> ModelCLIConfig:
        """Load config from default location or create with defaults."""
        config_path = cls.get_default_config_path()

        if config_path.exists():
            return cls.from_file(config_path)

        # Create default config
        config = cls()
        config.save_to_file(config_path)
        return config
