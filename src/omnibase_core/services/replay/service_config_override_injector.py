"""Service for injecting configuration overrides during replay.

Uses centralized exception groups from omnibase_core.errors.exception_groups.

This module provides the ServiceConfigOverrideInjector class for validating,
previewing, and applying configuration overrides to handler configurations,
environment variables, and replay contexts.

Thread Safety:
    ServiceConfigOverrideInjector is stateless (only strict_mode set at init)
    and thread-safe. All methods are pure functions that do not modify shared
    state. The apply() method always deep-copies configurations before
    modification, ensuring the original is never mutated.

Design:
    The service uses a MISSING sentinel to distinguish between:
    - Path not found (returns MISSING)
    - Path exists but value is None (returns None)

    This enables accurate validation and preview generation.

Architecture:
    Configuration override injection operates at three injection points:

    1. HANDLER_CONFIG: Patches handler configuration models (Pydantic or dict)
       before handler execution begins.

    2. ENVIRONMENT: Creates an environment variable overlay dict without
       mutating os.environ. Caller is responsible for applying the overlay.

    3. CONTEXT: Patches replay context fields on a copy, not the original.

Example:
    >>> from omnibase_core.services.replay.service_config_override_injector import (
    ...     ServiceConfigOverrideInjector,
    ... )
    >>> from omnibase_core.models.replay import ModelConfigOverride, ModelConfigOverrideSet
    >>> from omnibase_core.enums.replay import EnumOverrideInjectionPoint
    >>>
    >>> injector = ServiceConfigOverrideInjector()
    >>> override = ModelConfigOverride(
    ...     path="retry.max_attempts",
    ...     value=5,
    ...     injection_point=EnumOverrideInjectionPoint.HANDLER_CONFIG,
    ... )
    >>> override_set = ModelConfigOverrideSet(overrides=(override,))
    >>> config = {"retry": {"max_attempts": 3}}
    >>>
    >>> # Validate overrides
    >>> validation = injector.validate(override_set, config)
    >>> print(validation.is_valid)
    True
    >>>
    >>> # Preview changes
    >>> preview = injector.preview(override_set, config)
    >>> print(preview.to_markdown())
    ...
    >>>
    >>> # Apply overrides
    >>> result = injector.apply(override_set, config)
    >>> print(result.patched_config)
    {'retry': {'max_attempts': 5}}

Related:
    - OMN-1205: Configuration Override Injection
    - ModelConfigOverrideSet: Collection of overrides
    - ModelReplayContext: Replay context for deterministic execution

.. versionadded:: 0.4.0
    Added Configuration Override Injection (OMN-1205)
"""

import copy
import logging
import re
import types
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel

from omnibase_core.enums.replay.enum_override_injection_point import (
    EnumOverrideInjectionPoint,
)
from omnibase_core.errors.exception_groups import (
    ATTRIBUTE_ACCESS_ERRORS,
    PYDANTIC_MODEL_ERRORS,
)
from omnibase_core.models.replay.model_config_override_field_preview import (
    ModelConfigOverrideFieldPreview,
)
from omnibase_core.models.replay.model_config_override_preview import (
    ModelConfigOverridePreview,
)
from omnibase_core.models.replay.model_config_override_result import (
    ModelConfigOverrideResult,
)
from omnibase_core.models.replay.model_config_override_set import (
    ModelConfigOverrideSet,
)
from omnibase_core.models.replay.model_config_override_validation import (
    ModelConfigOverrideValidation,
)
from omnibase_core.services.replay.service_sentinel_missing import MISSING

logger = logging.getLogger(__name__)


