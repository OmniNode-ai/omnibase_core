"""
Namespace configuration model.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ModelNamespaceConfig(BaseModel):
    """Configuration for namespace handling."""

    enabled: bool = True
    strategy: Literal["ONEX_DEFAULT", "EXPLICIT", "AUTO"] = "ONEX_DEFAULT"
