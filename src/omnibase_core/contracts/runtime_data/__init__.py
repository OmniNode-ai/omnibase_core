# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Runtime contract YAML data package.

This package bundles the runtime contract YAML files so they are discoverable
via ``importlib.resources`` when omnibase_core is installed from PyPI.

The canonical contract YAMLs also live at the repository root
(``contracts/runtime/``) for use by validation scripts and pre-commit hooks.
When modifying contracts, update both locations (or run the sync check in CI).

See ``get_runtime_contracts_dir()`` in ``runtime_contracts.py`` for the
3-tier resolution strategy.
"""
