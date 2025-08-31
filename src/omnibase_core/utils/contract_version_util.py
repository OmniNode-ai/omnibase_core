"""
Contract Version Utility - Proper version management for ONEX tools.

This utility provides the correct pattern for tools to access their version
from contract.yaml instead of hardcoding versions. This eliminates the anti-pattern
of manual version creation and ensures version consistency across the framework.

Author: ONEX Framework Team
"""

from pathlib import Path

from omnibase_core.core.contract_loader import ContractLoader
from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.exceptions import OnexError
from omnibase_core.model.core.model_semver import ModelSemVer


class ContractVersionUtil:
    """
    Utility for accessing version information from tool contracts.

    This class implements the correct pattern for version management:
    1. Load version from contract.yaml (single source of truth)
    2. Convert to appropriate format (string or ModelSemVer)
    3. Cache for performance
    4. Eliminate hardcoded versions
    """

    _version_cache = {}  # Cache contract versions for performance

    @classmethod
    def get_node_version_from_contract(cls, contract_path: Path) -> ModelSemVer:
        """
        Get node version as ModelSemVer from contract.yaml.

        This is the correct pattern for tools to get their version:
        - Loads from contract.yaml (single source of truth)
        - Returns ModelSemVer object for output states
        - Caches for performance
        - No hardcoded versions

        Args:
            contract_path: Path to the tool's contract.yaml file

        Returns:
            ModelSemVer: Version from contract's node_version field

        Raises:
            OnexError: If contract cannot be loaded or version is invalid
        """
        # Use cache for performance
        cache_key = str(contract_path)
        if cache_key in cls._version_cache:
            return cls._version_cache[cache_key]

        try:
            # Load contract using ContractLoader
            base_path = contract_path.parent
            loader = ContractLoader(base_path=base_path)
            contract = loader.load_contract(contract_path)

            # Extract version from contract (try node_version first, fallback to contract_version)
            version_field = None
            if hasattr(contract, "node_version"):
                version_field = contract.node_version
            elif hasattr(contract, "contract_version"):
                version_field = contract.contract_version
            else:
                msg = f"Contract missing version field (node_version or contract_version): {contract_path}"
                raise OnexError(
                    msg,
                    CoreErrorCode.VALIDATION_ERROR,
                )

            node_version = version_field

            # Convert to ModelSemVer
            if hasattr(node_version, "major"):
                # Already a structured version object
                version = ModelSemVer(
                    major=node_version.major,
                    minor=node_version.minor,
                    patch=node_version.patch,
                )
            else:
                # Parse string version
                version = ModelSemVer.parse(str(node_version))

            # Cache for future use
            cls._version_cache[cache_key] = version
            return version

        except OnexError:
            raise
        except Exception as e:
            msg = f"Failed to load version from contract {contract_path}: {e!s}"
            raise OnexError(
                msg,
                CoreErrorCode.OPERATION_FAILED,
            ) from e

    @classmethod
    def get_node_version_string(cls, contract_path: Path) -> str:
        """
        Get node version as string from contract.yaml.

        Args:
            contract_path: Path to the tool's contract.yaml file

        Returns:
            str: Version string (e.g., "1.0.0")
        """
        version = cls.get_node_version_from_contract(contract_path)
        return f"{version.major}.{version.minor}.{version.patch}"

    @classmethod
    def get_contract_version_from_contract(cls, contract_path: Path) -> ModelSemVer:
        """
        Get contract version as ModelSemVer from contract.yaml.

        Args:
            contract_path: Path to the tool's contract.yaml file

        Returns:
            ModelSemVer: Version from contract's contract_version field
        """
        # Similar implementation for contract_version field
        cache_key = f"{contract_path}_contract"
        if cache_key in cls._version_cache:
            return cls._version_cache[cache_key]

        try:
            base_path = contract_path.parent
            loader = ContractLoader(base_path=base_path)
            contract = loader.load_contract(contract_path)

            if not hasattr(contract, "contract_version"):
                msg = f"Contract missing contract_version field: {contract_path}"
                raise OnexError(
                    msg,
                    CoreErrorCode.VALIDATION_ERROR,
                )

            contract_version = contract.contract_version

            if hasattr(contract_version, "major"):
                version = ModelSemVer(
                    major=contract_version.major,
                    minor=contract_version.minor,
                    patch=contract_version.patch,
                )
            else:
                version = ModelSemVer.parse(str(contract_version))

            cls._version_cache[cache_key] = version
            return version

        except OnexError:
            raise
        except Exception as e:
            msg = f"Failed to load contract version from {contract_path}: {e!s}"
            raise OnexError(
                msg,
                CoreErrorCode.OPERATION_FAILED,
            ) from e


# Convenience functions for tools
def get_tool_version(contract_path: Path) -> ModelSemVer:
    """
    Convenience function for tools to get their version from contract.

    Usage in tools:
        from omnibase_core.utils.contract_version_util import get_tool_version
        from pathlib import Path

        contract_path = Path(__file__).parent / "contract.yaml"
        version = get_tool_version(contract_path)
    """
    return ContractVersionUtil.get_node_version_from_contract(contract_path)


def get_tool_version_string(contract_path: Path) -> str:
    """
    Convenience function for tools to get their version as string from contract.
    """
    return ContractVersionUtil.get_node_version_string(contract_path)
