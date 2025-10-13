"""
Namespace configuration model.
"""

from pydantic import BaseModel

from omnibase_core.enums import EnumNamespaceStrategy


class ModelNamespaceConfig(BaseModel):
    """Configuration for namespace handling."""

    enabled: bool = True
    strategy: EnumNamespaceStrategy = EnumNamespaceStrategy.ONEX_DEFAULT
