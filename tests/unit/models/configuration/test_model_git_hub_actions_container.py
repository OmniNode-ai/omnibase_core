"""
Tests for ModelGitHubActionsContainer.

Validates:
1. Model instantiation with valid data
2. Model validation with invalid data
3. Optional field handling
4. Type coercion where applicable

Related:
    - PR #302: Add GitHub Actions container model
"""

import pytest
from pydantic import ValidationError

from omnibase_core.models.configuration.model_git_hub_actions_container import (
    ModelGitHubActionsContainer,
)

# =============================================================================
# Test Classes
# =============================================================================


@pytest.mark.unit
class TestModelGitHubActionsContainerInstantiation:
    """Tests for ModelGitHubActionsContainer instantiation."""

    def test_create_with_image_only(self) -> None:
        """Test creating container config with only required image field."""
        container = ModelGitHubActionsContainer(image="node:14")
        assert container.image == "node:14"
        assert container.credentials is None
        assert container.env is None
        assert container.ports is None
        assert container.volumes is None
        assert container.options is None

    def test_create_with_all_fields(self) -> None:
        """Test creating container config with all fields."""
        container = ModelGitHubActionsContainer(
            image="node:18",
            credentials={"username": "user", "password": "pass"},
            env={"NODE_ENV": "production", "DEBUG": "false"},
            ports=[80, "8080:8080", 443],
            volumes=["/data:/data", "/config:/config:ro"],
            options="--cpus 2 --memory 4g",
        )

        assert container.image == "node:18"
        assert container.credentials == {"username": "user", "password": "pass"}
        assert container.env == {"NODE_ENV": "production", "DEBUG": "false"}
        assert container.ports == [80, "8080:8080", 443]
        assert container.volumes == ["/data:/data", "/config:/config:ro"]
        assert container.options == "--cpus 2 --memory 4g"

    def test_create_with_public_image(self) -> None:
        """Test creating container with public Docker Hub image."""
        container = ModelGitHubActionsContainer(image="python:3.12-slim")
        assert container.image == "python:3.12-slim"

    def test_create_with_private_registry_image(self) -> None:
        """Test creating container with private registry image."""
        container = ModelGitHubActionsContainer(
            image="ghcr.io/owner/image:latest",
            credentials={
                "username": "${{ github.actor }}",
                "password": "${{ secrets.GITHUB_TOKEN }}",
            },
        )
        assert container.image == "ghcr.io/owner/image:latest"
        assert container.credentials is not None
        assert container.credentials["username"] == "${{ github.actor }}"

    def test_create_with_numeric_ports(self) -> None:
        """Test creating container with numeric port list."""
        container = ModelGitHubActionsContainer(
            image="nginx:latest",
            ports=[80, 443, 8080],
        )
        assert container.ports == [80, 443, 8080]
        assert all(isinstance(p, int) for p in container.ports)

    def test_create_with_string_ports(self) -> None:
        """Test creating container with string port mappings."""
        container = ModelGitHubActionsContainer(
            image="nginx:latest",
            ports=["80:80", "443:443", "8080:8000"],
        )
        assert container.ports == ["80:80", "443:443", "8080:8000"]
        assert all(isinstance(p, str) for p in container.ports)

    def test_create_with_mixed_ports(self) -> None:
        """Test creating container with mixed port types."""
        container = ModelGitHubActionsContainer(
            image="nginx:latest",
            ports=[80, "8080:8080", 443, "9000:9000"],
        )
        assert container.ports == [80, "8080:8080", 443, "9000:9000"]

    def test_create_with_empty_credentials(self) -> None:
        """Test creating container with empty credentials dict."""
        container = ModelGitHubActionsContainer(
            image="node:14",
            credentials={},
        )
        assert container.credentials == {}

    def test_create_with_empty_env(self) -> None:
        """Test creating container with empty env dict."""
        container = ModelGitHubActionsContainer(
            image="node:14",
            env={},
        )
        assert container.env == {}

    def test_create_with_empty_ports(self) -> None:
        """Test creating container with empty ports list."""
        container = ModelGitHubActionsContainer(
            image="node:14",
            ports=[],
        )
        assert container.ports == []

    def test_create_with_empty_volumes(self) -> None:
        """Test creating container with empty volumes list."""
        container = ModelGitHubActionsContainer(
            image="node:14",
            volumes=[],
        )
        assert container.volumes == []


