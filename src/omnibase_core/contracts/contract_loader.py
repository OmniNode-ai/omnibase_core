# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Contract loader with YAML !include directive support and optional caching.

This module provides contract loading with support for modular contract
composition via the YAML !include tag. Contracts can reference external
YAML files that are resolved and merged during loading.

An optional in-memory cache (ContractLoaderCache) is available for
high-throughput scenarios where the same contract files are loaded
repeatedly. Caching is opt-in and disabled by default.

Security:
    - Path traversal attacks are blocked (relative paths only)
    - Absolute paths are rejected
    - Circular include detection prevents infinite recursion
    - Maximum nesting depth enforced (default: 10)
    - File size limits prevent DoS attacks (default: 1MB)
    - Symlinks are resolved (followed) - the resolved target must be within the base directory

Thread Safety:
    IncludeLoader instances are NOT thread-safe. Create separate instances
    for concurrent use or protect with external synchronization.
    ContractLoaderCache is NOT thread-safe. Use external synchronization
    for concurrent access or create per-thread instances.

Example:
    Basic usage (no caching)::

        from omnibase_core.contracts.contract_loader import load_contract

        # Load contract with includes
        contract = load_contract(Path("contracts/my_node.yaml"))

    Cached usage::

        from omnibase_core.contracts.contract_loader import (
            ContractLoaderCache,
            load_contract_cached,
        )

        # Create a cache with 60-second TTL
        cache = ContractLoaderCache(ttl_seconds=60)

        # Load with caching; repeated calls return the cached result
        contract = load_contract_cached(Path("contracts/my_node.yaml"), cache=cache)
        stats = cache.get_stats()

    Module-level default cache (suitable for process-wide reuse)::

        from omnibase_core.contracts.contract_loader import (
            get_default_cache,
            load_contract_cached,
        )

        contract = load_contract_cached(Path("contracts/my_node.yaml"))

    Contract with include::

        # my_node.yaml
        contract_version:
          major: 1
          minor: 0
          patch: 0
        routing: !include subcontracts/routing.yaml

See Also:
    - OMN-554: Optional caching for contract loading in high-throughput scenarios
    - OMN-1047: YAML !include directive support implementation
    - util_contract_loader.py: Legacy contract loading (without !include)
