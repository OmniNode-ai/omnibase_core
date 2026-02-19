# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pre-refactor API snapshot tests for omnibase_core modules.

These tests capture the public API surface before v0.4.0 refactoring.
If these tests fail due to intentional breaking changes, update them
in the same PR with a migration note in the changelog.

Purpose:
--------
- Lock current public API behavior with snapshot tests
- Detect accidental API changes during refactoring
- Document the exact public interface for each module
- Ensure backward compatibility is explicitly tracked

Convention:
-----------
Each module should have a corresponding test file named:
    test_{module_name}_api_snapshot.py

Test classes should follow the pattern:
    Test{ModuleName}APISnapshot
"""
