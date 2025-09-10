import importlib
from pathlib import Path

from omnibase_core.model.core.model_generic_yaml import ModelGenericYaml
from omnibase_core.utils.safe_yaml_loader import (
    load_and_validate_yaml_model,
)


class MixinNodeIdFromContract:
    """
    Mixin to load node_id (node_name) from node.onex.yaml or contract.yaml in the node's directory.
    Provides the _load_node_id() utility method for use in node __init__.
    Now supports explicit contract_path injection for testability and non-standard instantiation.
    """

    def __init__(self, contract_path: Path | None = None, *args, **kwargs):
        self._explicit_contract_path = contract_path
        super().__init__(*args, **kwargs)

    def _get_node_dir(self):
        module = importlib.import_module(self.__class__.__module__)
        node_file = Path(module.__file__)
        return node_file.parent

    def _load_node_id(self, contract_path: Path | None = None):
        # Use explicit contract_path if provided
        contract_path = contract_path or getattr(self, "_explicit_contract_path", None)
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

            contract = yaml_model.model_dump()
        return contract.get("node_name") or contract.get("name")
