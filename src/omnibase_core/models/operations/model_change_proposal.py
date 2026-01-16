"""ModelChangeProposal for representing proposed system changes (OMN-1196).

This module provides a typed model for capturing proposed system changes
including model swaps, configuration changes, and endpoint changes. It is
designed for use in the DEMO feature set for evaluating changes before
they are applied.

Thread Safety:
    This model is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or
    async tasks.

See Also:
    - ModelEffectOperationConfig: Related configuration model pattern
    - ModelAction: Similar factory method and validation patterns

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1196 change proposal feature.
"""

import re
from datetime import UTC, datetime
from typing import Any, ClassVar, Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_change_type import EnumChangeType
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

__all__ = ["ChangeConfigDict", "EnumChangeType", "ModelChangeProposal"]

# Type alias for configuration dictionaries used in change proposals.
# Values can be any JSON-serializable type (str, int, float, bool, list, dict, None).
# Named ChangeConfigDict to avoid conflict with pydantic.ConfigDict.
ChangeConfigDict = dict[str, object]

# =============================================================================
# URL Validation Pattern Components
# =============================================================================
# This regex validates URLs for endpoint_change proposals. It supports:
# - HTTP and HTTPS protocols
# - Domain names with TLDs (e.g., example.com, api.example.co.uk)
# - localhost for local development
# - IPv4 addresses (0.0.0.0 to 255.255.255.255)
# - Simple hostnames without TLD (e.g., internal-server)
# - Optional port numbers (e.g., :8080)
# - Optional paths and query strings
# =============================================================================

# Protocol: http:// or https://
_URL_PROTOCOL = r"^https?://"

# Domain with TLD: e.g., example.com, api.example.co.uk
# - Label: starts with alphanumeric, allows hyphens in middle, ends with alphanumeric
# - Supports multiple subdomains (label + dot repeated)
# - TLD: 2-6 uppercase letters (case-insensitive via re.IGNORECASE)
_URL_DOMAIN_LABEL = r"[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"
_URL_DOMAIN_WITH_TLD = rf"(?:{_URL_DOMAIN_LABEL}\.)+[A-Z]{{2,6}}\.?"

# Localhost: for local development URLs
_URL_LOCALHOST = r"localhost"

# IPv4 address: four octets (0-255) separated by dots
# - Octet pattern: 250-255, 200-249, 0-199 (with optional leading zeros)
_URL_IP_OCTET = r"(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
_URL_IP_ADDRESS = rf"({_URL_IP_OCTET}\.){{3}}{_URL_IP_OCTET}"

# Simple hostname: single label without TLD (e.g., internal-server, db01)
_URL_SIMPLE_HOSTNAME = r"[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?"

# Port: optional colon followed by digits (e.g., :8080, :443)
_URL_PORT = r"(?::\d+)?"

# Path: optional path, query string, or fragment
# - Empty path, single slash, or slash/question followed by non-whitespace
_URL_PATH = r"(?:/?|[/?]\S+)$"

# Combined URL pattern: protocol + host (one of four types) + optional port + optional path
_URL_PATTERN = re.compile(
    _URL_PROTOCOL
    + r"(?:"
    + _URL_DOMAIN_WITH_TLD
    + r"|"
    + _URL_LOCALHOST
    + r"|"
    + _URL_IP_ADDRESS
    + r"|"
    + _URL_SIMPLE_HOSTNAME
    + r")"
    + _URL_PORT
    + _URL_PATH,
    re.IGNORECASE,
)


def _is_valid_url(url: str) -> bool:
    """Check if a string is a valid URL."""
    return bool(_URL_PATTERN.match(url))


