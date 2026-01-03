"""
Model for contract loader representation in ONEX NodeBase implementation.

This model supports the PATTERN-005 NodeBase functionality for
unified contract loading and resolution.

"""

import threading
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_contract_cache import ModelContractCache
from omnibase_core.models.core.model_contract_content import ModelContractContent
from omnibase_core.models.core.model_contract_reference import ModelContractReference

# Lazy model rebuild flag - forward references are resolved on first use, not at import
_models_rebuilt = False
_rebuild_lock = threading.Lock()


def _ensure_models_rebuilt(contract_loader_cls: type[BaseModel] | None = None) -> None:
    """Ensure models are rebuilt to resolve forward references (lazy initialization).

    This function implements lazy model rebuild to avoid importing ModelCustomFields
    at module load time. The rebuild only happens on first ModelContractLoader
    instantiation, improving import performance when the model isn't used.

    The pattern:
    1. Module-level flag tracks if rebuild has occurred
    2. This function is called via __new__ on first instantiation
    3. The rebuild resolves forward references to ModelCustomFields in dependency chain
    4. Then rebuilds ModelContractLoader to pick up the resolved types
    5. Subsequent instantiations skip the rebuild (flag is already True)

    Args:
        contract_loader_cls: The ModelContractLoader class to rebuild. Must be provided
            on first call to properly resolve the forward reference chain.

    Thread Safety:
        This function is thread-safe. It uses double-checked locking to ensure that
        concurrent first-instantiation calls safely coordinate the rebuild. The pattern:
        1. Fast path: Check flag without lock (subsequent calls return immediately)
        2. Acquire lock only when rebuild might be needed
        3. Re-check flag inside lock to handle race conditions
        4. Perform rebuild and set flag atomically within lock
    """
    global _models_rebuilt
    if _models_rebuilt:  # Fast path - no lock needed
        return

    with _rebuild_lock:
        if (
            _models_rebuilt
        ):  # Double-check after acquiring lock  # type: ignore[unreachable]
            return  # type: ignore[unreachable]

        # Import ModelCustomFields to resolve forward references
        from omnibase_core.models.services.model_custom_fields import (  # noqa: F401
            ModelCustomFields,
        )

        # Rebuild intermediate models that may have forward references
        ModelContractContent.model_rebuild()
        ModelContractCache.model_rebuild()

        # Then rebuild the contract loader model to pick up the resolved types
        if contract_loader_cls is not None:
            contract_loader_cls.model_rebuild()
        _models_rebuilt = True


class ModelContractLoader(BaseModel):
    """Model representing contract loader state and configuration."""

    def __new__(cls, **_data: Any) -> "ModelContractLoader":
        """Override __new__ to trigger lazy model rebuild before Pydantic validation.

        Pydantic validates model completeness before calling model_validator,
        so we must trigger the rebuild in __new__ which runs first.

        Args:
            **_data: Keyword arguments passed to Pydantic (handled by __init__).
                Uses ``Any`` type because this is a pass-through pattern where we
                capture but do not process arbitrary Pydantic field values. The
                values can be any type that matches the model's field definitions
                (bool, dict, list, Path, etc.) and are validated by Pydantic.

        Returns:
            A new ModelContractLoader instance with forward references resolved.
        """
        _ensure_models_rebuilt(cls)
        return super().__new__(cls)

    cache_enabled: bool = Field(
        default=True,
        description="Whether contract caching is enabled",
    )
    contract_cache: dict[str, ModelContractCache] = Field(
        default_factory=dict,
        description="Contract cache storage",
    )
    resolution_stack: list[str] = Field(
        default_factory=list,
        description="Current resolution stack for circular reference detection",
    )
    base_path: Path = Field(
        default=..., description="Base path for contract resolution"
    )
    loaded_contracts: dict[str, ModelContractContent] = Field(
        default_factory=dict,
        description="Successfully loaded contracts",
    )
    resolved_references: dict[str, ModelContractReference] = Field(
        default_factory=dict,
        description="Resolved contract references",
    )
