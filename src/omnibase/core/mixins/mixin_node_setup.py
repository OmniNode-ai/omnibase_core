from pathlib import Path

from omnibase.model.core.model_state_contract import load_state_contract_from_file


class MixinNodeSetup:
    """
    Canonical mixin for ONEX nodes to provide contract and metadata access.
    Usage: Inherit in your node class to get contract, node_id, node_version, node_onex_yaml_path, etc.

    By default, contract and metadata paths are resolved relative to the node's directory.
    To override the node directory, set self._node_directory in your node's __init__.
    """

    @property
    def node_directory(self):
        # Allow override by setting self._node_directory in the node class
        if hasattr(self, "_node_directory"):
            return self._node_directory
        # Fallback: try to infer from the concrete class's file
        import inspect

        frame = inspect.currentframe()
        # Walk up the stack to find the first non-mixin class
        for cls in type(self).mro():
            if cls is not MixinNodeSetup and hasattr(cls, "__module__"):
                try:
                    mod = __import__(cls.__module__, fromlist=["__file__"])
                    return Path(mod.__file__).parent
                except Exception:
                    continue
        # Fallback to mixin's own directory
        return Path(__file__).parent

    @property
    def contract_path(self):
        return self.node_directory / "contract.yaml"

    @property
    def node_onex_yaml_path(self):
        return self.node_directory / "node.onex.yaml"

    @property
    def contract(self):
        if not hasattr(self, "_contract"):
            self._contract = load_state_contract_from_file(self.contract_path)
        return self._contract

    @property
    def node_id(self):
        return self.contract.node_name

    @property
    def node_version(self):
        return self.contract.node_version

    @property
    def contract_version(self):
        return self.contract.contract_version
