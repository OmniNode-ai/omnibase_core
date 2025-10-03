"""
Contract Service implementation for ModelNodeBase Phase 1 deconstruction.

This service extracts contract loading, parsing, validation, and caching
operations from ModelNodeBase to improve separation of concerns and testability.

Following ONEX standards:
- Protocol-based duck typing implementation
- Fail-fast error handling with OnexError
- Comprehensive logging and metrics
- Strong typing with Pydantic models
"""

from pathlib import Path

from omnibase_core.core.contract_loader import ContractLoader
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event
from omnibase_core.models.core.model_contract_content import ModelContractContent
from omnibase_core.models.core.model_semver import ModelSemVer

from .models.model_contract_cache_entry import ModelContractCacheEntry
from .models.model_contract_service_state import ModelContractServiceState


class ContractService:
    """
    Contract service implementation following ProtocolContractService.

    This service provides contract loading, parsing, validation, and caching
    operations extracted from ModelNodeBase for better separation of concerns.

    Key features:
    - Contract loading with full reference resolution
    - Contract validation and structure verification
    - Performance-optimized caching with staleness detection
    - Contract metadata extraction helpers
    - Comprehensive error handling and logging
    """

    def __init__(
        self,
        cache_enabled: bool = True,
        cache_max_size: int = 100,
        base_path: Path | None = None,
    ):
        """
        Initialize contract service.

        Args:
            cache_enabled: Whether to enable contract caching
            cache_max_size: Maximum number of contracts to cache
            base_path: Base path for contract resolution
        """
        self.state = ModelContractServiceState(
            cache_enabled=cache_enabled,
            cache_max_size=cache_max_size,
        )
        self._base_path = base_path
        self._contract_loader: ContractLoader | None = None

        emit_log_event(
            LogLevel.INFO,
            "ContractService initialized",
            {
                "cache_enabled": cache_enabled,
                "cache_max_size": cache_max_size,
                "base_path": str(base_path) if base_path else None,
            },
        )

    def _get_contract_loader(self, contract_path: Path) -> ContractLoader:
        """Get or create contract loader instance."""
        base_path = self._base_path or contract_path.parent
        if self._contract_loader is None:
            self._contract_loader = ContractLoader(base_path=base_path)
        return self._contract_loader

    def load_contract(self, contract_path: Path) -> ModelContractContent:
        """
        Load and parse a contract from file system.

        Args:
            contract_path: Path to the contract YAML file

        Returns:
            ModelContractContent: Fully parsed contract with all references resolved

        Raises:
            OnexError: If contract loading or parsing fails
        """
        contract_path = contract_path.resolve()
        contract_path_str = str(contract_path)

        try:
            # Check cache first if enabled
            if self.state.cache_enabled:
                cached_contract = self.get_cached_contract(contract_path)
                if cached_contract is not None:
                    self.state.record_cache_hit()
                    emit_log_event(
                        LogLevel.DEBUG,
                        f"Contract loaded from cache: {contract_path}",
                        {"contract_path": contract_path_str, "cache_hit": True},
                    )
                    return cached_contract

                self.state.record_cache_miss()

            # Load contract using ContractLoader
            contract_loader = self._get_contract_loader(contract_path)
            contract_content = contract_loader.load_contract(contract_path)

            # Cache if enabled
            if self.state.cache_enabled:
                self.cache_contract(contract_path, contract_content)

            self.state.record_load()

            emit_log_event(
                LogLevel.INFO,
                f"Contract loaded successfully: {contract_path}",
                {
                    "contract_path": contract_path_str,
                    "node_name": contract_content.node_name,
                    "has_dependencies": hasattr(contract_content, "dependencies")
                    and contract_content.dependencies is not None,
                },
            )

            return contract_content

        except Exception as e:
            emit_log_event(
                LogLevel.ERROR,
                f"Failed to load contract: {e!s}",
                {"contract_path": contract_path_str, "error": str(e)},
            )
            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"Failed to load contract: {e!s}",
                context={"contract_path": contract_path_str},
            ) from e

    def validate_contract(self, contract: ModelContractContent) -> bool:
        """
        Validate contract structure and content.

        Args:
            contract: Contract to validate

        Returns:
            bool: True if contract is valid, False otherwise

        Raises:
            OnexError: If validation encounters critical errors
        """
        try:
            # Basic required field validation
            required_fields = ["node_name", "tool_specification", "contract_version"]
            for field in required_fields:
                if not hasattr(contract, field) or getattr(contract, field) is None:
                    self.state.record_validation(success=False)
                    emit_log_event(
                        LogLevel.ERROR,
                        f"Contract missing required field: {field}",
                        {
                            "field": field,
                            "node_name": getattr(contract, "node_name", "unknown"),
                        },
                    )
                    return False

            # Tool specification validation
            if not hasattr(contract.tool_specification, "main_tool_class"):
                self.state.record_validation(success=False)
                return False

            # Version validation
            if hasattr(contract, "contract_version"):
                try:
                    self.extract_version(contract)
                except Exception as e:
                    emit_log_event(
                        LogLevel.WARNING,
                        f"Contract version validation warning: {e!s}",
                        {"node_name": contract.node_name, "error": str(e)},
                    )

            self.state.record_validation(success=True)
            return True

        except Exception as e:
            self.state.record_validation(success=False)
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message=f"Contract validation failed: {e!s}",
                context={"node_name": getattr(contract, "node_name", "unknown")},
            ) from e

    def get_cached_contract(
        self,
        contract_path: Path,
    ) -> ModelContractContent | None:
        """
        Retrieve contract from cache if available.

        Args:
            contract_path: Path to the contract file

        Returns:
            Optional[ModelContractContent]: Cached contract or None if not cached
        """
        if not self.state.cache_enabled:
            return None

        contract_path_str = str(contract_path.resolve())
        cache_entry = self.state.cache_entries.get(contract_path_str)

        if cache_entry is None:
            return None

        # Check if cache is stale
        try:
            current_file_time = (
                contract_path.stat().st_mtime if contract_path.exists() else None
            )
        except OSError:
            current_file_time = None

        if cache_entry.is_stale(current_file_time):
            # Remove stale entry
            del self.state.cache_entries[contract_path_str]
            return None

        # Update access metadata and return cached contract
        cache_entry.update_access()
        return cache_entry.contract_content

    def cache_contract(
        self,
        contract_path: Path,
        contract: ModelContractContent,
    ) -> bool:
        """
        Cache a contract for future retrieval.

        Args:
            contract_path: Path to the contract file
            contract: Contract to cache

        Returns:
            bool: True if caching succeeded, False otherwise
        """
        if not self.state.cache_enabled:
            return False

        try:
            contract_path_resolved = contract_path.resolve()
            contract_path_str = str(contract_path_resolved)

            # Get file modification time for staleness detection
            file_modified_time = None
            if contract_path_resolved.exists():
                file_modified_time = contract_path_resolved.stat().st_mtime

            # Create cache entry
            cache_entry = ModelContractCacheEntry.create_from_contract(
                contract_path=contract_path_resolved,
                contract_content=contract,
                file_modified_time=file_modified_time,
            )

            # Check cache size limit
            if len(self.state.cache_entries) >= self.state.cache_max_size:
                evicted_count = self.state.evict_oldest_entries(
                    self.state.cache_max_size - 1,
                )
                if evicted_count > 0:
                    emit_log_event(
                        LogLevel.DEBUG,
                        f"Evicted {evicted_count} cache entries to make room",
                        {
                            "evicted_count": evicted_count,
                            "cache_size": len(self.state.cache_entries),
                        },
                    )

            # Store in cache
            self.state.cache_entries[contract_path_str] = cache_entry

            emit_log_event(
                LogLevel.DEBUG,
                f"Contract cached: {contract_path}",
                {
                    "contract_path": contract_path_str,
                    "cache_size": len(self.state.cache_entries),
                },
            )

            return True

        except Exception as e:
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to cache contract: {e!s}",
                {"contract_path": str(contract_path), "error": str(e)},
            )
            return False

    def clear_cache(self, contract_path: Path | None = None) -> int:
        """
        Clear contract cache.

        Args:
            contract_path: Specific contract to remove, or None to clear all

        Returns:
            int: Number of contracts removed from cache
        """
        if contract_path is not None:
            contract_path_str = str(contract_path.resolve())
            if contract_path_str in self.state.cache_entries:
                del self.state.cache_entries[contract_path_str]
                return 1
            return 0
        return self.state.clear_cache()

    def extract_node_id(self, contract: ModelContractContent) -> str:
        """
        Extract node ID from contract.

        Args:
            contract: Contract to extract ID from

        Returns:
            str: Node identifier

        Raises:
            OnexError: If node ID cannot be extracted
        """
        try:
            if hasattr(contract, "node_name") and contract.node_name:
                return str(contract.node_name)
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message="Contract missing node_name field",
                context={"contract_type": type(contract).__name__},
            )
        except Exception as e:
            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"Failed to extract node ID: {e!s}",
                context={"contract_type": type(contract).__name__},
            ) from e

    def extract_version(self, contract: ModelContractContent) -> ModelSemVer:
        """
        Extract semantic version from contract.

        Args:
            contract: Contract to extract version from

        Returns:
            ModelSemVer: Semantic version object

        Raises:
            OnexError: If version cannot be extracted or parsed
        """
        try:
            # Try node_version first, then contract_version
            version_field = None
            if hasattr(contract, "node_version"):
                version_field = contract.node_version
            elif hasattr(contract, "contract_version"):
                version_field = contract.contract_version
            else:
                raise OnexError(
                    error_code=CoreErrorCode.VALIDATION_ERROR,
                    message="Contract missing version field (node_version or contract_version)",
                    context={"node_name": getattr(contract, "node_name", "unknown")},
                )

            # Convert to ModelSemVer if needed
            if hasattr(version_field, "major"):
                # Already a structured version object
                return ModelSemVer(
                    major=version_field.major,
                    minor=version_field.minor,
                    patch=version_field.patch,
                )
            # Parse string version
            return ModelSemVer.parse(str(version_field))

        except Exception as e:
            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"Failed to extract version: {e!s}",
                context={"node_name": getattr(contract, "node_name", "unknown")},
            ) from e

    def extract_dependencies(
        self,
        contract: ModelContractContent,
    ) -> list[dict[str, str]]:
        """
        Extract dependency list from contract.

        Args:
            contract: Contract to extract dependencies from

        Returns:
            List[Dict[str, str]]: List of dependency specifications
        """
        if hasattr(contract, "dependencies") and contract.dependencies is not None:
            # Convert dependencies to list of dicts if needed
            deps = []
            for dep in contract.dependencies:
                if hasattr(dep, "__dict__"):
                    deps.append(dep.__dict__)
                elif isinstance(dep, dict):
                    deps.append(dep)
                else:
                    deps.append({"name": str(dep)})
            return deps
        return []

    def extract_tool_class_name(self, contract: ModelContractContent) -> str:
        """
        Extract main tool class name from contract.

        Args:
            contract: Contract to extract tool class from

        Returns:
            str: Main tool class name

        Raises:
            OnexError: If tool class name cannot be extracted
        """
        try:
            if hasattr(contract, "tool_specification") and hasattr(
                contract.tool_specification,
                "main_tool_class",
            ):
                return str(contract.tool_specification.main_tool_class)
            raise OnexError(
                error_code=CoreErrorCode.VALIDATION_ERROR,
                message="Contract missing tool_specification.main_tool_class",
                context={"node_name": getattr(contract, "node_name", "unknown")},
            )
        except Exception as e:
            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"Failed to extract tool class name: {e!s}",
                context={"node_name": getattr(contract, "node_name", "unknown")},
            ) from e

    def extract_event_patterns(self, contract: ModelContractContent) -> list[str]:
        """
        Extract event subscription patterns from contract.

        Args:
            contract: Contract to extract patterns from

        Returns:
            List[str]: List of event patterns
        """
        patterns = []
        try:
            contract_dict = contract.__dict__
            if "event_subscriptions" in contract_dict:
                event_subs = contract_dict["event_subscriptions"]
                if isinstance(event_subs, list):
                    for sub in event_subs:
                        if isinstance(sub, dict) and "event_type" in sub:
                            patterns.append(sub["event_type"])
        except Exception as e:
            emit_log_event(
                LogLevel.WARNING,
                f"Failed to extract event patterns: {e!s}",
                {
                    "node_name": getattr(contract, "node_name", "unknown"),
                    "error": str(e),
                },
            )

        return patterns

    def health_check(self) -> dict[str, object]:
        """
        Perform health check on contract service.

        Returns:
            Dict[str, object]: Health check results with status and metrics
        """
        try:
            # Basic functionality test
            test_metrics = {
                "status": "healthy",
                "cache_enabled": self.state.cache_enabled,
                "cache_size": self.state.cache_size,
                "cache_hit_rate": self.state.cache_hit_rate,
                "total_loads": self.state.total_loads,
                "validation_success_rate": self.state.validation_success_rate,
                "service_type": "ContractService",
                "implementation": "v1.0.0",
                "protocol_compliant": True,
            }

            emit_log_event(
                LogLevel.INFO,
                "ContractService health check completed",
                test_metrics,
            )

            return test_metrics

        except Exception as e:
            error_result = {
                "status": "unhealthy",
                "error": str(e),
                "service_type": "ContractService",
            }

            emit_log_event(
                LogLevel.ERROR,
                f"ContractService health check failed: {e!s}",
                error_result,
            )

            return error_result
