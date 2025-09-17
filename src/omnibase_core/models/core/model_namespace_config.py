"""
Namespace configuration model.
"""

from pydantic import BaseModel

from omnibase_core.enums import NamespaceStrategyEnum


class ModelNamespaceConfig(BaseModel):
    """Configuration for namespace handling."""

    enabled: bool = True
    strategy: NamespaceStrategyEnum = NamespaceStrategyEnum.ONEX_DEFAULT
