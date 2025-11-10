from typing import Any

from omnibase_core.models.security.model_mask_data import ModelMaskData
from omnibase_core.models.security.model_secret_config import ModelSecretConfig
from omnibase_core.models.security.model_secret_manager import ModelSecretManager


class ModelSecretManagerCompat:
    """
    Current SecretManager standards layer.

    DEPRECATED: Use ModelSecretManager instead for enhanced functionality.
    This class provides compatibility for existing code.
    """

    def __init__(self, config: ModelSecretConfig):
        """Initialize with ModelSecretManager internally."""
        self._manager = ModelSecretManager(config=config)

    def get_database_config(self) -> Any:
        """Get database configuration (legacy method)."""
        return self._manager.get_database_config()

    def mask_sensitive_data(
        self, data: ModelMaskData, mask_level: str = "standard"
    ) -> ModelMaskData:
        """Mask sensitive data (legacy method)."""
        return self._manager.mask_sensitive_data(data, mask_level)