@pytest.mark.unit
class TestModelGitHubActionsContainerValidation:
    """Tests for ModelGitHubActionsContainer validation."""

    def test_image_is_required(self) -> None:
        """Test that image field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelGitHubActionsContainer()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("image",)
        assert errors[0]["type"] == "missing"

    def test_image_must_be_string(self) -> None:
        """Test that image must be a string."""
        with pytest.raises(ValidationError) as exc_info:
            ModelGitHubActionsContainer(image=123)  # type: ignore[arg-type]

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("image",) for e in errors)

    def test_credentials_must_be_dict(self) -> None:
        """Test that credentials must be a dictionary."""
        with pytest.raises(ValidationError) as exc_info:
            ModelGitHubActionsContainer(
                image="node:14",
                credentials=["username", "password"],  # type: ignore[arg-type]
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("credentials",) for e in errors)

    def test_env_must_be_dict(self) -> None:
        """Test that env must be a dictionary."""
        with pytest.raises(ValidationError) as exc_info:
            ModelGitHubActionsContainer(
                image="node:14",
                env=["NODE_ENV=production"],  # type: ignore[arg-type]
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("env",) for e in errors)

    def test_ports_must_be_list(self) -> None:
        """Test that ports must be a list."""
        with pytest.raises(ValidationError) as exc_info:
            ModelGitHubActionsContainer(
                image="node:14",
                ports="80",  # type: ignore[arg-type]
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("ports",) for e in errors)

    def test_volumes_must_be_list(self) -> None:
        """Test that volumes must be a list."""
        with pytest.raises(ValidationError) as exc_info:
            ModelGitHubActionsContainer(
                image="node:14",
                volumes="/data:/data",  # type: ignore[arg-type]
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("volumes",) for e in errors)

    def test_volumes_items_must_be_strings(self) -> None:
        """Test that volumes items must be strings."""
        with pytest.raises(ValidationError) as exc_info:
            ModelGitHubActionsContainer(
                image="node:14",
                volumes=[123, 456],  # type: ignore[list-item]
            )

        errors = exc_info.value.errors()
        assert any("volumes" in str(e["loc"]) for e in errors)

    def test_options_must_be_string(self) -> None:
        """Test that options must be a string."""
        with pytest.raises(ValidationError) as exc_info:
            ModelGitHubActionsContainer(
                image="node:14",
                options=["--cpus", "2"],  # type: ignore[arg-type]
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("options",) for e in errors)


@pytest.mark.unit
class TestModelGitHubActionsContainerOptionalFields:
    """Tests for optional field handling."""

    def test_all_optional_fields_default_to_none(self) -> None:
        """Test that all optional fields default to None."""
        container = ModelGitHubActionsContainer(image="alpine:latest")

        assert container.credentials is None
        assert container.env is None
        assert container.ports is None
        assert container.volumes is None
        assert container.options is None

    def test_optional_fields_can_be_explicitly_none(self) -> None:
        """Test that optional fields can be explicitly set to None."""
        container = ModelGitHubActionsContainer(
            image="alpine:latest",
            credentials=None,
            env=None,
            ports=None,
            volumes=None,
            options=None,
        )

        assert container.credentials is None
        assert container.env is None
        assert container.ports is None
        assert container.volumes is None
        assert container.options is None

    def test_partial_optional_fields(self) -> None:
        """Test creating container with some optional fields."""
        container = ModelGitHubActionsContainer(
            image="node:18",
            env={"NODE_ENV": "test"},
            ports=[3000],
        )

        assert container.image == "node:18"
        assert container.credentials is None
        assert container.env == {"NODE_ENV": "test"}
        assert container.ports == [3000]
        assert container.volumes is None
        assert container.options is None


@pytest.mark.unit
class TestModelGitHubActionsContainerSerialization:
    """Tests for model serialization."""

    def test_model_dump_with_all_fields(self) -> None:
        """Test model serialization with all fields."""
        container = ModelGitHubActionsContainer(
            image="node:18",
            credentials={"username": "user", "password": "pass"},
            env={"NODE_ENV": "production"},
            ports=[80, "8080:8080"],
            volumes=["/data:/data"],
            options="--cpus 2",
        )

        data = container.model_dump()

        assert data["image"] == "node:18"
        assert data["credentials"] == {"username": "user", "password": "pass"}
        assert data["env"] == {"NODE_ENV": "production"}
        assert data["ports"] == [80, "8080:8080"]
        assert data["volumes"] == ["/data:/data"]
        assert data["options"] == "--cpus 2"

    def test_model_dump_with_minimal_fields(self) -> None:
        """Test model serialization with minimal fields."""
        container = ModelGitHubActionsContainer(image="alpine:latest")

        data = container.model_dump()

        assert data["image"] == "alpine:latest"
        assert data["credentials"] is None
        assert data["env"] is None
        assert data["ports"] is None
        assert data["volumes"] is None
        assert data["options"] is None

    def test_model_dump_exclude_none(self) -> None:
        """Test model serialization excluding None values."""
        container = ModelGitHubActionsContainer(
            image="alpine:latest",
            env={"DEBUG": "true"},
        )

        data = container.model_dump(exclude_none=True)

        assert data["image"] == "alpine:latest"
        assert data["env"] == {"DEBUG": "true"}
        assert "credentials" not in data
        assert "ports" not in data
        assert "volumes" not in data
        assert "options" not in data

    def test_model_dump_json(self) -> None:
        """Test model JSON serialization."""
        container = ModelGitHubActionsContainer(
            image="node:18",
            ports=[80, 443],
        )

        json_str = container.model_dump_json()

        assert '"image":"node:18"' in json_str
        assert '"ports":[80,443]' in json_str

    def test_round_trip_serialization(self) -> None:
        """Test serialization and deserialization round trip."""
        original = ModelGitHubActionsContainer(
            image="python:3.12",
            credentials={"username": "test", "password": "secret"},
            env={"PYTHONUNBUFFERED": "1"},
            ports=[8000, "5432:5432"],
            volumes=["/app:/app", "/data:/data:ro"],
            options="--network host",
        )

        data = original.model_dump()
        restored = ModelGitHubActionsContainer(**data)

        assert restored.image == original.image
        assert restored.credentials == original.credentials
        assert restored.env == original.env
        assert restored.ports == original.ports
        assert restored.volumes == original.volumes
        assert restored.options == original.options


@pytest.mark.unit
class TestModelGitHubActionsContainerUseCases:
    """Tests for real-world use cases."""

    def test_node_ci_container(self) -> None:
        """Test typical Node.js CI container configuration."""
        container = ModelGitHubActionsContainer(
            image="node:18-alpine",
            env={
                "NODE_ENV": "test",
                "CI": "true",
            },
        )

        assert container.image == "node:18-alpine"
        assert container.env is not None
        assert container.env["NODE_ENV"] == "test"
        assert container.env["CI"] == "true"

    def test_python_ci_container(self) -> None:
        """Test typical Python CI container configuration."""
        container = ModelGitHubActionsContainer(
            image="python:3.12-slim",
            env={
                "PYTHONUNBUFFERED": "1",
                "PIP_NO_CACHE_DIR": "1",
            },
            volumes=["/cache:/root/.cache"],
        )

        assert container.image == "python:3.12-slim"
        assert container.volumes == ["/cache:/root/.cache"]

    def test_database_service_container(self) -> None:
        """Test database service container configuration."""
        container = ModelGitHubActionsContainer(
            image="postgres:15",
            env={
                "POSTGRES_USER": "test",
                "POSTGRES_PASSWORD": "test",
                "POSTGRES_DB": "testdb",
            },
            ports=[5432],
            options="--health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5",
        )

        assert container.image == "postgres:15"
        assert container.env is not None
        assert container.env["POSTGRES_DB"] == "testdb"
        assert container.ports == [5432]
        assert "--health-cmd" in container.options  # type: ignore[operator]

    def test_private_registry_container(self) -> None:
        """Test private registry container with secrets."""
        container = ModelGitHubActionsContainer(
            image="ghcr.io/myorg/myimage:latest",
            credentials={
                "username": "${{ github.actor }}",
                "password": "${{ secrets.GITHUB_TOKEN }}",
            },
        )

        assert "ghcr.io" in container.image
        assert container.credentials is not None
        assert "${{ github.actor }}" in container.credentials["username"]

    def test_container_with_resource_limits(self) -> None:
        """Test container with resource limits in options."""
        container = ModelGitHubActionsContainer(
            image="ubuntu:22.04",
            options="--cpus 2 --memory 4g --memory-swap 8g",
        )

        assert container.options is not None
        assert "--cpus 2" in container.options
        assert "--memory 4g" in container.options

    def test_container_with_multiple_volumes(self) -> None:
        """Test container with multiple volume mounts."""
        container = ModelGitHubActionsContainer(
            image="ubuntu:22.04",
            volumes=[
                "/workspace:/workspace",
                "/data:/data:ro",
                "/config:/app/config:rw",
                "/cache:/root/.cache",
            ],
        )

        assert container.volumes is not None
        assert len(container.volumes) == 4
        assert "/data:/data:ro" in container.volumes


@pytest.mark.unit
class TestModelGitHubActionsContainerImports:
    """Tests for model imports."""

    def test_import_from_configuration_module(self) -> None:
        """Test import from configuration module."""
        from omnibase_core.models.configuration.model_git_hub_actions_container import (
            ModelGitHubActionsContainer,
        )

        assert ModelGitHubActionsContainer is not None

    def test_model_has_expected_fields(self) -> None:
        """Test model has all expected fields defined."""
        fields = ModelGitHubActionsContainer.model_fields

        assert "image" in fields
        assert "credentials" in fields
        assert "env" in fields
        assert "ports" in fields
        assert "volumes" in fields
        assert "options" in fields

    def test_model_field_annotations(self) -> None:
        """Test model field type annotations."""
        fields = ModelGitHubActionsContainer.model_fields

        # image is required (no default)
        assert fields["image"].is_required()

        # All other fields are optional
        assert not fields["credentials"].is_required()
        assert not fields["env"].is_required()
        assert not fields["ports"].is_required()
        assert not fields["volumes"].is_required()
        assert not fields["options"].is_required()
