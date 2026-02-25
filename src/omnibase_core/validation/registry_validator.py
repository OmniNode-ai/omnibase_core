# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorRegistry — thread-safe registry mapping validators to subjects.

Part of the Generic Validator Node Architecture (OMN-2362).
Blocked by: OMN-2543 (models), OMN-2550 (NodeValidator base class).

The registry stores `(ModelValidatorDescriptor, NodeValidator subclass)` pairs
and provides:
- register(): record a descriptor + node class (raises on duplicate validator_id)
- resolve(): return instantiated NodeValidator instances applicable to a query
- list_all(): enumerate all registered descriptors

Thread safety:
The registry is designed for a read-heavy, startup-write pattern.
A threading.RLock guards all mutations. Reads (resolve, list_all) acquire a
shared read lock via the same RLock for simplicity and correctness — this is
sufficient for the expected usage pattern (few registrations at startup,
many resolutions at runtime).

Registration:
Validators register themselves either:
1. Explicitly: registry.register(MyValidator.descriptor, MyValidator)
2. Via decorator: @registry.register_decorator (see register_decorator method)

No magic auto-discovery. Registration must be explicit and happen before
the first resolve() call.
"""

from __future__ import annotations

import threading
from typing import Literal

from omnibase_core.models.validation.model_validator_descriptor import (
    ModelValidatorDescriptor,
)


def _is_validator_node_class(obj: object) -> bool:
    """Duck-type check: does obj look like a concrete NodeValidator subclass?

    We use duck typing rather than a strict issubclass() check to avoid
    import-identity issues when the NodeValidator class is loaded from
    different paths (e.g. editable installs vs site-packages).

    A valid NodeValidator subclass must:
    - Be a type (class).
    - Have a callable 'validate' instance method.
    - Have a 'descriptor' class attribute of type ModelValidatorDescriptor.
    """
    if not isinstance(obj, type):
        return False
    # Must have a callable validate method (abstract or concrete).
    validate_attr = getattr(obj, "validate", None)
    if validate_attr is None or not callable(validate_attr):
        return False
    # Must have a descriptor of type ModelValidatorDescriptor.
    descriptor = getattr(obj, "descriptor", None)
    if not isinstance(descriptor, ModelValidatorDescriptor):
        return False
    return True


class ValidatorRegistry:
    """Thread-safe registry that maps ValidatorDescriptors to NodeValidator classes.

    The registry does NOT import NodeValidator at module level to avoid a circular
    import between this module and node_validator.py. The type annotation is kept
    as a string forward reference.

    Example:
        >>> from omnibase_core.validation.registry_validator import ValidatorRegistry
        >>> registry = ValidatorRegistry()
        >>> # Register during application startup (not at module level):
        >>> # registry.register(MyValidator.descriptor, MyValidator)
        >>> # Later, resolve validators for a request:
        >>> validators = registry.resolve(scope="file")
        >>> # validators is a list of instantiated NodeValidator instances.
    """

    def __init__(self) -> None:
        # _entries maps validator_id -> (descriptor, node_class)
        self._entries: dict[str, tuple[ModelValidatorDescriptor, type]] = {}
        self._lock = threading.RLock()

    def register(
        self,
        descriptor: ModelValidatorDescriptor,
        node_class: type,
    ) -> None:
        """Register a validator with its descriptor.

        Args:
            descriptor: The ModelValidatorDescriptor declaring the validator's
                identity and capabilities.
            node_class: The concrete NodeValidator subclass to instantiate when
                this validator is resolved. Must be a subclass of NodeValidator
                (i.e. must have a callable 'validate' method and a 'descriptor'
                attribute of type ModelValidatorDescriptor).

        Raises:
            TypeError: If node_class does not look like a NodeValidator subclass.
            ValueError: If a validator with the same validator_id is already registered.
        """
        if not _is_validator_node_class(node_class):
            raise TypeError(
                f"node_class must be a subclass of NodeValidator, "
                f"got {node_class!r}."
            )
        with self._lock:
            if descriptor.validator_id in self._entries:
                existing_descriptor, _ = self._entries[descriptor.validator_id]
                raise ValueError(
                    f"A validator with id '{descriptor.validator_id}' is already "
                    f"registered (class: {existing_descriptor.display_name or descriptor.validator_id!r}). "
                    f"Registry must not silently overwrite existing registrations. "
                    f"Use a different validator_id or deregister the existing validator first."
                )
            self._entries[descriptor.validator_id] = (descriptor, node_class)

    def register_decorator(self, node_class: type) -> type:
        """Class decorator that registers a NodeValidator subclass on definition.

        The class must have a 'descriptor' class variable of type
        ModelValidatorDescriptor set before the decorator is applied.

        Usage:
            registry = ValidatorRegistry()

            @registry.register_decorator
            class MyValidator(NodeValidator):
                descriptor = ModelValidatorDescriptor(
                    validator_id="my_validator",
                    applicable_scopes=("file",),
                )
                def validate(self, request):
                    ...

        Returns:
            The unmodified node_class (the decorator is registration-only).

        Raises:
            TypeError: If node_class is not a NodeValidator subclass.
            ValueError: If the validator_id is already registered.
        """
        if not _is_validator_node_class(node_class):
            raise TypeError(
                f"register_decorator can only be applied to NodeValidator subclasses, "
                f"got {node_class!r}."
            )
        descriptor: ModelValidatorDescriptor = node_class.descriptor  # type: ignore[attr-defined]
        self.register(descriptor, node_class)
        return node_class

    def resolve(
        self,
        scope: Literal["file", "subtree", "workspace", "artifact"] | None = None,
        contract_types: tuple[str, ...] = (),
        tuple_types: tuple[str, ...] = (),
        available_capabilities: tuple[str, ...] = (),
        deny_list: tuple[str, ...] = (),
    ) -> list[object]:
        """Return instantiated NodeValidator instances applicable to a query.

        Filtering logic (all filters are AND-combined):
        1. scope: If provided, the validator's applicable_scopes must include it.
        2. contract_types: If non-empty, the validator's applicable_contract_types
           must intersect (at least one contract_type in common).
           If both are empty, the filter is skipped (validator applies to all).
        3. tuple_types: If non-empty, the validator's applicable_tuple_types
           must intersect with the query tuple_types.
           If both are empty, the filter is skipped.
        4. available_capabilities: The validator's required_capabilities must be
           a subset of the available_capabilities provided by the runtime.
           Validators with no required_capabilities always pass.
        5. deny_list: Validators whose validator_id appears in deny_list are
           excluded regardless of other filters.

        Args:
            scope: Optional scope to filter by. None means "any scope".
            contract_types: ONEX contract types present in the target. Empty
                tuple means "do not filter by contract type".
            tuple_types: ONEX tuple types present in the target. Empty tuple
                means "do not filter by tuple type".
            available_capabilities: Capabilities provided by the current runtime
                environment. Validators with required_capabilities not in this
                set are excluded.
            deny_list: Validator IDs to exclude from results.

        Returns:
            A list of instantiated NodeValidator instances, ordered by
            validator_id (deterministic).
        """
        matched: list[tuple[str, object]] = []

        with self._lock:
            entries_snapshot = list(self._entries.values())

        for descriptor, node_class in entries_snapshot:
            # 1. deny_list check
            if descriptor.validator_id in deny_list:
                continue

            # 2. scope filter
            if scope is not None and scope not in descriptor.applicable_scopes:
                continue

            # 3. contract_types filter (only if query is non-empty)
            if contract_types and descriptor.applicable_contract_types:
                if not set(contract_types).intersection(descriptor.applicable_contract_types):
                    continue

            # 4. tuple_types filter (only if query is non-empty)
            if tuple_types and descriptor.applicable_tuple_types:
                if not set(tuple_types).intersection(descriptor.applicable_tuple_types):
                    continue

            # 5. capability filter
            if descriptor.required_capabilities:
                if not set(descriptor.required_capabilities).issubset(
                    set(available_capabilities)
                ):
                    continue

            matched.append((descriptor.validator_id, node_class()))

        # Deterministic ordering by validator_id
        matched.sort(key=lambda pair: pair[0])
        return_list = [node for _, node in matched]
        return return_list

    def list_all(self) -> list[ModelValidatorDescriptor]:
        """Return all registered descriptors, ordered by validator_id.

        Returns:
            A new list of ModelValidatorDescriptor instances. The list is
            a snapshot; modifications to it do not affect the registry.
        """
        with self._lock:
            entries_snapshot = list(self._entries.values())

        descriptors = [descriptor for descriptor, _ in entries_snapshot]
        descriptors.sort(key=lambda d: d.validator_id)
        return descriptors

    def deregister(self, validator_id: str) -> bool:
        """Remove a validator registration by ID.

        Primarily useful for testing. Production code should not call this.

        Args:
            validator_id: The ID of the validator to remove.

        Returns:
            True if the validator was found and removed, False if not found.
        """
        with self._lock:
            if validator_id in self._entries:
                del self._entries[validator_id]
                return True
        return False

    def __len__(self) -> int:
        """Return the number of registered validators."""
        with self._lock:
            return len(self._entries)

    def __contains__(self, validator_id: object) -> bool:
        """Return True if a validator with the given ID is registered."""
        if not isinstance(validator_id, str):
            return False
        with self._lock:
            return validator_id in self._entries


__all__ = ["ValidatorRegistry"]