"""

import time
from pathlib import Path

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.exception_groups import FILE_IO_ERRORS, YAML_PARSING_ERRORS
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.typed_dict.typed_dict_contract_loader_cache_stats import (
    TypedDictContractLoaderCacheStats,
)

# Default configuration constants
DEFAULT_MAX_INCLUDE_DEPTH = 10
DEFAULT_MAX_FILE_SIZE = 1024 * 1024  # 1MB

# Default cache TTL (seconds). None = no expiration.
DEFAULT_CACHE_TTL_SECONDS: int | None = None


class ContractLoaderCache:
    """
    Optional in-memory cache for contract loading in high-throughput scenarios.

    Cache keys incorporate the file path and its mtime so that a modified
    contract is never served stale. Entries optionally expire after a
    configurable TTL.

    Caching is opt-in: pass a ``ContractLoaderCache`` instance to
    ``load_contract_cached()`` to enable it. The module-level default cache
    (accessed via ``get_default_cache()``) is created lazily with
    ``ttl_seconds=None`` (no expiration).

    Thread Safety:
        This class is NOT thread-safe. For concurrent use, either create
        separate instances per thread or protect access with an external lock.

    Attributes:
        _ttl_seconds: Seconds before a cache entry expires, or None for no expiration.
        _store: Internal mapping from cache key to (value, expiry_timestamp).
        _hits: Number of cache hits since last reset.
        _misses: Number of cache misses since last reset.
        _evictions: Number of entries removed due to expiry or explicit invalidation.

    Example:
        .. code-block:: python

            from omnibase_core.contracts.contract_loader import (
                ContractLoaderCache,
                load_contract_cached,
            )

            cache = ContractLoaderCache(ttl_seconds=300)
            contract = load_contract_cached(
                Path("contracts/my_node.yaml"), cache=cache
            )
            stats = cache.get_stats()
            # stats["hits"] == 0, stats["misses"] == 1 after first load

    .. versionadded:: OMN-554
    """

    def __init__(self, ttl_seconds: int | None = DEFAULT_CACHE_TTL_SECONDS) -> None:
        """
        Initialise the cache.

        Args:
            ttl_seconds: Seconds until a cached entry expires.  ``None`` (the
                default) means entries never expire automatically.  A value of
                ``0`` or negative is treated as *no caching* — ``get()`` always
                returns a miss and ``put()`` is a no-op.
        """
        self._ttl_seconds = ttl_seconds
        # key -> (contract_dict, expiry_timestamp | None)
        self._store: dict[str, tuple[dict[str, object], float | None]] = {}
        self._hits: int = 0
        self._misses: int = 0
        self._evictions: int = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_key(self, contract_path: Path) -> str:
        """
        Compute a cache key from path and mtime.

        Including the mtime in the key ensures that file modifications
        automatically produce a cache miss without requiring explicit
        invalidation.

        Args:
            contract_path: Resolved (absolute) path to the contract file.

        Returns:
            A string key in the form ``<absolute_path>:<mtime_ns>``.
        """
        try:
            mtime_ns = contract_path.stat().st_mtime_ns
        except OSError:
            # File does not exist or is inaccessible; use a sentinel mtime.
            mtime_ns = -1
        return f"{contract_path!s}:{mtime_ns}"

    def _is_expired(self, expiry: float | None) -> bool:
        """Return True if the entry has passed its expiry timestamp."""
        if expiry is None:
            return False
        return time.monotonic() > expiry

    def _compute_expiry(self) -> float | None:
        """Return the expiry timestamp for a new entry, or None if no TTL."""
        if self._ttl_seconds is None:
            return None
        return time.monotonic() + self._ttl_seconds

    def _is_disabled(self) -> bool:
        """Return True if TTL is zero or negative (caching disabled)."""
        return self._ttl_seconds is not None and self._ttl_seconds <= 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, contract_path: Path) -> dict[str, object] | None:
        """
        Retrieve a cached contract, or return ``None`` on miss/expiry.

        Expired entries are lazily removed on access.

        Args:
            contract_path: Resolved path to the contract file.

        Returns:
            The cached contract dictionary, or ``None`` if not found or expired.
        """
        if self._is_disabled():
            self._misses += 1
            return None

        key = self._make_key(contract_path)
        entry = self._store.get(key)

        if entry is None:
            self._misses += 1
            return None

        value, expiry = entry
        if self._is_expired(expiry):
            del self._store[key]
            self._evictions += 1
            self._misses += 1
            return None

        self._hits += 1
        return value

    def put(self, contract_path: Path, contract: dict[str, object]) -> None:
        """
        Store a contract in the cache.

        A no-op when TTL is zero or negative.

        Args:
            contract_path: Resolved path used to generate the cache key.
            contract: The loaded contract dictionary to cache.
        """
        if self._is_disabled():
            return

        key = self._make_key(contract_path)
        expiry = self._compute_expiry()
        self._store[key] = (contract, expiry)

    def invalidate(self, contract_path: Path) -> bool:
        """
        Remove a specific contract from the cache.

        Args:
            contract_path: Path whose entry should be removed.

        Returns:
            ``True`` if an entry was removed, ``False`` if it was not present.
        """
        key = self._make_key(contract_path)
        if key in self._store:
            del self._store[key]
            self._evictions += 1
            return True
        return False

    def clear(self) -> int:
        """
        Remove all entries from the cache.

        Returns:
            Number of entries removed.
        """
        count = len(self._store)
        self._store.clear()
        self._evictions += count
        return count

    def get_stats(self) -> TypedDictContractLoaderCacheStats:
        """
        Return current cache statistics.

        Does NOT trigger expiry cleanup; call ``evict_expired()`` explicitly
        if you want accurate ``entries`` counts.

        Returns:
            A :class:`TypedDictContractLoaderCacheStats` with fields:
            - ``enabled``: True unless TTL is zero or negative.
            - ``entries``: Current number of stored entries (may include expired).
            - ``hits``: Cumulative hit count.
            - ``misses``: Cumulative miss count.
            - ``evictions``: Cumulative eviction count (expiry + explicit).
            - ``hit_ratio``: hits / (hits + misses), or 0.0 if no lookups.
        """
        total = self._hits + self._misses
        hit_ratio = self._hits / total if total > 0 else 0.0
        return TypedDictContractLoaderCacheStats(
            enabled=not self._is_disabled(),
            entries=len(self._store),
            hits=self._hits,
            misses=self._misses,
            evictions=self._evictions,
            hit_ratio=hit_ratio,
        )

    def evict_expired(self) -> int:
        """
        Remove all expired entries from the cache.

        Returns:
            Number of entries evicted.
        """
        now = time.monotonic()
        expired = [
            k
            for k, (_, expiry) in self._store.items()
            if expiry is not None and now > expiry
        ]
        for k in expired:
            del self._store[k]
        self._evictions += len(expired)
        return len(expired)

    def reset_stats(self) -> None:
        """Reset hit/miss/eviction counters without clearing cached data."""
        self._hits = 0
        self._misses = 0
        self._evictions = 0


# ---------------------------------------------------------------------------
# Module-level default cache (lazily initialised, process-wide singleton)
# ---------------------------------------------------------------------------

_default_cache: ContractLoaderCache | None = None


def get_default_cache() -> ContractLoaderCache:
    """
    Return the module-level default ``ContractLoaderCache`` instance.

    The default cache is created lazily on first access with
    ``ttl_seconds=None`` (entries never expire). It is suitable for
    process-wide reuse when contract files are not expected to change
    during the process lifetime.

    For time-limited caching or per-request caches, create a dedicated
    ``ContractLoaderCache`` instance instead.

    Returns:
        The process-wide default ``ContractLoaderCache``.
    """
    global _default_cache  # module-level singleton
    if _default_cache is None:
        _default_cache = ContractLoaderCache(ttl_seconds=None)
    return _default_cache


def _validate_file_size(
    file_path: Path, max_file_size: int, path_label: str = "File"
) -> None:
    """
    Validate that a file does not exceed the maximum allowed size.

    Args:
        file_path: Path to the file to check.
        max_file_size: Maximum allowed file size in bytes.
        path_label: Label for error messages (e.g., "Include file", "Contract file").

    Raises:
        ModelOnexError: If file exceeds size limit with VALIDATION_ERROR code.
    """
    file_size = file_path.stat().st_size
    if file_size > max_file_size:
        raise ModelOnexError(
            message=f"{path_label} too large: {file_size} bytes (max: {max_file_size})",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            context={
                "file_path": str(file_path),
                "file_size": file_size,
                "max_file_size": max_file_size,
            },
        )


class IncludeLoader(yaml.SafeLoader):
    """
    YAML loader with !include tag support for modular contract composition.

    This loader extends SafeLoader to add support for the !include tag,
    which allows contracts to reference and include content from external
    YAML files.

    Security features:
        - Only relative paths within the base directory are allowed
        - Absolute paths are blocked
        - Path traversal (../) is blocked
        - Circular includes are detected and prevented
        - Maximum nesting depth is enforced

    Attributes:
        base_path: Base directory for resolving relative include paths.
        include_stack: Stack of currently loading files for cycle detection.
        max_depth: Maximum nesting depth for includes.
        max_file_size: Maximum file size in bytes.

    Example:
        >>> loader = IncludeLoader(content, base_path=Path("contracts/"))
        >>> loader.include_stack = set()
        >>> data = loader.get_single_data()
    """

    base_path: Path
    include_stack: set[Path]
    max_depth: int
    max_file_size: int
    current_depth: int

    def __init__(
        self,
        stream: str,
        *,
        base_path: Path,
        include_stack: set[Path] | None = None,
        max_depth: int = DEFAULT_MAX_INCLUDE_DEPTH,
        max_file_size: int = DEFAULT_MAX_FILE_SIZE,
        current_depth: int = 0,
    ) -> None:
        """
        Initialize the include loader.

        Args:
            stream: YAML content string to parse.
            base_path: Base directory for resolving relative includes.
            include_stack: Set of file paths currently being loaded (for cycle detection).
            max_depth: Maximum include nesting depth.
            max_file_size: Maximum file size in bytes.
            current_depth: Current nesting depth.
        """
        super().__init__(stream)
        self.base_path = base_path
        self.include_stack = include_stack if include_stack is not None else set()
        self.max_depth = max_depth
        self.max_file_size = max_file_size
        self.current_depth = current_depth


def _include_constructor(loader: IncludeLoader, node: yaml.Node) -> object:
    """
    YAML constructor for !include tag.

    Handles loading and including content from external YAML files.

    Args:
        loader: The IncludeLoader instance.
        node: The YAML node containing the include path.

    Returns:
        The loaded content from the included file.

    Raises:
        ModelOnexError: If include path is invalid, file not found,
            circular reference detected, or depth limit exceeded.
    """
    # Validate node type - !include should only be used with scalar values
    if not isinstance(node, yaml.ScalarNode):
        raise ModelOnexError(
            message=f"!include requires a scalar value, got {type(node).__name__}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            context={"node_type": type(node).__name__},
        )
    include_path_str = loader.construct_scalar(node)
    if not isinstance(include_path_str, str):
        raise ModelOnexError(
            message=f"Include path must be a string, got {type(include_path_str).__name__}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            context={"node_value": str(node.value)},
        )

    # Validate path security
    _validate_include_path(include_path_str)

    # Resolve the include path relative to the base path
    include_path = (loader.base_path / include_path_str).resolve()

    # Verify the resolved path is still within base_path (security check)
    try:
        include_path.relative_to(loader.base_path.resolve())
    except ValueError:
        raise ModelOnexError(
            message=f"Include path escapes base directory: {include_path_str}",
            error_code=EnumCoreErrorCode.SECURITY_VIOLATION,
            context={
                "include_path": include_path_str,
                "base_path": str(loader.base_path),
                "resolved_path": str(include_path),
            },
        )

    # Check for circular includes
    if include_path in loader.include_stack:
        cycle_path = " -> ".join(str(p) for p in loader.include_stack)
        raise ModelOnexError(
            message=f"Circular include detected: {include_path}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            context={
                "circular_path": str(include_path),
                "include_chain": cycle_path,
            },
        )

    # Check depth limit
    if loader.current_depth >= loader.max_depth:
        raise ModelOnexError(
            message=f"Maximum include depth ({loader.max_depth}) exceeded",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            context={
                "max_depth": loader.max_depth,
                "current_depth": loader.current_depth,
                "include_path": include_path_str,
            },
        )

    # Check file exists
    if not include_path.exists():
        raise ModelOnexError(
            message=f"Include file not found: {include_path_str}",
            error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
            context={
                "include_path": include_path_str,
                "resolved_path": str(include_path),
                "base_path": str(loader.base_path),
            },
        )

    # Check file size
    _validate_file_size(include_path, loader.max_file_size, "Include file")

    # Load the included file
    try:
        content = include_path.read_text(encoding="utf-8")
    except FILE_IO_ERRORS as e:
        # boundary-ok: convert OS-level file read errors to structured ModelOnexError
        raise ModelOnexError(
            message=f"Cannot read include file: {e}",
            error_code=EnumCoreErrorCode.FILE_READ_ERROR,
            context={
                "include_path": include_path_str,
                "error": str(e),
            },
        ) from e

    # Handle empty files
    if not content.strip():
        return None

    # Create new loader with updated include stack
    new_stack = loader.include_stack.copy()
    new_stack.add(include_path)

    try:
        nested_loader = IncludeLoader(
            content,
            base_path=include_path.parent,
            include_stack=new_stack,
            max_depth=loader.max_depth,
            max_file_size=loader.max_file_size,
            current_depth=loader.current_depth + 1,
        )
        result = nested_loader.get_single_data()
        # NOTE(OMN-1302): YAML SafeLoader.dispose() is untyped in PyYAML stubs. Safe because method exists.
        nested_loader.dispose()  # type: ignore[no-untyped-call]
        return result
    except YAML_PARSING_ERRORS as e:
        # boundary-ok: convert YAML syntax errors to structured ModelOnexError
        raise ModelOnexError(
            message=f"Invalid YAML in include file: {e}",
            error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
            context={
                "include_path": include_path_str,
                "yaml_error": str(e),
            },
        ) from e


def _validate_include_path(path_str: str) -> None:
    """
    Validate that an include path is safe and secure.

    Args:
        path_str: The include path string to validate.

    Raises:
        ModelOnexError: If the path is not safe (absolute, traversal, etc.).
    """
    # Block empty paths
    if not path_str or not path_str.strip():
        raise ModelOnexError(
            message="Include path cannot be empty",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            context={"include_path": path_str},
        )

    # Block absolute paths
    if Path(path_str).is_absolute():
        raise ModelOnexError(
            message=f"Absolute paths not allowed in includes: {path_str}",
            error_code=EnumCoreErrorCode.SECURITY_VIOLATION,
            context={"include_path": path_str},
        )

    # Block path traversal attempts
    normalized = Path(path_str).as_posix()
    if normalized.startswith("../") or "/../" in normalized:
        raise ModelOnexError(
            message=f"Path traversal not allowed in includes: {path_str}",
            error_code=EnumCoreErrorCode.SECURITY_VIOLATION,
            context={"include_path": path_str},
        )


# Register the !include constructor
IncludeLoader.add_constructor("!include", _include_constructor)


def load_contract(
    contract_path: Path,
    *,
    max_depth: int = DEFAULT_MAX_INCLUDE_DEPTH,
    max_file_size: int = DEFAULT_MAX_FILE_SIZE,
) -> dict[str, object]:
    """
    Load a YAML contract with !include directive support.

    This function loads a YAML contract file and processes any !include
    directives, recursively loading and merging referenced files.

    Thread Safety:
        This function is thread-safe. Each call creates a new IncludeLoader
        instance with its own state, so there is no shared mutable state
        between concurrent calls.

    Symlink Handling:
        Symlinks in contract paths and include paths are resolved (followed).
        The resolved target path must be within the allowed base directory;
        symlinks that escape the base directory are rejected with a
        SECURITY_VIOLATION error.

    Args:
        contract_path: Path to the contract YAML file.
        max_depth: Maximum nesting depth for includes (default: 10).
        max_file_size: Maximum file size in bytes (default: 1MB).

    Returns:
        The loaded contract as a dictionary.

    Raises:
        ModelOnexError: If the contract cannot be loaded or parsed.

    Example:
        >>> contract = load_contract(Path("contracts/my_node.yaml"))
        >>> print(contract["node_name"])
    """
    contract_path = contract_path.resolve()

    if not contract_path.exists():
        raise ModelOnexError(
            message=f"Contract file not found: {contract_path}",
            error_code=EnumCoreErrorCode.FILE_NOT_FOUND,
            context={"contract_path": str(contract_path)},
        )

    # Check file size
    _validate_file_size(contract_path, max_file_size, "Contract file")

    try:
        content = contract_path.read_text(encoding="utf-8")
    except FILE_IO_ERRORS as e:
        # boundary-ok: convert OS-level file read errors to structured ModelOnexError
        raise ModelOnexError(
            message=f"Cannot read contract file: {e}",
            error_code=EnumCoreErrorCode.FILE_READ_ERROR,
            context={
                "contract_path": str(contract_path),
                "error": str(e),
            },
        ) from e

    # Handle empty files
    if not content.strip():
        return {}

    # Create initial include stack with the main contract path
    include_stack: set[Path] = {contract_path}

    try:
        loader = IncludeLoader(
            content,
            base_path=contract_path.parent,
            include_stack=include_stack,
            max_depth=max_depth,
            max_file_size=max_file_size,
            current_depth=0,
        )
        result = loader.get_single_data()
        # NOTE(OMN-1302): YAML SafeLoader.dispose() is untyped in PyYAML stubs. Safe because method exists.
        loader.dispose()  # type: ignore[no-untyped-call]

        if result is None:
            return {}

        if not isinstance(result, dict):
            raise ModelOnexError(
                message=f"Contract must be a YAML mapping, got {type(result).__name__}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={
                    "contract_path": str(contract_path),
                    "result_type": type(result).__name__,
                },
            )

        return result

    except YAML_PARSING_ERRORS as e:
        # boundary-ok: convert YAML syntax errors to structured ModelOnexError
        raise ModelOnexError(
            message=f"Invalid YAML in contract file: {e}",
            error_code=EnumCoreErrorCode.CONFIGURATION_PARSE_ERROR,
            context={
                "contract_path": str(contract_path),
                "yaml_error": str(e),
            },
        ) from e


def load_contract_cached(
    contract_path: Path,
    *,
    cache: ContractLoaderCache | None = None,
    max_depth: int = DEFAULT_MAX_INCLUDE_DEPTH,
    max_file_size: int = DEFAULT_MAX_FILE_SIZE,
) -> dict[str, object]:
    """
    Load a YAML contract with optional in-memory caching.

    On a cache hit the cached dictionary is returned immediately without
    reading or parsing the file again.  Cache keys include the file's
    ``mtime`` so that on-disk changes automatically produce a miss.

    If ``cache`` is ``None``, the module-level default cache (see
    ``get_default_cache()``) is used.  To disable caching entirely, pass
    a ``ContractLoaderCache`` with ``ttl_seconds=0``.

    Thread Safety:
        The underlying ``load_contract()`` call is thread-safe.
        ``ContractLoaderCache`` itself is NOT thread-safe; use an external
        lock if multiple threads share the same cache instance.

    Args:
        contract_path: Path to the contract YAML file.
        cache: ``ContractLoaderCache`` instance to use.  Defaults to the
            module-level default cache.
        max_depth: Maximum nesting depth for !include directives (default: 10).
        max_file_size: Maximum file size in bytes (default: 1MB).

    Returns:
        The loaded (and possibly cached) contract as a dictionary.

    Raises:
        ModelOnexError: If the contract cannot be loaded or parsed.

    Example:
        .. code-block:: python

            from pathlib import Path
            from omnibase_core.contracts.contract_loader import (
                ContractLoaderCache,
                load_contract_cached,
            )

            cache = ContractLoaderCache(ttl_seconds=300)
            contract = load_contract_cached(
                Path("contracts/my_node.yaml"), cache=cache
            )
            # Second call returns cached result without I/O
            contract2 = load_contract_cached(
                Path("contracts/my_node.yaml"), cache=cache
            )
            assert cache.get_stats()["hits"] == 1

    .. versionadded:: OMN-554
    """
    resolved = contract_path.resolve()
    effective_cache = cache if cache is not None else get_default_cache()

    # Try cache first
    cached_value = effective_cache.get(resolved)
    if cached_value is not None:
        return cached_value

    # Cache miss: load from disk
    result = load_contract(resolved, max_depth=max_depth, max_file_size=max_file_size)

    # Store in cache (put() is a no-op when cache is disabled)
    effective_cache.put(resolved, result)

    return result
