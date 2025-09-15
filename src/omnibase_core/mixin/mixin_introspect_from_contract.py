import importlib
from pathlib import Path

from omnibase_core.models.core.model_generic_yaml import ModelGenericYaml
from omnibase_core.utils.safe_yaml_loader import (
    load_and_validate_yaml_model,
)


class MixinIntrospectFromContract:
    """
    Mixin to provide a canonical introspect() method that loads contract/metadata YAML as a dict.
    Looks for node.onex.yaml or contract.yaml in the node's directory.
    """

    def _get_node_dir(self):
        # Security: validate module is within allowed namespaces
        allowed_prefixes = [
            "omnibase_core.",
            "omnibase_spi.",
            "omnibase.",
            # Add other trusted prefixes as needed
        ]
        if not any(
            self.__class__.__module__.startswith(prefix) for prefix in allowed_prefixes
        ):
            raise ValueError(
                f"Module not in allowed namespace: {self.__class__.__module__}"
            )

        module = importlib.import_module(self.__class__.__module__)
        node_file = Path(module.__file__)
        return node_file.parent

    def introspect(self, contract_path: Path | None = None) -> dict:
        node_dir = self._get_node_dir()
        if contract_path is None:
            contract_path = node_dir / "node.onex.yaml"
            if not contract_path.exists():
                contract_path = node_dir / "contract.yaml"
        if not contract_path.exists():
            msg = f"No contract file found at {contract_path}"
            raise FileNotFoundError(msg)
        with open(contract_path) as f:
            # Load and validate YAML using Pydantic model

            yaml_model = load_and_validate_yaml_model(contract_path, ModelGenericYaml)

            return yaml_model.model_dump()
