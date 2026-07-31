# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for typed application-database deployment topology contracts."""

from typing import Any

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_database_grant_object_type import (
    EnumDatabaseGrantObjectType,
)
from omnibase_core.enums.enum_database_privilege import EnumDatabasePrivilege
from omnibase_core.enums.enum_database_schema_domain import EnumDatabaseSchemaDomain
from omnibase_core.models.contracts.subcontracts.model_db_table_declaration import (
    ModelDbTableDeclaration,
)
from omnibase_core.models.core.model_deployment_topology import ModelDeploymentTopology

pytestmark = pytest.mark.unit


def _database_payload() -> dict[str, Any]:
    return {
        "physical_name": "omnidash_analytics",
        "schemas": {
            "tenant": {"domain": "TENANT", "owner": "owner_onex_tenant"},
            "omninode_internal": {
                "domain": "OMNINODE_INTERNAL",
                "owner": "owner_omninode_internal",
            },
            "platform_catalog": {
                "domain": "PLATFORM_CATALOG",
                "owner": "owner_platform_catalog",
            },
        },
        "owners": {
            "owner_onex_tenant": {"login": False},
            "owner_omninode_internal": {"login": False},
            "owner_platform_catalog": {"login": False},
        },
        "principals": {
            "onex_api": {
                "login": True,
                "bypass_rls": False,
                "grants": [
                    {
                        "object_type": "SCHEMA",
                        "schema": "tenant",
                        "privileges": ["USAGE"],
                    },
                    {
                        "object_type": "TABLE",
                        "schema": "tenant",
                        "objects": ["delegation_events"],
                        "privileges": ["SELECT", "INSERT"],
                    },
                ],
            }
        },
        "bindings": {
            "onex_api": {
                "database_ref": "application",
                "principal": "onex_api",
                "dsn_env": "OMNINODE_CLOUD_DB_URL",
            }
        },
        "migration_stream": "omnibase_infra.application",
        "checksum_ledgers": {
            "canonical": {
                "schema": "platform_catalog",
                "relation": "schema_migrations",
                "stream_column": "migration_stream",
                "domain_column": "domain",
                "version_column": "version",
                "checksum_column": "checksum",
            }
        },
        "checksum_ledger": "canonical",
    }


def _topology_payload() -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "services": {},
        "presets": {},
        "active_preset": None,
        "databases": {"application": _database_payload()},
    }


def test_database_topology_parses_typed_resource_and_resolves_table_domain() -> None:
    topology = ModelDeploymentTopology.model_validate(_topology_payload())
    declaration = ModelDbTableDeclaration(
        name="delegation_events",
        database_ref="application",
        schema="tenant",
        migration="nodes/node_projection_delegation/0001.sql",
        access="read_write",
        role="events",
    )

    database = topology.databases["application"]
    assert database.physical_name == "omnidash_analytics"
    assert database.schemas["tenant"].domain is EnumDatabaseSchemaDomain.TENANT
    assert topology.table_domain(declaration) is EnumDatabaseSchemaDomain.TENANT
    assert (
        database.principals["onex_api"].grants[0].object_type
        is EnumDatabaseGrantObjectType.SCHEMA
    )
    assert (
        EnumDatabasePrivilege.USAGE
        in database.principals["onex_api"].grants[0].privileges
    )


def test_database_topology_yaml_roundtrip_is_stable() -> None:
    topology = ModelDeploymentTopology.model_validate(_topology_payload())

    restored = ModelDeploymentTopology._from_yaml_string(topology._to_yaml_string())

    assert restored == topology


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (
            ("databases", "application", "schemas", "tenant", "owner"),
            "missing_owner",
            "owner",
        ),
        (
            (
                "databases",
                "application",
                "bindings",
                "onex_api",
                "database_ref",
            ),
            "missing_database",
            "database_ref",
        ),
        (
            ("databases", "application", "bindings", "onex_api", "principal"),
            "missing_principal",
            "principal",
        ),
        (
            ("databases", "application", "checksum_ledger"),
            "missing_ledger",
            "checksum_ledger",
        ),
        (
            (
                "databases",
                "application",
                "principals",
                "onex_api",
                "grants",
                0,
                "schema",
            ),
            "missing_schema",
            "schema",
        ),
    ],
)
def test_unknown_database_cross_references_fail_closed(
    path: tuple[str | int, ...], value: str, message: str
) -> None:
    payload = _topology_payload()
    target: Any = payload
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value

    with pytest.raises(ValidationError, match=message):
        ModelDeploymentTopology.model_validate(payload)