class ServiceConfigOverrideInjector:
    """Service for validating, previewing, and applying configuration overrides.

    Provides validate/preview/apply operations for config overrides during replay.
    All operations are stateless and thread-safe.

    Attributes:
        strict_mode: If True, validation fails on any warning. Default False.
        MAX_PATH_DEPTH: Maximum allowed path depth to prevent DoS attacks.

    Thread Safety:
        This service is stateless (only strict_mode config set at init).
        All methods are pure functions that do not modify shared state.
        The apply() method always deep-copies before modification.

    Example:
        >>> injector = ServiceConfigOverrideInjector()
        >>> result = injector.validate(override_set, config)
        >>> if result.is_valid:
        ...     applied = injector.apply(override_set, config)
    """

    # Maximum path depth to prevent DoS via deeply nested paths
    MAX_PATH_DEPTH: int = 20

    def __init__(self, strict_mode: bool = False) -> None:
        """Initialize the config override injector.

        Args:
            strict_mode: If True, validation fails on any warning.
                Default False allows warnings without failing validation.
        """
        self.strict_mode = strict_mode

    def _is_frozen_pydantic_model(self, obj: Any) -> bool:
        """Check if an object is a frozen Pydantic model.

        Frozen Pydantic models cannot be modified after creation. This method
        detects frozen models by checking the model_config attribute for
        frozen=True setting.

        Args:
            obj: The object to check.

        Returns:
            True if the object is a frozen Pydantic BaseModel, False otherwise.

        Examples:
            >>> from pydantic import BaseModel, ConfigDict
            >>> class FrozenModel(BaseModel):
            ...     model_config = ConfigDict(frozen=True)
            ...     value: int
            >>> injector = ServiceConfigOverrideInjector()
            >>> injector._is_frozen_pydantic_model(FrozenModel(value=1))
            True
            >>> class MutableModel(BaseModel):
            ...     value: int
            >>> injector._is_frozen_pydantic_model(MutableModel(value=1))
            False
        """
        if not isinstance(obj, BaseModel):
            return False

        # Check model_config for frozen setting
        model_config = getattr(obj, "model_config", None)
        if model_config is None:
            return False

        # model_config can be a dict or ConfigDict
        if isinstance(model_config, dict):
            return model_config.get("frozen", False) is True

        # For ConfigDict or other mapping types
        if isinstance(model_config, Mapping):
            return model_config.get("frozen", False) is True

        return False

    def _is_valid_path_syntax(self, path: str) -> tuple[bool, str]:
        """Validate dot-path syntax.

        Checks that the path follows valid dot-notation syntax:
        - Segments separated by dots
        - Each segment is a valid identifier or numeric index
        - Path depth does not exceed MAX_PATH_DEPTH

        Args:
            path: The dot-separated path to validate.

        Returns:
            Tuple of (is_valid, error_message). If valid, error_message is empty.

        Examples:
            >>> injector = ServiceConfigOverrideInjector()
            >>> injector._is_valid_path_syntax("config.timeout")
            (True, '')
            >>> injector._is_valid_path_syntax("items.0.name")
            (True, '')
            >>> injector._is_valid_path_syntax("")
            (False, 'Path cannot be empty')
        """
        if not path:
            return (False, "Path cannot be empty")

        if not path.strip():
            return (False, "Path cannot be whitespace only")

        parts = path.split(".")
        if len(parts) > self.MAX_PATH_DEPTH:
            return (
                False,
                f"Path depth {len(parts)} exceeds maximum {self.MAX_PATH_DEPTH}",
            )

        # Check each segment
        for i, part in enumerate(parts):
            if not part:
                return (False, f"Empty segment at position {i}")

            # Allow numeric segments for array indices
            if part.isdigit():
                continue

            # Check identifier format for non-numeric segments
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", part):
                return (
                    False,
                    f"Invalid path segment '{part}' at position {i}: "
                    "must be a valid identifier or numeric index",
                )

        return (True, "")

    def _get_value_at_path(self, obj: Any, path: str | None) -> Any:
        """Get value at a dot-separated path.

        Traverses nested structures (dict, Pydantic model, list/tuple) to
        retrieve the value at the specified path. Returns MISSING sentinel
        if the path does not exist.

        Args:
            obj: The object to traverse (dict, Pydantic model, or list).
            path: The dot-separated path to the value.

        Returns:
            The value at the path, or MISSING if the path does not exist.

        Thread Safety:
            This is a pure function that does not modify the input object.

        Examples:
            >>> injector = ServiceConfigOverrideInjector()
            >>> data = {"config": {"timeout": 30}}
            >>> injector._get_value_at_path(data, "config.timeout")
            30
            >>> injector._get_value_at_path(data, "config.missing")
            <MISSING>
        """
        # Handle None/invalid inputs gracefully
        if obj is None or path is None:
            return MISSING

        try:
            parts = path.split(".")
        except AttributeError:
            # boundary-ok: path is not a string-like object
            return MISSING

        current: Any = obj

        for part in parts:
            if current is MISSING:
                return MISSING

            try:
                if isinstance(current, dict):
                    current = current.get(part, MISSING)
                elif isinstance(current, BaseModel):
                    current = getattr(current, part, MISSING)
                elif isinstance(current, (list, tuple)) and part.isdigit():
                    idx = int(part)
                    if 0 <= idx < len(current):
                        current = current[idx]
                    else:
                        current = MISSING
                else:
                    # Try getattr for other objects
                    current = getattr(current, part, MISSING)
            except ATTRIBUTE_ACCESS_ERRORS as e:
                # boundary-ok: handle edge cases like non-subscriptable types
                logger.debug(
                    "Path traversal failed at '%s': %s",
                    part,
                    str(e),
                )
                return MISSING

        return current

    def _set_value_at_path(self, obj: Any, path: str, value: Any) -> tuple[bool, str]:
        """Set value at a dot-separated path.

        Traverses nested structures and sets the value at the specified path.
        Creates intermediate dictionaries if they don't exist.

        Args:
            obj: The object to modify (must be a dict or mutable structure).
            path: The dot-separated path to set.
            value: The value to set.

        Returns:
            Tuple of (success, error_message). If successful, error_message is empty.

        Warning:
            This method modifies the input object in place. Always use on a
            deep copy to avoid mutating the original.

        Examples:
            >>> injector = ServiceConfigOverrideInjector()
            >>> data = {"config": {"timeout": 30}}
            >>> injector._set_value_at_path(data, "config.timeout", 60)
            (True, '')
            >>> data["config"]["timeout"]
            60
        """
        # Handle None object gracefully
        if obj is None:
            return (False, "Cannot set value on None object")

        parts = path.split(".")

        current: Any = obj

        # Navigate to parent of target
        for i, part in enumerate(parts[:-1]):
            try:
                if isinstance(current, dict):
                    if part not in current:
                        # Create intermediate dict
                        current[part] = {}
                    current = current[part]
                elif isinstance(current, BaseModel):
                    # Pydantic models are typically frozen, need special handling
                    child = getattr(current, part, MISSING)
                    if child is MISSING:
                        return (
                            False,
                            f"Cannot create path segment '{part}' in frozen Pydantic model",
                        )
                    current = child
                elif isinstance(current, (list, tuple)) and part.isdigit():
                    idx = int(part)
                    if 0 <= idx < len(current):
                        current = current[idx]
                    else:
                        return (
                            False,
                            f"Index {idx} out of bounds for list at '{'.'.join(parts[:i])}'",
                        )
                else:
                    return (
                        False,
                        f"Cannot traverse non-container type {type(current).__name__} "
                        f"at path segment '{part}'",
                    )
            except ATTRIBUTE_ACCESS_ERRORS as e:
                # boundary-ok: handle edge cases during path navigation
                return (
                    False,
                    f"Path navigation failed at '{part}': {e}",
                )

        # Set the final value
        final_part = parts[-1]
        try:
            if isinstance(current, dict):
                current[final_part] = value
                return (True, "")
            elif isinstance(current, BaseModel):
                # Pydantic models: need to check if field exists and is settable
                if not hasattr(current, final_part):
                    return (
                        False,
                        f"Field '{final_part}' does not exist on Pydantic model "
                        f"{type(current).__name__}",
                    )
                try:
                    setattr(current, final_part, value)
                    return (True, "")
                except PYDANTIC_MODEL_ERRORS as e:
                    # catch-all-ok: Pydantic models may reject values for various reasons
                    return (
                        False,
                        f"Cannot set field '{final_part}' on Pydantic model: {e}",
                    )
            elif isinstance(current, list) and final_part.isdigit():
                idx = int(final_part)
                if 0 <= idx < len(current):
                    current[idx] = value
                    return (True, "")
                else:
                    return (
                        False,
                        f"Index {idx} out of bounds for list",
                    )
            else:
                return (
                    False,
                    f"Cannot set value on {type(current).__name__}",
                )
        except ATTRIBUTE_ACCESS_ERRORS as e:
            # boundary-ok: handle edge cases during value assignment
            return (
                False,
                f"Failed to set value at '{final_part}': {e}",
            )

    def _deep_copy_config(self, config: Any) -> Any:
        """Deep copy a configuration object.

        Handles both dict and Pydantic model configurations.
        For mutable Pydantic models, uses model_copy(deep=True).
        For frozen Pydantic models, converts to dict since frozen models
        cannot be modified after creation.

        Args:
            config: The configuration to copy.

        Returns:
            A deep copy of the configuration. For frozen Pydantic models,
            returns a dict representation that can be modified.

        Thread Safety:
            This is a pure function that creates a new object.

        Note:
            Frozen Pydantic models are detected early and converted to dicts
            to allow modification. This is intentional - if you need to apply
            overrides to a frozen model, the result must be a dict since the
            original frozen model's copy would also be frozen.
        """
        if isinstance(config, BaseModel):
            # Check for frozen models first - they need special handling
            if self._is_frozen_pydantic_model(config):
                # Frozen models cannot be modified, so convert to dict
                # This allows overrides to be applied to the dict representation
                logger.debug(
                    "Converting frozen Pydantic model %s to dict for override application",
                    type(config).__name__,
                )
                return copy.deepcopy(config.model_dump())
            # Mutable Pydantic model - use model_copy
            return config.model_copy(deep=True)
        else:
            return copy.deepcopy(config)

    def validate(
        self,
        overrides: ModelConfigOverrideSet | None,
        config: Any,
        injection_point: EnumOverrideInjectionPoint | None = None,
    ) -> ModelConfigOverrideValidation:
        """Validate configuration overrides against a config.

        Checks path existence, type compatibility, and override consistency.
        Does NOT modify the original configuration.

        Args:
            overrides: The set of overrides to validate. If None, returns
                a validation result with is_valid=False.
            config: The target configuration to validate against. If None,
                all paths will be marked as non-existent.
            injection_point: Optional filter to only validate overrides for
                a specific injection point. If None, validates all overrides.

        Returns:
            ModelConfigOverrideValidation with validation results.

        Thread Safety:
            Pure function - does not modify any state.

        Example:
            >>> validation = injector.validate(override_set, config)
            >>> if validation.is_valid:
            ...     print("All overrides are valid")
            >>> else:
            ...     for v in validation.violations:
            ...         print(f"Error: {v}")
        """
        # Handle None overrides gracefully
        if overrides is None:
            return ModelConfigOverrideValidation(
                is_valid=False,
                violations=("Overrides cannot be None",),
                warnings=(),
                suggestions=(),
                paths_validated=0,
                type_checks_passed=0,
            )

        violations: list[str] = []
        warnings: list[str] = []
        suggestions: list[str] = []
        paths_validated = 0
        type_checks_passed = 0

        # Handle None config - all paths will be treated as non-existent
        if config is None:
            warnings.append("Config is None - all paths will be treated as new")

        # Filter overrides by injection point if specified
        overrides_to_check = overrides.overrides
        if injection_point is not None:
            overrides_to_check = tuple(
                o for o in overrides.overrides if o.injection_point == injection_point
            )

        for override in overrides_to_check:
            paths_validated += 1

            # Validate path syntax
            is_valid_syntax, syntax_error = self._is_valid_path_syntax(override.path)
            if not is_valid_syntax:
                violations.append(
                    f"Invalid path syntax '{override.path}': {syntax_error}"
                )
                continue

            # Check if path exists
            current_value = self._get_value_at_path(config, override.path)

            if current_value is MISSING:
                # Path doesn't exist - this could be creating a new path
                if override.injection_point == EnumOverrideInjectionPoint.ENVIRONMENT:
                    # Environment overrides can create new keys
                    suggestions.append(
                        f"Path '{override.path}' will be created as new environment variable"
                    )
                else:
                    warnings.append(
                        f"Path '{override.path}' does not exist in config (will be created)"
                    )
            else:
                # Path exists - check type compatibility
                current_type = type(current_value).__name__
                new_type = type(override.value).__name__

                if current_type != new_type:
                    # Type mismatch
                    if override.value is None:
                        # Setting to None is usually acceptable
                        suggestions.append(
                            f"Path '{override.path}' will be set to None "
                            f"(was {current_type})"
                        )
                    elif isinstance(current_value, (int, float)) and isinstance(
                        override.value, (int, float)
                    ):
                        # Numeric type conversion is acceptable
                        type_checks_passed += 1
                    else:
                        warnings.append(
                            f"Type mismatch at '{override.path}': "
                            f"changing from {current_type} to {new_type}"
                        )
                else:
                    type_checks_passed += 1

        # Determine overall validity
        is_valid = len(violations) == 0
        if self.strict_mode and warnings:
            is_valid = False

        return ModelConfigOverrideValidation(
            is_valid=is_valid,
            violations=tuple(violations),
            warnings=tuple(warnings),
            suggestions=tuple(suggestions),
            paths_validated=paths_validated,
            type_checks_passed=type_checks_passed,
        )

    def preview(
        self,
        overrides: ModelConfigOverrideSet | None,
        config: Any,
        injection_point: EnumOverrideInjectionPoint | None = None,
    ) -> ModelConfigOverridePreview:
        """Preview configuration changes before applying.

        Generates a patch-like diff showing before/after state for each
        override without modifying the original configuration.

        Args:
            overrides: The set of overrides to preview. If None, returns
                an empty preview.
            config: The target configuration to preview against. If None,
                all paths will be marked as not existing.
            injection_point: Optional filter to only preview overrides for
                a specific injection point. If None, previews all overrides.

        Returns:
            ModelConfigOverridePreview with before/after previews.

        Thread Safety:
            Pure function - does not modify any state.

        Example:
            >>> preview = injector.preview(override_set, config)
            >>> print(preview.to_markdown())
            ## Configuration Override Preview
            | Path | Injection Point | Before | After | Status |
            ...
        """
        # Handle None overrides gracefully
        if overrides is None:
            return ModelConfigOverridePreview(
                field_previews=(),
                paths_not_found=(),
                type_mismatches=(),
            )

        field_previews: list[ModelConfigOverrideFieldPreview] = []
        paths_not_found: list[str] = []
        type_mismatches: list[str] = []

        # Filter overrides by injection point if specified
        overrides_to_preview = overrides.overrides
        if injection_point is not None:
            overrides_to_preview = tuple(
                o for o in overrides.overrides if o.injection_point == injection_point
            )

        for override in overrides_to_preview:
            # Validate path syntax first
            is_valid_syntax, _ = self._is_valid_path_syntax(override.path)
            if not is_valid_syntax:
                # Skip invalid paths in preview
                continue

            # Get current value
            current_value = self._get_value_at_path(config, override.path)
            path_exists = current_value is not MISSING

            # Track paths not found
            if not path_exists:
                paths_not_found.append(override.path)
                old_value: Any = None  # Use None for display
            else:
                old_value = current_value

            # Check for type mismatch
            if path_exists and current_value is not None:
                current_type = type(current_value).__name__
                new_type = type(override.value).__name__
                if current_type != new_type:
                    # Allow numeric conversions
                    if not (
                        isinstance(current_value, (int, float))
                        and isinstance(override.value, (int, float))
                    ):
                        type_mismatches.append(
                            f"{override.path}: {current_type} -> {new_type}"
                        )

            # Create field preview
            field_preview = ModelConfigOverrideFieldPreview(
                path=override.path,
                injection_point=override.injection_point,
                old_value=old_value,
                new_value=override.value,
                value_type=type(override.value).__name__,
                path_exists=path_exists,
            )
            field_previews.append(field_preview)

        return ModelConfigOverridePreview(
            field_previews=tuple(field_previews),
            paths_not_found=tuple(paths_not_found),
            type_mismatches=tuple(type_mismatches),
        )

    def apply(
        self,
        overrides: ModelConfigOverrideSet | None,
        config: Any,
        injection_point: EnumOverrideInjectionPoint | None = None,
    ) -> ModelConfigOverrideResult:
        """Apply configuration overrides to a config.

        Creates a deep copy of the configuration and applies all overrides.
        The original configuration is NEVER modified.

        Args:
            overrides: The set of overrides to apply. If None, returns
                an error result.
            config: The target configuration to patch. Will NOT be modified.
                If None, returns an error result.
            injection_point: Optional filter to only apply overrides for
                a specific injection point. If None, applies all overrides.

        Returns:
            ModelConfigOverrideResult with the patched configuration.

        Thread Safety:
            Pure function - creates a deep copy before modification.
            The original config is never mutated.

        Example:
            >>> result = injector.apply(override_set, config)
            >>> if result.success:
            ...     new_config = result.patched_config
            ...     print(f"Applied {result.overrides_applied} overrides")
        """
        # Handle None overrides gracefully
        if overrides is None:
            return ModelConfigOverrideResult(
                success=False,
                patched_config=config,
                overrides_applied=0,
                paths_created=(),
                errors=("Overrides cannot be None",),
            )

        # Handle None config gracefully
        if config is None:
            return ModelConfigOverrideResult(
                success=False,
                patched_config=None,
                overrides_applied=0,
                paths_created=(),
                errors=("Config cannot be None",),
            )

        # Deep copy the config to avoid mutating the original
        patched_config = self._deep_copy_config(config)

        errors: list[str] = []
        paths_created: list[str] = []
        overrides_applied = 0

        # Filter overrides by injection point if specified
        overrides_to_apply = overrides.overrides
        if injection_point is not None:
            overrides_to_apply = tuple(
                o for o in overrides.overrides if o.injection_point == injection_point
            )

        for override in overrides_to_apply:
            # Validate path syntax
            is_valid_syntax, syntax_error = self._is_valid_path_syntax(override.path)
            if not is_valid_syntax:
                errors.append(f"Invalid path '{override.path}': {syntax_error}")
                continue

            # Check if path exists (for tracking paths_created)
            current_value = self._get_value_at_path(patched_config, override.path)
            path_existed = current_value is not MISSING

            # Apply the override
            success, error = self._set_value_at_path(
                patched_config, override.path, override.value
            )

            if success:
                overrides_applied += 1
                if not path_existed:
                    paths_created.append(override.path)
            else:
                errors.append(f"Failed to set '{override.path}': {error}")

        return ModelConfigOverrideResult(
            success=len(errors) == 0,
            patched_config=patched_config,
            overrides_applied=overrides_applied,
            paths_created=tuple(paths_created),
            errors=tuple(errors),
        )

    def apply_environment_overlay(
        self,
        overrides: ModelConfigOverrideSet | None,
    ) -> types.MappingProxyType[str, str]:
        """Create an immutable environment variable overlay from overrides.

        Extracts ENVIRONMENT injection point overrides and creates an immutable
        mapping that can be used as an environment overlay. Does NOT mutate
        os.environ.

        The caller is responsible for applying the overlay to their environment
        context (e.g., passing to subprocess or using with os.environ.update()).

        Environment Variable Naming Derivation:
            The environment variable name is derived from the override path
            using the **last segment** of the dot-separated path, converted
            to **uppercase**. This allows for logical grouping in paths while
            producing conventional environment variable names.

            Path Segment Extraction::

                path.split(".")[-1].upper()

            Examples:
                - "timeout"              -> "TIMEOUT"
                - "llm.temperature"      -> "TEMPERATURE"
                - "config.retry.count"   -> "COUNT"
                - "my_setting"           -> "MY_SETTING"

            Rationale:
                - Paths may be hierarchical for organization/grouping purposes
                - Environment variable names are traditionally SCREAMING_CASE
                - Using the last segment prevents overly long env var names
                - Underscores in path segments are preserved (my_var -> MY_VAR)

        Value Conversion:
            - None values become empty strings ("")
            - Boolean True becomes "true", False becomes "false"
            - All other values use str() conversion

        Args:
            overrides: The set of overrides to extract environment variables from.
                If None, returns an empty mapping.

        Returns:
            Immutable mapping of environment variable names to string values.
            Only includes overrides with injection_point=ENVIRONMENT.
            Returns MappingProxyType to prevent callers from mutating the result.

        Thread Safety:
            Pure function - returns an immutable mapping, never mutates os.environ.

        Example:
            >>> from omnibase_core.models.replay import ModelConfigOverride, ModelConfigOverrideSet
            >>> from omnibase_core.enums.replay import EnumOverrideInjectionPoint
            >>> override = ModelConfigOverride(
            ...     path="llm.openai.api_key",  # Grouped path
            ...     value="sk-test-123",
            ...     injection_point=EnumOverrideInjectionPoint.ENVIRONMENT,
            ... )
            >>> override_set = ModelConfigOverrideSet(overrides=(override,))
            >>> injector = ServiceConfigOverrideInjector()
            >>> overlay = injector.apply_environment_overlay(override_set)
            >>> dict(overlay)
            {'API_KEY': 'sk-test-123'}  # Last segment, uppercased
            >>>
            >>> # Pass to subprocess (dict() creates a mutable copy if needed)
            >>> subprocess.run(cmd, env={**os.environ, **overlay})
            >>>
            >>> # Or use as context manager (user-provided)
            >>> with env_context(overlay):
            ...     run_handler()
            >>>
            >>> # Attempting to mutate raises TypeError
            >>> overlay["NEW_VAR"] = "value"  # Raises TypeError
        """
        # Handle None overrides gracefully
        if overrides is None:
            return types.MappingProxyType({})

        env_overlay: dict[str, str] = {}

        for override in overrides.overrides:
            if override.injection_point != EnumOverrideInjectionPoint.ENVIRONMENT:
                continue

            # Environment variable names are the path (or last segment)
            # Path can be the full env var name or nested for grouping
            parts = override.path.split(".")
            env_name = parts[-1].upper()  # Use last segment, uppercase by convention

            # Convert value to string
            if override.value is None:
                value_str = ""
            elif isinstance(override.value, bool):
                value_str = "true" if override.value else "false"
            else:
                value_str = str(override.value)

            env_overlay[env_name] = value_str

        return types.MappingProxyType(env_overlay)


__all__ = ["ServiceConfigOverrideInjector", "MISSING"]
