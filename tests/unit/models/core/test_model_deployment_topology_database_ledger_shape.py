# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""OMN-26471 AC6: a database declares its migration-ledger shape, typed."""

from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.models.core.model_deployment_topology_database_migration_ledger import (
    ModelDeploymentTopologyDatabaseMigrationLedger,
)

pytestmark = pytest.mark.unit

_FOUR: dict[str, Any] = {
    "schema": "platform_catalog",
    "relation": "schema_migrations",
    "stream_column": "migration_stream",
    "domain_column": "domain",
    "version_column": "version",
    "checksum_column": "checksum",
}
_CLOUD: dict[str, Any] = {
    "schema": "public",
    "relation": "schema_migrations",
    "shape": "version_checksum",
    "version_column": "version",
    "checksum_column": "checksum",
}


def test_cloud_version_checksum_shape_is_accepted() -> None:
    ledger = ModelDeploymentTopologyDatabaseMigrationLedger.model_validate(_CLOUD)
    assert ledger.stream_column is None
    assert ledger.domain_column is None
    assert ledger.model_dump(by_alias=True)["shape"] == "version_checksum"


def test_existing_four_column_entry_stays_valid_without_shape_key() -> None:
    ledger = ModelDeploymentTopologyDatabaseMigrationLedger.model_validate(_FOUR)
    assert ledger.shape.value == "stream_domain_version_checksum"
    assert ledger.stream_column == "migration_stream"


def test_four_column_shape_requires_stream_and_domain() -> None:
    payload = {k: v for k, v in _FOUR.items() if k != "stream_column"}
    with pytest.raises(ValidationError, match="stream_column"):
        ModelDeploymentTopologyDatabaseMigrationLedger.model_validate(payload)


def test_four_column_shape_still_refuses_duplicate_columns() -> None:
    with pytest.raises(ValidationError, match="distinct"):
        ModelDeploymentTopologyDatabaseMigrationLedger.model_validate(
            {**_FOUR, "domain_column": "version"}
        )


def test_version_checksum_shape_refuses_stream_column() -> None:
    with pytest.raises(ValidationError, match="stream_column"):
        ModelDeploymentTopologyDatabaseMigrationLedger.model_validate(
            {**_CLOUD, "stream_column": "migration_stream"}
        )


def test_version_checksum_shape_refuses_same_column_twice() -> None:
    with pytest.raises(ValidationError, match="distinct"):
        ModelDeploymentTopologyDatabaseMigrationLedger.model_validate(
            {**_CLOUD, "checksum_column": "version"}
        )


def test_unknown_shape_is_refused_by_name() -> None:
    with pytest.raises(ValidationError, match="shape"):
        ModelDeploymentTopologyDatabaseMigrationLedger.model_validate(
            {**_CLOUD, "shape": "free_form"}
        )