class ModelChangeProposal(BaseModel):
    """
    Represents a proposed system change for evaluation.

    This model captures what we want to change, why, and the before/after
    state for comparison. Used in the DEMO feature set for evaluating
    model swaps, config changes, and endpoint changes.

    The model is immutable (frozen=True) after creation, making it thread-safe
    for concurrent read access. Unknown fields are rejected (extra='forbid')
    to ensure strict schema compliance.

    Class Attributes:
        MODEL_NAME_KEY: The configuration key used to identify model names in
            MODEL_SWAP proposals. Defaults to "model_name". Can be overridden
            in subclasses to use a different key (e.g., "model", "model_id").

    Attributes:
        change_type: Type of change being proposed (discriminator field).
        change_id: Unique identifier for this proposal (auto-generated UUID).
        description: Human-readable description of the change.
        before_config: Current configuration state.
        after_config: Proposed configuration state.
        rationale: Why this change is proposed.
        created_at: When the proposal was created (auto-generated).
        proposed_by: Optional identifier of who proposed the change.
        estimated_impact: Optional description of expected improvement.
        rollback_plan: Optional description of how to revert if needed.
        correlation_id: Optional correlation ID for tracking related operations.
        tags: Optional list of tags for categorization.
        is_breaking_change: Whether this change is a breaking change (default False).

    Example:
        >>> proposal = ModelChangeProposal.create(
        ...     change_type="model_swap",
        ...     description="Replace GPT-4 with Claude-3.5",
        ...     before_config={"model": "gpt-4", "provider": "openai"},
        ...     after_config={"model": "claude-3-5-sonnet", "provider": "anthropic"},
        ...     rationale="50% cost reduction with comparable quality",
        ... )
        >>> proposal.change_type
        'model_swap'
        >>> proposal.get_changed_keys()
        {'model', 'provider'}

    To modify a frozen instance, use model_copy():
        >>> modified = proposal.model_copy(update={"rationale": "Updated rationale"})

    .. versionadded:: 0.4.0
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_enum_values=False,
        from_attributes=True,
    )

    # Class constant for the model name key - can be overridden in subclasses
    MODEL_NAME_KEY: ClassVar[str] = "model_name"  # env-var-ok: constant definition

    # Discriminator field FIRST per codebase pattern
    change_type: EnumChangeType = Field(
        ...,
        description="Type of change being proposed",
    )

    change_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this proposal",
    )

    description: str = Field(
        ...,
        min_length=1,
        description="Human-readable description of the change",
    )

    before_config: ChangeConfigDict = Field(
        ...,
        description="Current configuration state",
    )

    after_config: ChangeConfigDict = Field(
        ...,
        description="Proposed configuration state",
    )

    rationale: str = Field(
        ...,
        min_length=1,
        description="Why this change is proposed",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the proposal was created (UTC)",
    )

    proposed_by: str | None = Field(
        default=None,
        description="Who proposed this change",
    )

    estimated_impact: str | None = Field(
        default=None,
        description="Expected improvement from this change",
    )

    rollback_plan: str | None = Field(
        default=None,
        description="How to revert if needed",
    )

    correlation_id: UUID | None = Field(
        default=None,
        description="Correlation ID for tracking related operations",
    )

    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorizing this change proposal",
    )

    is_breaking_change: bool = Field(
        default=False,
        description="Whether this change is a breaking change",
    )

    @field_validator("description", "rationale", mode="after")
    @classmethod
    def _validate_not_whitespace_only(cls, v: str) -> str:
        """Validate that description and rationale are not whitespace-only."""
        if not v.strip():
            raise ValueError("cannot be whitespace-only")
        return v

    @field_validator("before_config", "after_config", mode="after")
    @classmethod
    def _validate_config_not_empty(cls, v: ChangeConfigDict) -> ChangeConfigDict:
        """Validate that before_config and after_config are not empty."""
        if not v:
            raise ValueError("cannot be empty")
        return v

    @model_validator(mode="after")
    def _validate_configs_differ(self) -> Self:
        """
        Validate before_config and after_config are not identical.

        A change proposal must represent an actual change. If the before
        and after configurations are identical, there is nothing to propose.

        Returns:
            Self: The validated model instance

        Raises:
            ModelOnexError: If before_config and after_config are identical
        """
        if self.before_config == self.after_config:
            # Error code rationale: INVALID_INPUT is used because this is a
            # precondition violation on the input data provided by the caller.
            # The two config dictionaries (inputs) must differ - this is a
            # constraint on what constitutes valid input, not a runtime state
            # issue or generic validation failure.
            raise ModelOnexError(
                message="before_config and after_config cannot be identical",
                error_code=EnumCoreErrorCode.INVALID_INPUT,
                change_type=self.change_type,
                change_id=str(self.change_id),
            )
        return self

    @model_validator(mode="after")
    def _validate_change_type_specific(self) -> Self:
        """
        Validate change type-specific requirements.

        Dispatches to the appropriate validation method based on change_type:
        - MODEL_SWAP: Requires 'model' or 'model_name' key in both configs
        - CONFIG_CHANGE: Requires at least one overlapping key between configs
        - ENDPOINT_CHANGE: Requires 'url' or 'endpoint' key with valid URL format

        Returns:
            Self: The validated model instance

        Raises:
            ModelOnexError: If change type-specific validation fails
        """
        if self.change_type == EnumChangeType.MODEL_SWAP:
            self._validate_model_swap()
        elif self.change_type == EnumChangeType.CONFIG_CHANGE:
            self._validate_config_change()
        elif self.change_type == EnumChangeType.ENDPOINT_CHANGE:
            self._validate_endpoint_change()
        return self

    def _validate_model_swap(self) -> None:
        """
        Validate model_swap change type.

        For model_swap, both before_config and after_config must have a 'model'
        or 'model_name' key to identify which models are being swapped.

        Raises:
            ModelOnexError: If 'model' or 'model_name' key is missing from either config
        """
        before_has_model = (
            "model" in self.before_config or "model_name" in self.before_config
        )
        after_has_model = (
            "model" in self.after_config or "model_name" in self.after_config
        )

        if not before_has_model:
            raise ModelOnexError(
                message="model_swap requires 'model' or 'model_name' key in before_config",
                error_code=EnumCoreErrorCode.INVALID_INPUT,
                change_type=self.change_type,
                change_id=str(self.change_id),
                available_keys=list(self.before_config.keys()),
            )

        if not after_has_model:
            raise ModelOnexError(
                message="model_swap requires 'model' or 'model_name' key in after_config",
                error_code=EnumCoreErrorCode.INVALID_INPUT,
                change_type=self.change_type,
                change_id=str(self.change_id),
                available_keys=list(self.after_config.keys()),
            )

    def _validate_config_change(self) -> None:
        """
        Validate config_change change type.

        For config_change, there must be at least one overlapping key between
        before_config and after_config to indicate which parameter(s) are being changed.

        Raises:
            ModelOnexError: If there are no common keys between configs
        """
        before_keys = set(self.before_config.keys())
        after_keys = set(self.after_config.keys())
        overlapping_keys = before_keys & after_keys

        if not overlapping_keys:
            raise ModelOnexError(
                message="config_change requires at least one common key between before_config and after_config",
                error_code=EnumCoreErrorCode.INVALID_INPUT,
                change_type=self.change_type,
                change_id=str(self.change_id),
                before_keys=list(before_keys),
                after_keys=list(after_keys),
            )

    def _validate_endpoint_change(self) -> None:
        """
        Validate endpoint_change change type.

        For endpoint_change, at least one config must have a 'url' or 'endpoint'
        key with a valid URL format.

        Raises:
            ModelOnexError: If no 'url' or 'endpoint' key is found, or if URL format is invalid
        """
        url_keys = ("url", "endpoint")

        # Find URL values in both configs
        # ONEX_EXCLUDE: dict_str_any - filtering arbitrary config dict for URL keys
        before_urls: dict[str, Any] = {
            k: v for k, v in self.before_config.items() if k in url_keys
        }
        after_urls: dict[str, Any] = {
            k: v for k, v in self.after_config.items() if k in url_keys
        }

        # At least one config must have a url or endpoint key
        if not before_urls and not after_urls:
            raise ModelOnexError(
                message="endpoint_change requires 'url' or 'endpoint' key in at least one config",
                error_code=EnumCoreErrorCode.INVALID_INPUT,
                change_type=self.change_type,
                change_id=str(self.change_id),
                before_keys=list(self.before_config.keys()),
                after_keys=list(self.after_config.keys()),
            )

        # Validate URL format for any url/endpoint values found
        for key, value in before_urls.items():
            if not isinstance(value, str):
                raise ModelOnexError(
                    message=f"'{key}' in before_config must be a string, got {type(value).__name__}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
            if not _is_valid_url(value):
                raise ModelOnexError(
                    message=f"Invalid URL format in before_config['{key}']: {value}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )

        for key, value in after_urls.items():
            if not isinstance(value, str):
                raise ModelOnexError(
                    message=f"'{key}' in after_config must be a string, got {type(value).__name__}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )
            if not _is_valid_url(value):
                raise ModelOnexError(
                    message=f"Invalid URL format in after_config['{key}']: {value}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                )

    @classmethod
    def create(
        cls,
        change_type: EnumChangeType | str,
        description: str,
        before_config: ChangeConfigDict,
        after_config: ChangeConfigDict,
        rationale: str,
        *,
        change_id: UUID | None = None,
        proposed_by: str | None = None,
        estimated_impact: str | None = None,
        rollback_plan: str | None = None,
        correlation_id: UUID | None = None,
        tags: list[str] | None = None,
        is_breaking_change: bool = False,
    ) -> "ModelChangeProposal":
        """
        Factory method for creating a change proposal.

        This is the preferred way to create ModelChangeProposal instances
        as it provides a clear, documented API with keyword-only optional
        arguments.

        Args:
            change_type: Type of change (model_swap, config_change, endpoint_change).
                Can be an EnumChangeType enum value or its string value.
            description: Human-readable description
            before_config: Current configuration state
            after_config: Proposed configuration state
            rationale: Why this change is proposed
            change_id: Optional - explicit ID for this proposal
            proposed_by: Optional - who proposed the change
            estimated_impact: Optional - expected improvement
            rollback_plan: Optional - how to revert
            correlation_id: Optional - for tracking related operations
            tags: Optional - list of tags for categorization
            is_breaking_change: Optional - whether this is a breaking change

        Returns:
            A new ModelChangeProposal instance.

        Raises:
            ModelOnexError: If before_config and after_config are identical

        Example:
            >>> proposal = ModelChangeProposal.create(
            ...     change_type="endpoint_change",
            ...     description="Switch to faster API endpoint",
            ...     before_config={"url": "https://api.old.com/v1"},
            ...     after_config={"url": "https://api.new.com/v2"},
            ...     rationale="New endpoint has 2x lower latency",
            ...     proposed_by="system-optimizer",
            ...     estimated_impact="50% latency reduction",
            ... )
        """
        # Convert string to enum if needed
        if isinstance(change_type, str):
            change_type = EnumChangeType(change_type)

        # Build kwargs dict to avoid code duplication while satisfying mypy strict mode
        # ONEX_EXCLUDE: dict_str_any - factory method kwargs for dynamic Pydantic model construction
        kwargs: dict[str, Any] = {
            "change_type": change_type,
            "description": description,
            "before_config": before_config,
            "after_config": after_config,
            "rationale": rationale,
            "proposed_by": proposed_by,
            "estimated_impact": estimated_impact,
            "rollback_plan": rollback_plan,
            "correlation_id": correlation_id,
            "tags": tags if tags is not None else [],
            "is_breaking_change": is_breaking_change,
        }

        # Only include change_id if explicitly provided (otherwise use default_factory)
        if change_id is not None:
            kwargs["change_id"] = change_id

        return cls(**kwargs)

    # ONEX_EXCLUDE: dict_str_any - arbitrary user config dicts with dynamic nested structure
    def _deep_diff_keys(
        self,
        before: dict[str, Any],
        after: dict[str, Any],
        prefix: str = "",
        max_depth: int = 10,
        _current_depth: int = 0,
    ) -> set[str]:
        """
        Recursively compute diff keys for nested dict structures.

        This private helper method traverses nested dictionaries and returns
        dot-separated paths for all changed values. For example, if
        ``config.timeout`` changed, the path "config.timeout" is returned.

        Args:
            before: The before configuration dict (or nested dict)
            after: The after configuration dict (or nested dict)
            prefix: The current path prefix for nested keys (e.g., "parent.")
            max_depth: Maximum recursion depth for nested dict comparison.
                When this depth is reached, nested dicts are compared as
                whole values rather than recursing further. Defaults to 10.
                This provides a defensive limit against stack overflow or
                poor performance with very deeply nested configurations.
            _current_depth: Internal parameter tracking current recursion depth.
                Do not set this directly; it is managed automatically during
                recursive calls.

        Returns:
            Set of dot-separated key paths that differ between before and after.

        Note:
            - Non-dict values are compared directly
            - When a key exists in only one dict, the entire key path is added
            - When both values are dicts, recursion continues (up to max_depth)
            - When one value is a dict and the other is not, the key is added
            - When max_depth is reached, nested dicts are compared as whole
              values and the key is reported as changed if they differ

        .. versionadded:: 0.4.0
        .. versionchanged:: 0.4.0
            Added ``max_depth`` and ``_current_depth`` parameters for
            defensive recursion limits.
        """
        result: set[str] = set()

        before_keys = set(before.keys())
        after_keys = set(after.keys())

        # Keys that exist in only one config
        for key in after_keys - before_keys:
            result.add(f"{prefix}{key}" if prefix else key)

        for key in before_keys - after_keys:
            result.add(f"{prefix}{key}" if prefix else key)

        # Keys that exist in both - check for differences
        for key in before_keys & after_keys:
            before_val = before[key]
            after_val = after[key]
            full_key = f"{prefix}{key}" if prefix else key

            if before_val == after_val:
                continue

            # Both are dicts - recurse if we haven't hit max_depth
            if isinstance(before_val, dict) and isinstance(after_val, dict):
                if _current_depth >= max_depth:
                    # Max depth reached - treat as changed at this level
                    result.add(full_key)
                else:
                    result.update(
                        self._deep_diff_keys(
                            before_val,
                            after_val,
                            prefix=f"{full_key}.",
                            max_depth=max_depth,
                            _current_depth=_current_depth + 1,
                        )
                    )
            else:
                # Values differ (or type changed from/to dict)
                result.add(full_key)

        return result

    def get_changed_keys(
        self, *, deep: bool = False, max_depth: int | None = None
    ) -> set[str]:
        """
        Get the set of keys that differ between before_config and after_config.

        This method identifies:
        - Keys where values differ between before and after
        - Keys that exist only in before_config (removed)
        - Keys that exist only in after_config (added)

        Args:
            deep: If True, recursively compare nested dicts and return
                dot-separated paths (e.g., "config.timeout"). If False (default),
                only compare top-level keys using shallow comparison.
            max_depth: Maximum recursion depth when ``deep=True``. Only applies
                when deep comparison is enabled. When the depth limit is reached,
                nested dicts are compared as whole values rather than recursing
                further. Defaults to 10 if not specified. Ignored when deep=False.

        Returns:
            Set of keys (or dot-separated paths if deep=True) where values differ
            or keys that exist in only one config.

        Example:
            >>> proposal = ModelChangeProposal.create(
            ...     change_type="config_change",
            ...     description="Update settings",
            ...     before_config={"a": 1, "b": 2, "c": 3},
            ...     after_config={"a": 1, "b": 5, "d": 4},
            ...     rationale="Optimize performance",
            ... )
            >>> sorted(proposal.get_changed_keys())
            ['b', 'c', 'd']

        Example with deep comparison:
            >>> proposal = ModelChangeProposal.create(
            ...     change_type="config_change",
            ...     description="Update nested settings",
            ...     before_config={"config": {"timeout": 10, "retries": 3}},
            ...     after_config={"config": {"timeout": 20, "retries": 3}},
            ...     rationale="Increase timeout",
            ... )
            >>> proposal.get_changed_keys(deep=False)
            {'config'}
            >>> proposal.get_changed_keys(deep=True)
            {'config.timeout'}

        .. versionchanged:: 0.4.0
            Added ``deep`` parameter for recursive nested dict comparison.
            Added ``max_depth`` parameter for defensive recursion limits.
        """
        if deep:
            depth = max_depth if max_depth is not None else 10
            return self._deep_diff_keys(
                self.before_config, self.after_config, max_depth=depth
            )

        before_keys = set(self.before_config.keys())
        after_keys = set(self.after_config.keys())

        # Keys that exist in only one config
        added_keys = after_keys - before_keys
        removed_keys = before_keys - after_keys

        # Keys that exist in both but have different values
        common_keys = before_keys & after_keys
        modified_keys = {
            key
            for key in common_keys
            if self.before_config[key] != self.after_config[key]
        }

        return added_keys | removed_keys | modified_keys

    # ONEX_EXCLUDE: dict_str_any - arbitrary user config dicts with dynamic nested structure
    def _get_nested_value(self, config: dict[str, Any], path: str) -> tuple[bool, Any]:
        """
        Get a value from a nested dict using a dot-separated path.

        Args:
            config: The configuration dictionary
            path: Dot-separated path (e.g., "config.timeout")

        Returns:
            Tuple of (found: bool, value: Any). If found is False, value is None.

        .. versionadded:: 0.4.0
        """
        parts = path.split(".")
        current: Any = config
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return (False, None)
            current = current[part]
        return (True, current)

    def get_diff_summary(
        self, *, deep: bool = False, max_depth: int | None = None
    ) -> str:
        """
        Get a human-readable summary of the configuration differences.

        This method produces a formatted string showing:
        - Added keys (in after_config but not in before_config)
        - Removed keys (in before_config but not in after_config)
        - Modified keys (value changed between before and after)

        Args:
            deep: If True, show nested paths (e.g., "config.timeout") for nested
                dict changes. If False (default), only show top-level keys.
            max_depth: Maximum recursion depth when ``deep=True``. Only applies
                when deep comparison is enabled. When the depth limit is reached,
                nested dicts are compared as whole values rather than recursing
                further. Defaults to 10 if not specified. Ignored when deep=False.

        Returns:
            Formatted string showing before/after values for changed keys.

        Example:
            >>> proposal = ModelChangeProposal.create(
            ...     change_type="model_swap",
            ...     description="Upgrade model",
            ...     before_config={"model": "v1", "temp": 0.5},
            ...     after_config={"model": "v2", "temp": 0.7, "top_p": 0.9},
            ...     rationale="Better accuracy",
            ... )
            >>> print(proposal.get_diff_summary())  # doctest: +NORMALIZE_WHITESPACE
            Configuration Changes:
              [+] top_p: 0.9 (added)
              [~] model: 'v1' -> 'v2'
              [~] temp: 0.5 -> 0.7

        Example with deep=True for nested configs:
            >>> proposal = ModelChangeProposal.create(
            ...     change_type="config_change",
            ...     description="Update nested settings",
            ...     before_config={"settings": {"timeout": 10, "retries": 3}},
            ...     after_config={"settings": {"timeout": 20, "retries": 3}},
            ...     rationale="Increase timeout",
            ... )
            >>> print(proposal.get_diff_summary(deep=True))
            Configuration Changes:
              [~] settings.timeout: 10 -> 20

        .. versionchanged:: 0.4.0
            Added ``deep`` parameter for nested path display.
            Added ``max_depth`` parameter for defensive recursion limits.
        """
        if deep:
            depth = max_depth if max_depth is not None else 10
            return self._get_deep_diff_summary(max_depth=depth)

        before_keys = set(self.before_config.keys())
        after_keys = set(self.after_config.keys())

        added_keys = sorted(after_keys - before_keys)
        removed_keys = sorted(before_keys - after_keys)
        common_keys = before_keys & after_keys
        modified_keys = sorted(
            key
            for key in common_keys
            if self.before_config[key] != self.after_config[key]
        )

        lines: list[str] = ["Configuration Changes:"]

        for key in added_keys:
            lines.append(f"  [+] {key}: {self.after_config[key]!r} (added)")

        for key in removed_keys:
            lines.append(f"  [-] {key}: {self.before_config[key]!r} (removed)")

        for key in modified_keys:
            before_val = self.before_config[key]
            after_val = self.after_config[key]
            lines.append(f"  [~] {key}: {before_val!r} -> {after_val!r}")

        if len(lines) == 1:
            lines.append("  (no changes detected)")

        return "\n".join(lines)

    def _get_deep_diff_summary(self, max_depth: int = 10) -> str:
        """
        Get deep diff summary with nested paths.

        This internal helper produces the summary when deep=True is used.
        It uses the _deep_diff_keys method to find all nested changes and
        then formats them appropriately.

        Args:
            max_depth: Maximum recursion depth for nested dict comparison.
                When this depth is reached, nested dicts are compared as
                whole values rather than recursing further. Defaults to 10.

        Returns:
            Formatted string showing nested path changes.

        .. versionadded:: 0.4.0
        .. versionchanged:: 0.4.0
            Added ``max_depth`` parameter for defensive recursion limits.
        """
        changed_paths = sorted(
            self._deep_diff_keys(
                self.before_config, self.after_config, max_depth=max_depth
            )
        )

        lines: list[str] = ["Configuration Changes:"]

        for path in changed_paths:
            before_found, before_val = self._get_nested_value(self.before_config, path)
            after_found, after_val = self._get_nested_value(self.after_config, path)

            if not before_found and after_found:
                lines.append(f"  [+] {path}: {after_val!r} (added)")
            elif before_found and not after_found:
                lines.append(f"  [-] {path}: {before_val!r} (removed)")
            else:
                lines.append(f"  [~] {path}: {before_val!r} -> {after_val!r}")

        if len(lines) == 1:
            lines.append("  (no changes detected)")

        return "\n".join(lines)

    def get_model_names(self) -> dict[str, str | None] | None:
        """
        Extract old and new model names for MODEL_SWAP change type.

        This method is specifically for MODEL_SWAP proposals to extract
        the model names from the before/after configurations. It checks for
        MODEL_NAME_KEY (defaults to "model_name") first, then falls back to
        "model" key for consistency with _validate_model_swap() which accepts
        either key.

        Note:
            Model name values are explicitly coerced to strings using ``str()``.
            This is intentional to handle cases where model names might be stored
            as non-string types in configuration dictionaries (e.g., numeric
            identifiers, enums, or other objects with ``__str__`` implementations).
            The coercion ensures consistent string output regardless of the
            underlying storage type.

        Returns:
            Dictionary with "old_model" and "new_model" keys if change_type
            is MODEL_SWAP, None otherwise. Values are coerced to strings,
            or None if the model name key is not present in the config.

        Example:
            >>> proposal = ModelChangeProposal.create(
            ...     change_type="model_swap",
            ...     description="Upgrade model",
            ...     before_config={"model_name": "gpt-4"},
            ...     after_config={"model_name": "gpt-4-turbo"},
            ...     rationale="Better performance",
            ... )
            >>> proposal.get_model_names()
            {'old_model': 'gpt-4', 'new_model': 'gpt-4-turbo'}
        """
        if self.change_type != EnumChangeType.MODEL_SWAP:
            return None

        # Check for model_name first (preferred), then fall back to model
        old_model = self.before_config.get(
            self.MODEL_NAME_KEY
        ) or self.before_config.get("model")
        new_model = self.after_config.get(self.MODEL_NAME_KEY) or self.after_config.get(
            "model"
        )

        return {
            "old_model": str(old_model) if old_model is not None else None,
            "new_model": str(new_model) if new_model is not None else None,
        }

    @classmethod
    def create_model_swap(
        cls,
        old_model: str,
        new_model: str,
        description: str,
        rationale: str,
        before_config: ChangeConfigDict,
        after_config: ChangeConfigDict,
        *,
        change_id: UUID | None = None,
        proposed_by: str | None = None,
        estimated_impact: str | None = None,
        rollback_plan: str | None = None,
        correlation_id: UUID | None = None,
        tags: list[str] | None = None,
        is_breaking_change: bool = False,
    ) -> "ModelChangeProposal":
        """
        Factory method specifically for creating model swap proposals.

        This is a convenience method that creates a ModelChangeProposal with
        change_type set to MODEL_SWAP and stores the old/new model names
        in the configuration using the MODEL_NAME_KEY class attribute
        (defaults to "model_name"). Subclasses can override MODEL_NAME_KEY
        to use a different configuration key.

        Args:
            old_model: Name of the model being replaced
            new_model: Name of the replacement model
            description: Human-readable description
            rationale: Why this change is proposed
            before_config: Current configuration state
            after_config: Proposed configuration state
            change_id: Optional - explicit ID for this proposal
            proposed_by: Optional - who proposed the change
            estimated_impact: Optional - expected improvement
            rollback_plan: Optional - how to revert
            correlation_id: Optional - for tracking related operations
            tags: Optional - list of tags for categorization
            is_breaking_change: Optional - whether this is a breaking change

        Returns:
            A new ModelChangeProposal instance with MODEL_SWAP type.

        Example:
            >>> proposal = ModelChangeProposal.create_model_swap(
            ...     old_model="gpt-4",
            ...     new_model="gpt-4-turbo",
            ...     description="Upgrade to GPT-4 Turbo",
            ...     rationale="Better performance at lower cost",
            ...     before_config={"model_name": "gpt-4", "temperature": 0.7},
            ...     after_config={"model_name": "gpt-4-turbo", "temperature": 0.5},
            ... )
        """
        # Ensure model name key is in configs for get_model_names() to work
        # (but don't override if already present)
        final_before = dict(before_config)
        final_after = dict(after_config)

        # Use type.__getattribute__ to bypass Pydantic's __getattr__ interception
        # for ClassVar attributes in classmethods
        model_name_key: str = type.__getattribute__(cls, "MODEL_NAME_KEY")
        if model_name_key not in final_before:
            final_before[model_name_key] = old_model
        if model_name_key not in final_after:
            final_after[model_name_key] = new_model

        return cls.create(
            change_type=EnumChangeType.MODEL_SWAP,
            description=description,
            rationale=rationale,
            before_config=final_before,
            after_config=final_after,
            change_id=change_id,
            proposed_by=proposed_by,
            estimated_impact=estimated_impact,
            rollback_plan=rollback_plan,
            correlation_id=correlation_id,
            tags=tags,
            is_breaking_change=is_breaking_change,
        )
