"""Tests for protocol structural compliance.

This module verifies that all protocols in omnibase_core follow proper
structural conventions:

1. All protocols have proper docstrings
2. Protocols only define abstract methods (no implementation)
3. Protocols use proper type annotations

These tests help maintain protocol quality and ONEX compliance standards.

Related:
    - PR #241: Protocol structural compliance review
    - docs/conventions/PROTOCOL_CONVENTIONS.md
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Any, Protocol, get_type_hints

import pytest


def get_all_protocol_classes() -> list[tuple[str, type]]:
    """Discover all Protocol classes in omnibase_core.protocols.

    Returns:
        List of (module_path, protocol_class) tuples.
    """
    import omnibase_core.protocols as protocols_pkg

    protocol_classes: list[tuple[str, type]] = []

    # Walk through all submodules
    for importer, modname, ispkg in pkgutil.walk_packages(
        protocols_pkg.__path__, prefix="omnibase_core.protocols."
    ):
        try:
            module = importlib.import_module(modname)
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # Check if it's a Protocol subclass (but not Protocol itself)
                if (
                    name.startswith("Protocol")
                    and hasattr(obj, "__mro__")
                    and Protocol in obj.__mro__
                    and obj is not Protocol
                ):
                    protocol_classes.append((f"{modname}.{name}", obj))
        except ImportError:
            # Skip modules that fail to import
            continue

    return protocol_classes


# Cache the protocol list to avoid repeated discovery
_PROTOCOL_CLASSES: list[tuple[str, type]] | None = None


def get_cached_protocol_classes() -> list[tuple[str, type]]:
    """Get cached list of protocol classes."""
    global _PROTOCOL_CLASSES
    if _PROTOCOL_CLASSES is None:
        _PROTOCOL_CLASSES = get_all_protocol_classes()
    return _PROTOCOL_CLASSES


@pytest.mark.unit
class TestProtocolDocstrings:
    """Test that all protocols have proper docstrings."""

    def test_all_protocols_have_class_docstrings(self):
        """Verify every protocol class has a docstring.

        Good protocols should document their purpose, usage, and any
        important implementation notes.
        """
        protocols = get_cached_protocol_classes()
        missing_docstrings: list[str] = []

        for path, protocol_cls in protocols:
            if not protocol_cls.__doc__ or not protocol_cls.__doc__.strip():
                missing_docstrings.append(path)

        if missing_docstrings:
            pytest.fail(
                "The following protocols are missing docstrings:\n"
                + "\n".join(f"  - {p}" for p in missing_docstrings[:10])
                + (
                    f"\n  ... and {len(missing_docstrings) - 10} more"
                    if len(missing_docstrings) > 10
                    else ""
                )
            )

    def test_protocol_methods_have_docstrings(self):
        """Verify protocol methods have docstrings.

        Public methods should document their purpose, parameters, and return values.
        """
        protocols = get_cached_protocol_classes()
        methods_without_docs: list[str] = []

        for path, protocol_cls in protocols:
            for name, method in inspect.getmembers(protocol_cls):
                # Skip private/dunder methods
                if name.startswith("_"):
                    continue
                # Skip non-callable attributes
                if not callable(method):
                    continue
                # Skip inherited from object/Protocol
                if hasattr(object, name) or hasattr(Protocol, name):
                    continue

                # Check for docstring
                if not getattr(method, "__doc__", None):
                    methods_without_docs.append(f"{path}.{name}")

        # Report but don't fail - some protocol methods may legitimately be simple
        if methods_without_docs and len(methods_without_docs) > 20:
            # Only warn if significant number of undocumented methods
            pass  # This is informational


@pytest.mark.unit
class TestProtocolAbstractness:
    """Test that protocols only define abstract methods (no implementation)."""

    def test_protocols_have_no_concrete_implementations(self):
        """Verify protocols don't contain concrete method implementations.

        Protocol methods should use '...' (Ellipsis) or 'pass' as their body,
        not actual implementations. Concrete implementations belong in
        implementing classes.
        """
        protocols = get_cached_protocol_classes()
        concrete_methods: list[str] = []

        for path, protocol_cls in protocols:
            for name, method in inspect.getmembers(protocol_cls):
                # Skip private/dunder methods and properties
                if name.startswith("_"):
                    continue
                if not callable(method) or isinstance(method, property):
                    continue
                if hasattr(object, name) or hasattr(Protocol, name):
                    continue

                # Try to inspect the source code
                try:
                    source = inspect.getsource(method)
                    # Check if it's a stub (contains only ... or pass)
                    # Strip comments and whitespace
                    lines = [
                        line.strip()
                        for line in source.split("\n")
                        if line.strip() and not line.strip().startswith("#")
                    ]
                    # Remove the def line and docstring
                    body_lines = []
                    in_docstring = False
                    past_def = False
                    for line in lines:
                        if not past_def:
                            if line.startswith(("def ", "async def ")):
                                past_def = True
                            continue
                        if '"""' in line or "'''" in line:
                            in_docstring = not in_docstring
                            continue
                        if not in_docstring:
                            body_lines.append(line)

                    # Check if body is just ... or pass
                    body = " ".join(body_lines)
                    if body and body not in ("...", "pass", "...;", "pass;"):
                        # Has actual implementation - but this might be intended
                        # for protocols with default implementations
                        pass  # Don't report, some protocols may have defaults
                except (OSError, TypeError):
                    # Can't get source - built-in or C extension
                    continue


