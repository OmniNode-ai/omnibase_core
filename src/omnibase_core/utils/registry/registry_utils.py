"""
Registry utilities for ONEX NodeBase patterns.

Provides common helper functions to eliminate repetitive registry patterns.
"""

from pathlib import Path


def get_default_node_dir(calling_file: str) -> Path:
    """
    Calculate default node_dir from calling registry file.

    This eliminates the repetitive pattern of hardcoded /tmp/ paths
    and provides consistent path calculation across all registries.

    Args:
        calling_file: __file__ from the calling registry

    Returns:
        Path to the tool's v1_0_0 directory (parent.parent of registry file)

    Example:
        # In registry file: src/omnibase_core/tools/canary/canary_pure_tool/v1_0_0/registry/registry_canary_pure_tool.py
        # Returns: src/omnibase_core/tools/canary/canary_pure_tool/v1_0_0/
        node_dir = get_default_node_dir(__file__)
    """
    return Path(calling_file).parent.parent


def validate_registry_config_type(
    config: object | None,
    expected_type: type,
) -> object:
    """
    Validate registry config is proper Pydantic model, not Dict[str, Any].

    Helps catch violations of "All data structures must be proper Pydantic models".

    Args:
        config: Configuration object to validate
        expected_type: Expected Pydantic model type

    Returns:
        Valid config instance or default instance of expected_type

    Raises:
        TypeError: If config is dict or other invalid type
    """
    if config is None:
        # Handle complex models that require sub-models
        if expected_type.__name__ == "ModelRegistryConfig":
            # Create default ModelRegistryConfig with required service_config
            from omnibase_core.model.service.model_service_registry_config import (
                ModelServiceRegistryConfig,
            )

            default_service_config = ModelServiceRegistryConfig()
            return expected_type(service_config=default_service_config)
        return expected_type()

    if isinstance(config, dict):
        msg = (
            f"Registry config must be {expected_type.__name__} Pydantic model, "
            f"not Dict[str, Any]. This violates ONEX core principle: "
            f"'All data structures must be proper Pydantic models'"
        )
        raise TypeError(
            msg,
        )

    if not isinstance(config, expected_type):
        msg = (
            f"Registry config must be {expected_type.__name__}, "
            f"got {type(config).__name__}"
        )
        raise TypeError(
            msg,
        )

    return config
