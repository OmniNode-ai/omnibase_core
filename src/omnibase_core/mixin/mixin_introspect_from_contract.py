import importlib
from pathlib import Path

import yaml


class MixinIntrospectFromContract:
    """
    Mixin to provide a canonical introspect() method that loads contract/metadata YAML as a dict.
    Looks for node.onex.yaml or contract.yaml in the node's directory.
    """

    def _get_node_dir(self):
        module = importlib.import_module(self.__class__.__module__)
        node_file = Path(module.__file__)
        return node_file.parent

    def introspect(self, contract_path: Path = None) -> dict:
        node_dir = self._get_node_dir()
        if contract_path is None:
            contract_path = node_dir / "node.onex.yaml"
            if not contract_path.exists():
                contract_path = node_dir / "contract.yaml"
        if not contract_path.exists():
            raise FileNotFoundError(f"No contract file found at {contract_path}")
        with open(contract_path, "r") as f:
            contract = yaml.safe_load(f)
        return contract
