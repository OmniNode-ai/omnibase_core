# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Catalog services for the registry-driven CLI system.

Provides ServiceCatalogManager for the full catalog materialization pipeline:
fetch → verify → validate → policy-filter → cache → load.

Import directly from the specific module per OMN-1071 policy:

    from omnibase_core.services.catalog.service_catalog_manager import ServiceCatalogManager

.. versionadded:: 0.19.0  (OMN-2544)
"""