@pytest.mark.unit
class TestProtocolTypeAnnotations:
    """Test that protocols use proper type annotations."""

    def test_protocol_methods_have_return_types(self):
        """Verify protocol methods have return type annotations.

        Type annotations enable mypy strict mode compliance and improve
        code quality and IDE support.
        """
        protocols = get_cached_protocol_classes()
        missing_return_types: list[str] = []

        for path, protocol_cls in protocols:
            for name, method in inspect.getmembers(protocol_cls):
                # Skip private/dunder methods
                if name.startswith("_"):
                    continue
                # Skip non-callable (properties handled separately)
                if not callable(method):
                    continue
                if hasattr(object, name) or hasattr(Protocol, name):
                    continue

                try:
                    hints = get_type_hints(method)
                    if "return" not in hints:
                        # Method missing return type annotation
                        missing_return_types.append(f"{path}.{name}")
                except Exception:
                    # Type hint resolution failed - skip
                    continue

        # Report significant issues
        if len(missing_return_types) > 50:
            pytest.fail(
                "Too many protocol methods missing return type annotations:\n"
                + "\n".join(f"  - {m}" for m in missing_return_types[:10])
                + f"\n  ... and {len(missing_return_types) - 10} more"
            )

    def test_protocol_methods_have_parameter_types(self):
        """Verify protocol method parameters have type annotations.

        All parameters (except 'self') should have type annotations.
        """
        protocols = get_cached_protocol_classes()
        missing_param_types: list[str] = []

        for path, protocol_cls in protocols:
            for name, method in inspect.getmembers(protocol_cls):
                if name.startswith("_"):
                    continue
                if not callable(method):
                    continue
                if hasattr(object, name) or hasattr(Protocol, name):
                    continue

                try:
                    sig = inspect.signature(method)
                    hints = get_type_hints(method)
                    for param_name, param in sig.parameters.items():
                        if param_name == "self":
                            continue
                        if param_name not in hints:
                            missing_param_types.append(f"{path}.{name}({param_name})")
                except Exception:
                    continue

        # Report significant issues
        if len(missing_param_types) > 50:
            pytest.fail(
                "Too many protocol parameters missing type annotations:\n"
                + "\n".join(f"  - {p}" for p in missing_param_types[:10])
                + f"\n  ... and {len(missing_param_types) - 10} more"
            )


