"""
Namespace configuration model.
"""

from __future__ import annotations

from pydantic import BaseModel

from omnibase_core.enums.enum_namespace_strategy import EnumNamespaceStrategy


class ModelNamespaceConfig(BaseModel):
    """Configuration for namespace handling."""

    enabled: bool = True
    strategy: EnumNamespaceStrategy = EnumNamespaceStrategy.ONEX_DEFAULT
