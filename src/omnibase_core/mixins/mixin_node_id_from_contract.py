import importlib
import os
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.core.model_generic_yaml import ModelGenericYaml
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class MixinNodeIdFromContract:
    """
    Mixin to load node_id (node_name) from node.onex.yaml or contract.yaml in the node's directory.
    Provides the _load_node_id() utility method for use in node __init__.
    Now supports explicit contract_path injection for testability and non-standard instantiation.

    Security: Uses configurable allowed namespaces to prevent unauthorized access.
    By default, allows omnibase_* modules, but can be customized via OMNIBASE_ALLOWED_NAMESPACES
    environment variable or _allowed_namespaces class attribute.
    """

    # Default allowed namespaces - can be overridden by subclasses
    _allowed_namespaces = [
        "omnibase_core.",
        "omnibase_spi.",
        "omnibase.",
    ]

    def __init__(
        self, contract_path: Path | None = None, *args: object, **kwargs: object
    ) -> None:
        self._explicit_contract_path = contract_path
        super().__init__(*args, **kwargs)

    def _get_allowed_namespaces(self) -> list[str]:
        """
        Get allowed module namespaces for security validation.

        Priority order:
        1. OMNIBASE_ALLOWED_NAMESPACES environment variable (comma-separated)
        2. Class-level _allowed_namespaces attribute
        3. Default omnibase namespaces

        Returns:
            List of allowed namespace prefixes
        """
        # Check environment variable first (for package consumers)
        env_namespaces = os.environ.get("OMNIBASE_ALLOWED_NAMESPACES")
        if env_namespaces:
            return [ns.strip() for ns in env_namespaces.split(",") if ns.strip()]

        # Use class-level configuration (for subclasses)
        if hasattr(self, "_allowed_namespaces"):
            return self._allowed_namespaces

        # Default to omnibase namespaces only
        return [
            "omnibase_core.",
            "omnibase_spi.",
            "omnibase.",
        ]

    def _get_node_dir(self) -> Path:
        """
        Get the directory containing the node module.

        Security: Validates module is within allowed namespaces to prevent
        unauthorized filesystem access. Consumers can configure allowed
        namespaces via environment variable or subclass attribute.
        """
        allowed_prefixes = self._get_allowed_namespaces()

        if not any(
            self.__class__.__module__.startswith(prefix) for prefix in allowed_prefixes
        ):
            raise ModelOnexError(
                f"Module '{self.__class__.__module__}' not in allowed namespaces: {allowed_prefixes}. "
                f"Set OMNIBASE_ALLOWED_NAMESPACES environment variable or override _allowed_namespaces class attribute.",
                EnumCoreErrorCode.VALIDATION_ERROR,
            )

        module = importlib.import_module(self.__class__.__module__)
        if module.__file__ is None:
            raise ModelOnexError(
                f"Module '{self.__class__.__module__}' has no __file__ attribute",
                EnumCoreErrorCode.VALIDATION_ERROR,
            )
        node_file = Path(module.__file__)
        return node_file.parent

    def _load_node_id(self, contract_path: Path | None = None) -> str:
        # Lazy import to avoid circular dependency
        from omnibase_core.utils.util_safe_yaml_loader import (
            load_and_validate_yaml_model,
        )

        # Use explicit contract_path if provided
        contract_path = contract_path or getattr(self, "_explicit_contract_path", None)
        node_dir = self._get_node_dir()
        if contract_path is None:
            contract_path = node_dir / "node.onex.yaml"
            if not contract_path.exists():
                contract_path = node_dir / "contract.yaml"
        if not contract_path.exists():
            msg = f"No contract file found at {contract_path}"
            raise ModelOnexError(msg, EnumCoreErrorCode.FILE_NOT_FOUND)
        # Load and validate YAML using Pydantic model
        contract_model = load_and_validate_yaml_model(contract_path, ModelGenericYaml)
        contract = contract_model.model_dump()
        node_name = contract.get("node_name") or contract.get("name")
        if not node_name:
            msg = f"Contract at {contract_path} must have 'node_name' or 'name' field"
            raise ModelOnexError(msg, EnumCoreErrorCode.VALIDATION_ERROR)
        return str(node_name)
