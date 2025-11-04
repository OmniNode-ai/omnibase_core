from __future__ import annotations

"""
Namespace configuration model.
"""


from typing import Any

from pydantic import BaseModel

from omnibase_core.enums.enum_namespace_strategy import EnumNamespaceStrategy


class ModelNamespaceConfig(BaseModel):
    """Configuration for namespace handling.
    Implements omnibase_spi protocols:
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    enabled: bool = True
    strategy: EnumNamespaceStrategy = EnumNamespaceStrategy.ONEX_DEFAULT

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If configuration logic fails
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            Exception: If validation logic fails
        """
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True
