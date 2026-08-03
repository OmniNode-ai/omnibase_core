# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Pre-merge gate tests.

Modules here are ordinary pytest tests collected by ``testpaths = ["tests"]`` in
``pyproject.toml``, so they run inside the existing required CI job. They are kept in
their own package because they assert cross-boundary invariants (source-tree shape,
external policy conformance) rather than the behaviour of one unit.
"""
