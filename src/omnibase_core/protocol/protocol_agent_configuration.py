"""
Protocol for Agent Configuration Management.

This protocol defines the interface for managing Claude Code agent configurations,
including validation, persistence, versioning, and security.
"""

from abc import ABC, abstractmethod

from omnibase_core.model.configuration.model_agent_config import ModelAgentConfig
from omnibase_core.model.core.model_validation_result import ModelValidationResult


class ProtocolAgentConfiguration(ABC):
    """Protocol for Claude Code agent configuration management."""

    @abstractmethod
    async def validate_configuration(
        self,
        config: ModelAgentConfig,
    ) -> ModelValidationResult:
        """
        Validate agent configuration for correctness and security.

        Args:
            config: Agent configuration to validate

        Returns:
            Validation result with issues and recommendations

        Raises:
            ValidationError: If validation process fails
        """

    @abstractmethod
    async def save_configuration(self, config: ModelAgentConfig) -> bool:
        """
        Save agent configuration to persistent storage.

        Args:
            config: Agent configuration to save

        Returns:
            True if configuration was saved successfully

        Raises:
            ConfigurationError: If saving fails
            SecurityError: If configuration violates security policies
        """

    @abstractmethod
    async def load_configuration(self, agent_id: str) -> ModelAgentConfig | None:
        """
        Load agent configuration from persistent storage.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent configuration or None if not found

        Raises:
            ConfigurationError: If loading fails
        """

    @abstractmethod
    async def delete_configuration(self, agent_id: str) -> bool:
        """
        Delete agent configuration from persistent storage.

        Args:
            agent_id: Agent identifier

        Returns:
            True if configuration was deleted successfully

        Raises:
            ConfigurationError: If deletion fails
        """

    @abstractmethod
    async def list_configurations(self) -> list[str]:
        """
        List all available agent configuration IDs.

        Returns:
            List of agent IDs with saved configurations
        """

    @abstractmethod
    async def update_configuration(
        self,
        agent_id: str,
        updates: dict[str, str],
    ) -> ModelAgentConfig:
        """
        Update specific fields in an agent configuration.

        Args:
            agent_id: Agent identifier
            updates: Dictionary of field updates

        Returns:
            Updated agent configuration

        Raises:
            ConfigurationError: If update fails
            ValidationError: If updated configuration is invalid
        """

    @abstractmethod
    async def create_configuration_template(
        self,
        template_name: str,
        base_config: ModelAgentConfig,
    ) -> bool:
        """
        Create a reusable configuration template.

        Args:
            template_name: Name for the template
            base_config: Base configuration to use as template

        Returns:
            True if template was created successfully

        Raises:
            ConfigurationError: If template creation fails
        """

    @abstractmethod
    async def apply_configuration_template(
        self,
        agent_id: str,
        template_name: str,
        overrides: dict[str, str] | None = None,
    ) -> ModelAgentConfig:
        """
        Apply a configuration template to create agent configuration.

        Args:
            agent_id: Agent identifier
            template_name: Name of template to apply
            overrides: Optional field overrides

        Returns:
            Generated agent configuration

        Raises:
            ConfigurationError: If template application fails
            TemplateNotFoundError: If template doesn't exist
        """

    @abstractmethod
    async def list_configuration_templates(self) -> list[str]:
        """
        List all available configuration templates.

        Returns:
            List of template names
        """

    @abstractmethod
    async def backup_configuration(self, agent_id: str) -> str:
        """
        Create a backup of agent configuration.

        Args:
            agent_id: Agent identifier

        Returns:
            Backup identifier for restoration

        Raises:
            ConfigurationError: If backup creation fails
        """

    @abstractmethod
    async def restore_configuration(self, agent_id: str, backup_id: str) -> bool:
        """
        Restore agent configuration from backup.

        Args:
            agent_id: Agent identifier
            backup_id: Backup identifier

        Returns:
            True if restoration was successful

        Raises:
            ConfigurationError: If restoration fails
            BackupNotFoundError: If backup doesn't exist
        """

    @abstractmethod
    async def get_configuration_history(self, agent_id: str) -> list[dict[str, str]]:
        """
        Get configuration change history for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            List of configuration changes with timestamps and changes
        """

    @abstractmethod
    async def clone_configuration(
        self,
        source_agent_id: str,
        target_agent_id: str,
    ) -> ModelAgentConfig:
        """
        Clone configuration from one agent to another.

        Args:
            source_agent_id: Source agent identifier
            target_agent_id: Target agent identifier

        Returns:
            Cloned agent configuration

        Raises:
            ConfigurationError: If cloning fails
            SourceNotFoundError: If source configuration doesn't exist
        """

    @abstractmethod
    async def validate_security_policies(self, config: ModelAgentConfig) -> list[str]:
        """
        Validate configuration against security policies.

        Args:
            config: Agent configuration to validate

        Returns:
            List of security policy violations
        """

    @abstractmethod
    async def encrypt_sensitive_fields(
        self,
        config: ModelAgentConfig,
    ) -> ModelAgentConfig:
        """
        Encrypt sensitive fields in agent configuration.

        Args:
            config: Agent configuration to encrypt

        Returns:
            Configuration with encrypted sensitive fields

        Raises:
            EncryptionError: If encryption fails
        """

    @abstractmethod
    async def decrypt_sensitive_fields(
        self,
        config: ModelAgentConfig,
    ) -> ModelAgentConfig:
        """
        Decrypt sensitive fields in agent configuration.

        Args:
            config: Agent configuration to decrypt

        Returns:
            Configuration with decrypted sensitive fields

        Raises:
            DecryptionError: If decryption fails
        """

    @abstractmethod
    async def set_configuration_defaults(
        self,
        config: ModelAgentConfig,
    ) -> ModelAgentConfig:
        """
        Apply default values to agent configuration.

        Args:
            config: Agent configuration to apply defaults to

        Returns:
            Configuration with defaults applied
        """

    @abstractmethod
    async def merge_configurations(
        self,
        base_config: ModelAgentConfig,
        override_config: ModelAgentConfig,
    ) -> ModelAgentConfig:
        """
        Merge two configurations with override taking precedence.

        Args:
            base_config: Base agent configuration
            override_config: Configuration with override values

        Returns:
            Merged agent configuration
        """

    @abstractmethod
    async def export_configuration(
        self,
        agent_id: str,
        format_type: str = "yaml",
    ) -> str:
        """
        Export agent configuration to specified format.

        Args:
            agent_id: Agent identifier
            format_type: Export format (yaml, json, toml)

        Returns:
            Serialized configuration in specified format

        Raises:
            ConfigurationError: If export fails
            UnsupportedFormatError: If format is not supported
        """

    @abstractmethod
    async def import_configuration(
        self,
        agent_id: str,
        config_data: str,
        format_type: str = "yaml",
    ) -> ModelAgentConfig:
        """
        Import agent configuration from serialized data.

        Args:
            agent_id: Agent identifier
            config_data: Serialized configuration data
            format_type: Import format (yaml, json, toml)

        Returns:
            Imported and validated agent configuration

        Raises:
            ConfigurationError: If import fails
            ValidationError: If imported configuration is invalid
            UnsupportedFormatError: If format is not supported
        """