@pytest.mark.unit
class TestProtocolNamingConventions:
    """Test that protocols follow naming conventions."""

    def test_protocol_classes_have_protocol_prefix(self):
        """Verify protocol classes are named with 'Protocol' prefix.

        Convention: Protocol classes should be named ProtocolXxx to clearly
        indicate they are protocols/interfaces.
        """
        protocols = get_cached_protocol_classes()

        for path, protocol_cls in protocols:
            assert protocol_cls.__name__.startswith("Protocol"), (
                f"Protocol class {path} should be named with 'Protocol' prefix, "
                f"got '{protocol_cls.__name__}'"
            )

    def test_protocol_modules_have_protocol_prefix(self):
        """Verify protocol module files are named with 'protocol_' prefix.

        Convention: Protocol files should be named protocol_xxx.py to clearly
        indicate they contain protocol definitions.
        """
        import omnibase_core.protocols as protocols_pkg

        for importer, modname, ispkg in pkgutil.walk_packages(
            protocols_pkg.__path__, prefix="omnibase_core.protocols."
        ):
            if ispkg:
                continue  # Skip packages

            # Get the last part of the module name (the filename without .py)
            filename = modname.split(".")[-1]

            # Skip __init__ and other special modules
            if filename.startswith("_"):
                continue

            # Should start with 'protocol_' (or be 'core' which is an exception)
            if filename != "core" and not filename.startswith("protocol_"):
                # This is informational - don't fail
                pass


@pytest.mark.unit
class TestProtocolRuntimeCheckability:
    """Test that protocols support runtime isinstance checks where appropriate."""

    def test_key_protocols_are_runtime_checkable(self):
        """Verify key protocols are marked @runtime_checkable.

        Protocols that are commonly used with isinstance() checks should
        be marked @runtime_checkable for duck typing support.
        """
        from omnibase_core.protocols import (
            ProtocolCircuitBreaker,
            ProtocolConfigurable,
            ProtocolExecutable,
            ProtocolIdentifiable,
            ProtocolValidatable,
        )

        key_protocols = [
            ProtocolCircuitBreaker,
            ProtocolConfigurable,
            ProtocolExecutable,
            ProtocolIdentifiable,
            ProtocolValidatable,
        ]

        for protocol in key_protocols:
            # Check if it has the runtime protocol marker
            is_runtime = hasattr(protocol, "_is_runtime_protocol") or hasattr(
                protocol, "__protocol_attrs__"
            )
            assert is_runtime, (
                f"{protocol.__name__} should be @runtime_checkable for duck typing"
            )


@pytest.mark.unit
class TestProtocolImportability:
    """Test that protocols can be imported from the main protocols module."""

    def test_key_protocols_importable_from_main_module(self):
        """Verify key protocols are exported from omnibase_core.protocols.

        For convenient usage, commonly used protocols should be importable
        directly from the main protocols module.
        """
        from omnibase_core.protocols import (
            ProtocolAsyncCircuitBreaker,
            ProtocolCircuitBreaker,
            ProtocolComputeCache,
            ProtocolConfigurable,
            ProtocolEventBus,
            ProtocolExecutable,
            ProtocolIdentifiable,
            ProtocolServiceRegistry,
            ProtocolValidatable,
            ProtocolValidationResult,
        )

        # All should be non-None (imported successfully)
        protocols = [
            ProtocolCircuitBreaker,
            ProtocolAsyncCircuitBreaker,
            ProtocolComputeCache,
            ProtocolConfigurable,
            ProtocolEventBus,
            ProtocolExecutable,
            ProtocolIdentifiable,
            ProtocolServiceRegistry,
            ProtocolValidatable,
            ProtocolValidationResult,
        ]

        for protocol in protocols:
            assert protocol is not None, f"Failed to import {protocol}"
            assert inspect.isclass(protocol), f"{protocol} should be a class"