def test_binding_cannot_reference_a_different_database() -> None:
    payload = _topology_payload()
    payload["databases"]["reporting"] = _database_payload()

    with pytest.raises(ValidationError, match="database_ref"):
        ModelDeploymentTopology.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [("login", False), ("bypass_rls", True)],
)
def test_workload_principal_must_be_login_without_bypass_rls(
    field: str, value: bool
) -> None:
    payload = _topology_payload()
    payload["databases"]["application"]["principals"]["onex_api"][field] = value

    with pytest.raises(ValidationError, match=field):
        ModelDeploymentTopology.model_validate(payload)


def test_schema_owner_must_be_nologin() -> None:
    payload = _topology_payload()
    payload["databases"]["application"]["owners"]["owner_onex_tenant"]["login"] = True

    with pytest.raises(ValidationError, match="login"):
        ModelDeploymentTopology.model_validate(payload)


def test_owner_and_login_principal_role_names_cannot_overlap() -> None:
    payload = _topology_payload()
    payload["databases"]["application"]["owners"]["onex_api"] = {"login": False}

    with pytest.raises(
        ValidationError, match="both NOLOGIN owners and LOGIN principals"
    ):
        ModelDeploymentTopology.model_validate(payload)


def test_workload_principal_cannot_receive_ddl_privileges() -> None:
    payload = _topology_payload()
    payload["databases"]["application"]["principals"]["onex_api"]["grants"].append(
        {
            "object_type": "SCHEMA",
            "schema": "tenant",
            "privileges": ["CREATE"],
        }
    )

    with pytest.raises(ValidationError, match="DDL privileges: CREATE"):
        ModelDeploymentTopology.model_validate(payload)


def test_dsn_binding_accepts_only_an_environment_variable_name() -> None:
    payload = _topology_payload()
    payload["databases"]["application"]["bindings"]["onex_api"]["dsn_env"] = (
        "postgresql://runtime@example.invalid/application"
    )

    with pytest.raises(ValidationError, match="dsn_env"):
        ModelDeploymentTopology.model_validate(payload)


def test_unknown_fields_and_secret_material_are_rejected() -> None:
    payload = _topology_payload()
    payload["databases"]["application"]["principals"]["onex_api"]["password"] = (
        "not-allowed"
    )

    with pytest.raises(ValidationError, match="password"):
        ModelDeploymentTopology.model_validate(payload)


def test_grant_privileges_must_match_object_type() -> None:
    payload = _topology_payload()
    payload["databases"]["application"]["principals"]["onex_api"]["grants"][0][
        "privileges"
    ] = ["SELECT"]

    with pytest.raises(ValidationError, match="SELECT"):
        ModelDeploymentTopology.model_validate(payload)


def test_unknown_table_location_fails_closed() -> None:
    topology = ModelDeploymentTopology.model_validate(_topology_payload())
    declaration = ModelDbTableDeclaration(
        name="delegation_events",
        database_ref="application",
        schema="unknown_schema",
        migration="nodes/node_projection_delegation/0001.sql",
        role="events",
    )

    with pytest.raises(ValueError, match="unknown_schema"):
        topology.table_domain(declaration)


def test_table_cannot_override_topology_owned_domain() -> None:
    with pytest.raises(ValidationError, match="domain"):
        ModelDbTableDeclaration(
            name="delegation_events",
            database_ref="application",
            schema="tenant",
            migration="nodes/node_projection_delegation/0001.sql",
            role="events",
            domain="OMNINODE_INTERNAL",  # type: ignore[call-arg]
        )


def test_database_resource_is_frozen() -> None:
    topology = ModelDeploymentTopology.model_validate(_topology_payload())

    with pytest.raises(ValidationError):
        topology.databases["application"].physical_name = "other"  # type: ignore[misc]
